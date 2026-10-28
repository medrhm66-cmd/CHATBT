[app]

# (str) Title of your application
title = Bluetooth Chat

# (str) Package name
package.name = btchat

# (str) Package domain (needed for android packaging)
package.domain = org.chatbt

# (str) Source directory where the app lives
source.dir = .

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
requirements = python3,kivy,pyjnius

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION

# (list) target API
android.api = 33
android.accept_sdk_license = True
# (list) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Use Android X
android.androidx = True

# (list) The Android archs to build for
android.archs = arm64-v8a

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug command)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_root = 1

# (str) Path to build artifact, storage, etc.
bin_dir = ./bin
