# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportUndefinedVariable=false
"""
ChatBT - Offline Bluetooth text chat (Android) using Kivy + KivyMD + pyjnius.

Protocol (line based, UTF-8, over an RFCOMM socket):
    H|<phone>   -> handshake: tells the other side our phone number (ID)
    M|<text>    -> chat message

Discovery: the app renames the phone's Bluetooth adapter to "ChatBT_<phone>"
so that nearby devices running ChatBT show the phone number in the scan list.
Whatever the name, the real ID is always exchanged in the handshake.
"""
import os
import re
import threading
import time

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.list import TwoLineListItem

# --------------------------------------------------------------------------
# Optional Arabic support (put an Arabic .ttf next to main.py, see notes)
# --------------------------------------------------------------------------
ARABIC_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "NotoNaskhArabic-Regular.ttf")
FONT = ARABIC_FONT if os.path.exists(ARABIC_FONT) else "Roboto"

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def shape(text):
        return get_display(arabic_reshaper.reshape(text))
except Exception:  # libraries not installed -> show text as-is
    def shape(text):
        return text

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
APP_UUID = "8ce255c0-200a-11e0-ac64-0800200c9a66"   # same on all ChatBT phones
NAME_PREFIX = "ChatBT_"
MAX_MSG_LEN = 1000

# --------------------------------------------------------------------------
# Android imports
# --------------------------------------------------------------------------
if platform == "android":
    from jnius import autoclass, cast
    from android.permissions import request_permissions
    from android.broadcast import BroadcastReceiver

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
    BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
    UUID = autoclass("java.util.UUID")
    BufferedReader = autoclass("java.io.BufferedReader")
    InputStreamReader = autoclass("java.io.InputStreamReader")
    BufferedWriter = autoclass("java.io.BufferedWriter")
    OutputStreamWriter = autoclass("java.io.OutputStreamWriter")
    BuildVersion = autoclass("android.os.Build$VERSION")


def request_bt_permissions(done):
    """Ask for runtime permissions. done(bool_all_granted) runs on Kivy thread."""
    if platform != "android":
        done(True)
        return
    p = "android.permission."
    if BuildVersion.SDK_INT >= 31:        # Android 12+
        perms = [p + "BLUETOOTH_SCAN", p + "BLUETOOTH_CONNECT",
                 p + "BLUETOOTH_ADVERTISE", p + "ACCESS_FINE_LOCATION",
                 p + "ACCESS_COARSE_LOCATION"]
    else:                                 # Android 11 and lower
        perms = [p + "ACCESS_FINE_LOCATION", p + "ACCESS_COARSE_LOCATION",
                 p + "BLUETOOTH", p + "BLUETOOTH_ADMIN"]

    def _cb(permissions, grants):
        ok = all(bool(g) for g in grants)
        Clock.schedule_once(lambda dt: done(ok), 0)

    request_permissions(perms, _cb)


# --------------------------------------------------------------------------
# Bluetooth manager (Android)
# --------------------------------------------------------------------------
class AndroidBluetooth:
    def __init__(self, handlers):
        self.h = handlers
        self.phone = ""
        self.adapter = None
        self.server = None
        self.sock = None
        self.reader = None
        self.writer = None
        self.receiver = None
        self.running = False
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()

    # ---- helpers ---------------------------------------------------------
    def emit(self, name, *args):
        fn = self.h.get(name)
        if fn:
            Clock.schedule_once(lambda dt: fn(*args), 0)

    def is_connected(self):
        return self.sock is not None

    def _ensure_name(self):
        try:
            wanted = NAME_PREFIX + self.phone
            if self.adapter.getName() != wanted:
                self.adapter.setName(wanted)
        except Exception:
            pass

    def _close_server(self):
        try:
            if self.server is not None:
                self.server.close()
        except Exception:
            pass
        self.server = None

    # ---- lifecycle -------------------------------------------------------
    def start(self, phone):
        self.phone = phone
        self.adapter = BluetoothAdapter.getDefaultAdapter()
        if self.adapter is None:
            self.emit("status", "This device has no Bluetooth.")
            return False
        if not self.adapter.isEnabled():
            try:
                PythonActivity.mActivity.startActivity(
                    Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            except Exception:
                pass
        self._ensure_name()
        try:
            self.receiver = BroadcastReceiver(
                self._on_broadcast,
                actions=["android.bluetooth.device.action.FOUND",
                         "android.bluetooth.adapter.action.DISCOVERY_FINISHED"])
            self.receiver.start()
        except Exception as e:
            self.emit("status", "Receiver error: %s" % e)
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return True

    def stop(self):
        self.running = False
        try:
            if self.receiver:
                self.receiver.stop()
        except Exception:
            pass
        self._close_server()
        self.disconnect()

    # ---- scanning --------------------------------------------------------
    def _on_broadcast(self, context, intent):
        try:
            action = intent.getAction()
            if action == "android.bluetooth.device.action.FOUND":
                dev = cast("android.bluetooth.BluetoothDevice",
                           intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE))
                self._report(dev)
            elif action == "android.bluetooth.adapter.action.DISCOVERY_FINISHED":
                self.emit("scan_finished")
        except Exception as e:
            self.emit("status", "Scan error: %s" % e)

    def _report(self, dev):
        name = dev.getName() or ""
        self.emit("device", name, dev.getAddress())

    def scan(self):
        if self.adapter is None or not self.adapter.isEnabled():
            self.emit("status", "Please turn Bluetooth on first.")
            self.emit("scan_finished")
            return
        try:
            # already paired devices first
            for d in self.adapter.getBondedDevices().toArray():
                self._report(cast("android.bluetooth.BluetoothDevice", d))
            if self.adapter.isDiscovering():
                self.adapter.cancelDiscovery()
            if not self.adapter.startDiscovery():
                self.emit("status", "Could not start scanning (check permissions / location).")
                self.emit("scan_finished")
        except Exception as e:
            self.emit("status", "Scan failed: %s" % e)
            self.emit("scan_finished")

    def make_discoverable(self):
        try:
            intent = Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
            intent.putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 300)
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            self.emit("status", "Cannot become visible: %s" % e)

    # ---- server side -----------------------------------------------------
    def _accept_loop(self):
        while self.running:
            if self.sock is not None or not self.adapter.isEnabled():
                time.sleep(1)
                continue
            self._ensure_name()
            try:
                self.server = self.adapter.listenUsingInsecureRfcommWithServiceRecord(
                    "ChatBT", UUID.fromString(APP_UUID))
                sock = self.server.accept()          # blocks until a peer connects
            except Exception:
                self._close_server()
                if self.running:
                    time.sleep(2)
                continue
            self._close_server()
            if sock is not None:
                self._open_session(sock)

    # ---- client side -----------------------------------------------------
    def connect(self, address):
        threading.Thread(target=self._connect_thread, args=(address,),
                         daemon=True).start()

    def _connect_thread(self, address):
        if self.sock is not None:
            return
        self.emit("status", "Connecting...")
        try:
            if self.adapter.isDiscovering():
                self.adapter.cancelDiscovery()
            dev = self.adapter.getRemoteDevice(address)
            sock = dev.createInsecureRfcommSocketToServiceRecord(
                UUID.fromString(APP_UUID))
            sock.connect()
        except Exception:
            self.emit("status", "Connection failed. Make sure ChatBT is open "
                                "on the other phone.")
            return
        self._close_server()        # unblocks accept(); loop will wait
        self._open_session(sock)

    # ---- session ---------------------------------------------------------
    def _open_session(self, sock):
        with self.lock:
            if self.sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
                return
            self.sock = sock
        try:
            self.reader = BufferedReader(
                InputStreamReader(sock.getInputStream(), "UTF-8"))
            self.writer = BufferedWriter(
                OutputStreamWriter(sock.getOutputStream(), "UTF-8"))
            self._write("H|" + self.phone)
            addr = sock.getRemoteDevice().getAddress()
        except Exception:
            self._drop()
            return
        self.emit("connected", addr)
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        while self.running and self.sock is not None:
            try:
                line = self.reader.readLine()      # blocks (background thread)
            except Exception:
                break
            if line is None:
                break
            if line.startswith("H|"):
                self.emit("peer", line[2:])
            elif line.startswith("M|"):
                self.emit("message", line[2:])
        self._drop()

    def _write(self, line):
        with self.write_lock:
            self.writer.write(line + "\n")
            self.writer.flush()

    def send(self, text):
        text = text.replace("\r", " ").replace("\n", " ")[:MAX_MSG_LEN]

        def _run():
            try:
                self._write("M|" + text)
            except Exception:
                self._drop()

        threading.Thread(target=_run, daemon=True).start()

    def _drop(self):
        with self.lock:
            sock, self.sock = self.sock, None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
            self.emit("disconnected")

    def disconnect(self):
        self._drop()


# --------------------------------------------------------------------------
# Fake Bluetooth manager so you can test the UI on a PC (python main.py)
# --------------------------------------------------------------------------
class MockBluetooth:
    def __init__(self, handlers):
        self.h = handlers
        self.connected = False

    def emit(self, name, *args):
        fn = self.h.get(name)
        if fn:
            Clock.schedule_once(lambda dt: fn(*args), 0)

    def is_connected(self):
        return self.connected

    def start(self, phone):
        self.emit("status", "[MOCK] Ready. Your ID: " + phone)
        return True

    def stop(self):
        pass

    def scan(self):
        def _go(dt):
            self.emit("device", "ChatBT_+213550000001", "AA:BB:CC:DD:EE:01")
            self.emit("device", "JBL Speaker", "AA:BB:CC:DD:EE:02")
            self.emit("scan_finished")
        Clock.schedule_once(_go, 1)

    def make_discoverable(self):
        self.emit("status", "[MOCK] Visible for 300 seconds.")

    def connect(self, address):
        self.connected = True
        self.emit("connected", address)
        Clock.schedule_once(lambda dt: self.emit("peer", "+213550000001"), 0.3)

    def send(self, text):
        Clock.schedule_once(lambda dt: self.emit("message", "echo: " + text), 1)

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.emit("disconnected")


# --------------------------------------------------------------------------
# Chat bubble widget
# --------------------------------------------------------------------------
class ChatBubble(BoxLayout):
    def __init__(self, text, mine, **kwargs):
        super().__init__(size_hint_y=None, padding=(dp(8), dp(3)), **kwargs)
        shaped = shape(text)
        fs = sp(16)

        core = CoreLabel(text=shaped, font_size=fs, font_name=FONT)
        core.refresh()
        natural = core.texture.width if core.texture else dp(40)
        inner_w = min(natural + 2, Window.width * 0.72)

        lbl = Label(text=shaped, font_size=fs, font_name=FONT,
                    color=(0, 0, 0, 1), size_hint=(None, None),
                    width=inner_w, text_size=(inner_w, None),
                    halign="left", valign="top")
        lbl.texture_update()
        lbl.height = lbl.texture_size[1]

        card = BoxLayout(size_hint=(None, None),
                         size=(inner_w + dp(24), lbl.height + dp(16)),
                         padding=(dp(12), dp(8)))
        bg = (0.85, 0.97, 0.78, 1) if mine else (1, 1, 1, 1)
        with card.canvas.before:
            Color(*bg)
            rect = RoundedRectangle(pos=card.pos, size=card.size,
                                    radius=[dp(14)] * 4)
        card.bind(pos=lambda i, v: setattr(rect, "pos", v),
                  size=lambda i, v: setattr(rect, "size", v))
        card.add_widget(lbl)

        self.height = card.height + dp(6)
        if mine:
            self.add_widget(Widget())
            self.add_widget(card)
        else:
            self.add_widget(card)
            self.add_widget(Widget())


# --------------------------------------------------------------------------
# UI (KV)
# --------------------------------------------------------------------------
KV = """
ScreenManager:

    MDScreen:
        name: "setup"
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(32)
            spacing: dp(20)
            Widget:
                size_hint_y: None
                height: dp(40)
            MDLabel:
                text: "Welcome to ChatBT"
                font_style: "H5"
                halign: "center"
                adaptive_height: True
            MDLabel:
                text: "Enter your phone number. It is your ID for chatting with nearby phones. No internet needed."
                halign: "center"
                adaptive_height: True
            MDTextField:
                id: phone_field
                hint_text: "Phone number (e.g. +213550123456)"
                input_type: "tel"
                helper_text: "Digits only, optional + at the start"
                helper_text_mode: "on_focus"
            MDRaisedButton:
                text: "Save & Continue"
                size_hint_x: 1
                on_release: app.save_phone()
            Widget:

    MDScreen:
        name: "scan"
        MDBoxLayout:
            orientation: "vertical"
            MDTopAppBar:
                title: "ChatBT"
                right_action_items: [["account-edit", lambda x: app.edit_phone()]]
                elevation: 2
            MDLabel:
                id: me_label
                text: ""
                halign: "center"
                size_hint_y: None
                height: dp(36)
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: dp(12), 0
                spacing: dp(8)
                MDRaisedButton:
                    id: scan_btn
                    text: "Scan for Nearby Devices"
                    size_hint_x: 1
                    on_release: app.start_scan()
                MDRaisedButton:
                    text: "Make Me Visible (5 min)"
                    size_hint_x: 1
                    md_bg_color: app.theme_cls.accent_color
                    on_release: app.make_visible()
            MDLabel:
                id: status_label
                text: ""
                halign: "center"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: dp(48)
            ScrollView:
                MDList:
                    id: device_list

    MDScreen:
        name: "chat"
        MDBoxLayout:
            orientation: "vertical"
            md_bg_color: 0.93, 0.92, 0.89, 1
            MDTopAppBar:
                id: chat_bar
                title: "Chat"
                left_action_items: [["arrow-left", lambda x: app.leave_chat()]]
                elevation: 2
            ScrollView:
                id: scroll
                MDBoxLayout:
                    id: msgs
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(2)
                    padding: 0, dp(8)
            MDBoxLayout:
                adaptive_height: True
                padding: dp(8)
                spacing: dp(8)
                md_bg_color: 1, 1, 1, 1
                MDTextField:
                    id: msg_input
                    hint_text: "Type a message"
                    mode: "round"
                    multiline: False
                    pos_hint: {"center_y": .5}
                    on_text_validate: app.send_message()
                MDIconButton:
                    icon: "send"
                    pos_hint: {"center_y": .5}
                    on_release: app.send_message()
"""


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
class ChatBTApp(MDApp):
    def build(self):
        self.title = "ChatBT"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        self.phone = ""
        self.bt = None
        self.bt_ready = False
        self.dev_items = {}      # address -> list item
        self.dev_names = {}      # address -> advertised name
        Window.bind(on_keyboard=self.on_keyboard)
        return Builder.load_string(KV)

    # ---- startup ---------------------------------------------------------
    def on_start(self):
        self.store = JsonStore(os.path.join(self.user_data_dir, "chatbt.json"))
        handlers = {
            "status": self.set_status,
            "device": self.on_device,
            "scan_finished": self.on_scan_finished,
            "connected": self.on_connected,
            "peer": self.on_peer,
            "message": self.on_message,
            "disconnected": self.on_disconnected,
        }
        self.bt = AndroidBluetooth(handlers) if platform == "android" \
            else MockBluetooth(handlers)

        if self.store.exists("user"):
            self.phone = self.store.get("user")["phone"]
            self.root.current = "scan"
            self.init_bluetooth()
        else:
            self.root.current = "setup"

    def on_stop(self):
        if self.bt:
            self.bt.stop()

    def on_keyboard(self, window, key, *args):
        if key == 27 and self.root.current == "chat":    # Android Back button
            self.leave_chat()
            return True
        return False

    # ---- identity --------------------------------------------------------
    def save_phone(self):
        raw = self.root.ids.phone_field.text
        phone = re.sub(r"[\s\-()]", "", raw)
        if not re.fullmatch(r"\+?\d{6,15}", phone):
            self.root.ids.phone_field.error = True
            self.root.ids.phone_field.helper_text = "Invalid phone number"
            return
        self.phone = phone
        self.store.put("user", phone=phone)
        self.root.current = "scan"
        if self.bt_ready:       # number changed -> restart with new name
            self.bt.phone = phone
            self.bt._ensure_name()
            self.root.ids.me_label.text = "Your ID: " + phone
        else:
            self.init_bluetooth()

    def edit_phone(self):
        self.root.ids.phone_field.text = self.phone
        self.root.current = "setup"

    # ---- bluetooth init --------------------------------------------------
    def init_bluetooth(self):
        self.root.ids.me_label.text = "Your ID: " + self.phone
        self.set_status("Requesting permissions...")
        request_bt_permissions(self._after_permissions)

    def _after_permissions(self, ok):
        if not ok:
            self.set_status("Permissions denied. Enable Bluetooth/Location "
                            "permissions in Android settings.")
            return
        if self.bt.start(self.phone):
            self.bt_ready = True
            self.set_status("Ready. Tap 'Scan' to find nearby ChatBT users.")

    # ---- scan screen -----------------------------------------------------
    def set_status(self, text):
        self.root.ids.status_label.text = text

    def start_scan(self):
        if not self.bt_ready:
            self.init_bluetooth()
            return
        self.root.ids.device_list.clear_widgets()
        self.dev_items.clear()
        self.root.ids.scan_btn.disabled = True
        self.set_status("Scanning...")
        self.bt.scan()

    def make_visible(self):
        if self.bt_ready:
            self.bt.make_discoverable()
        else:
            self.init_bluetooth()

    def on_device(self, name, addr):
        self.dev_names[addr] = name
        is_chatbt = name.startswith(NAME_PREFIX)
        primary = (name[len(NAME_PREFIX):] + "  (ChatBT)") if is_chatbt \
            else (name or "Unknown device")
        item = self.dev_items.get(addr)
        if item:
            item.text = primary
            return
        item = TwoLineListItem(
            text=primary, secondary_text=addr,
            on_release=lambda x, a=addr: self.connect_to(a))
        self.dev_items[addr] = item
        lst = self.root.ids.device_list
        if is_chatbt:       # ChatBT users on top
            lst.add_widget(item, index=len(lst.children))
        else:
            lst.add_widget(item)

    def on_scan_finished(self):
        self.root.ids.scan_btn.disabled = False
        n = len(self.dev_items)
        self.set_status("Found %d device(s). Tap one to chat." % n if n
                        else "No devices found. Try again.")

    def connect_to(self, addr):
        if self.bt.is_connected():
            return
        self.set_status("Connecting...")
        self.bt.connect(addr)

    # ---- chat screen -----------------------------------------------------
    def on_connected(self, addr):
        name = self.dev_names.get(addr, "")
        title = name[len(NAME_PREFIX):] if name.startswith(NAME_PREFIX) \
            else (name or addr)
        self.root.ids.chat_bar.title = title
        self.root.ids.msgs.clear_widgets()
        self.root.ids.scan_btn.disabled = False
        self.set_status("Connected.")
        self.root.current = "chat"

    def on_peer(self, phone):
        self.root.ids.chat_bar.title = phone

    def add_bubble(self, text, mine):
        self.root.ids.msgs.add_widget(ChatBubble(text, mine))
        Clock.schedule_once(
            lambda dt: setattr(self.root.ids.scroll, "scroll_y", 0), 0.05)

    def on_message(self, text):
        self.add_bubble(text, mine=False)

    def send_message(self):
        field = self.root.ids.msg_input
        text = field.text.strip()
        if not text:
            return
        if not self.bt.is_connected():
            self.set_status("Not connected.")
            return
        text = text[:MAX_MSG_LEN]
        self.add_bubble(text, mine=True)
        self.bt.send(text)
        field.text = ""
        Clock.schedule_once(lambda dt: setattr(field, "focus", True), 0.1)

    def leave_chat(self):
        self.bt.disconnect()
        self.root.current = "scan"

    def on_disconnected(self):
        if self.root.current == "chat":
            self.root.current = "scan"
        self.set_status("Disconnected.")


if __name__ == "__main__":
    ChatBTApp().run()