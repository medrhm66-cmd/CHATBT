[app]

title = ChatBT
package.name = chatbt
package.domain = org.chatbt
version = 1.0

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json

requirements = python3,kivy==2.2.1,kivymd==1.1.1,pillow,pyjnius,android

orientation = portrait
fullscreen = 0

android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_SCAN,BLUETOOTH_CONNECT,BLUETOOTH_ADVERTISE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True
android.enable_androidx = True
android.allow_backup = True

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
