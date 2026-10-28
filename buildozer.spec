[app]

title = Bluetooth Chat
package.name = btchat
package.domain = org.chatbt
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION
android.api = 33
android.minapi = 21
android.accept_sdk_license = True
android.androidx = True
android.archs = arm64-v8a
android.ndk = 

[buildozer]
log_level = 2
warn_root = 1
bin_dir = ./bin
