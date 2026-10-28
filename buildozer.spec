[app]

# ---------- App info ----------
title = ChatBT
package.name = chatbt
package.domain = org.chatbt
version = 1.0

# ---------- Source ----------
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json

# ---------- Requirements ----------
# For Arabic text in chat bubbles (optional), append:
#   ,arabic-reshaper,python-bidi==0.4.2
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pillow,pyjnius,android

# ---------- Display ----------
orientation = portrait
fullscreen = 0

# ---------- Android (Google Play ready) ----------
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_SCAN,BLUETOOTH_CONNECT,BLUETOOTH_ADVERTISE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# Google Play requires targeting API 36 for new apps (since 2026-08-31)
android.api = 36
android.minapi = 24
# NDK r28+ builds 16 KB page-size compatible libraries (Play requirement)
android.ndk = 28c
android.ndk_api = 24
# 64-bit only (Play requires 64-bit; smaller AAB)
android.archs = arm64-v8a

android.accept_sdk_license = True
android.enable_androidx = True
android.allow_backup = True

# Play Store wants an AAB; use "apk" for quick tests on your own phone
android.release_artifact = aab
android.debug_artifact = apk

# ---------- Python-for-Android ----------
# develop branch has the newest NDK / API support
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
