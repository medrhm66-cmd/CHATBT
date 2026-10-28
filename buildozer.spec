[app]

# (str) Title of your application
title = Bluetooth Chat

# (str) Package name
package.name = btchat

# (str) Package domain (needed for android packaging)
package.domain = org.chatbt

# (str) Source directory where the app lives
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning
version = 0.1

# (list) Application requirements
requirements = python3,kivy,pyjnius

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION

# (list) target API
android.api = 33

# (bool) Accept Android SDK license automatically (Very important for GitHub Actions)
android.accept_sdk_license = True

# (list) Minimum API your APK will support
android.minapi = 21

# (bool) Use Android X
android.androidx = True

# (list) The Android archs to build for
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_root = 1
bin_dir = ./bin
