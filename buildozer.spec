[app]
# (str) Source directory where the app lives
source.dir = .
# (str) Title of your application
title = Bluetooth Chat

# (str) Package name
package.name = btchat

# (str) Package domain (needed for android packaging)
package.domain = org.chatbt

# (list) Source files to include (let it empty to include all files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of directory to include (from source.dir)
source.include_dirs = 

# (list) Source files to exclude (let it empty to not exclude anything)
source.exclude_exts = spec

# (list) List of exclusions using pattern matching
source.exclude_patterns = license,images/*.jpg

# (str) Application versioning
version = 0.1

# (list) Application requirements
# Note: Python3, Kivy, and Pyjnius are essential for Bluetooth and UI
requirements = python3,kivy,pyjnius

# (list) Custom source folders for python requirements
#requirements.source.kivy = ../../../kivy

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (list) Supported orientations
orientation = portrait

# (list) List of services to declare
#services = 

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color
#presplash.color = #FFFFFF

# (list) Permissions
# Necessary for Bluetooth communication without internet
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION

# (list) target API
android.api = 33

# (list) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Use Android X
android.androidx = True

# (list) The Android archs to build for,, can be arm64-v8a, armeabi-v7a, x86, x86_64
android.archs = arm64-v8a

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug command)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_root = 1

# (str) Path to build artifact, storage, etc.
bin_dir = ./bin

# (str) Path to build intermediate
#build_dir = ./.buildozer
