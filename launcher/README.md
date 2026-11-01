# Firecube launcher prototype

API 22 Android Views launcher written in Kotlin. Favorites initially match the
user's Netflix, YouTube (both known identifiers), Paramount+, Hulu, Max, Disney+,
Plex and Peacock choices. Only installed launchable apps are shown; identifiers
can vary. All apps discovers other entries. Hold Select to change favorites.
No Internet, microphone, accessibility, usage access, or background-service
permissions are requested. Version 0.2.0 adds cached installed app banners/icons, a four-column grid, a
compact clock/date header and smaller navigation controls. Artwork falls back to
the installed app icon when no TV banner is supplied. Wallpaper editing, custom
ordering and settings import/export are not yet implemented.

Build with JDK 17 or 21, Android SDK platform 35 and build-tools 35.0.0. Set
ANDROID_HOME or local.properties to the SDK path. Run:

```
./gradlew :app:assembleDebug :app:lintDebug :probe:assembleDebug
```

Windows: use gradlew.bat. Android Studio can open this directory. Debug APKs are
in each module's build/outputs/apk/debug directory. Release builds need a private
signing key configured locally; never commit the key or its passwords.

The HOME intent filter advertises eligibility; it does not override Fire OS
policy. Physical-device navigation and launch behavior are unverified. Preserve
the Amazon launcher. Do not use home-remapping, stock-launcher-disable, or startup
commands based solely on a successful build.

## Proposed device installation (requires user confirmation)

Preview only; no device installation has been performed by this project:

```
adb -s DEVICE:5555 install app-debug.apk
adb -s DEVICE:5555 shell am start -n dev.firecube.launcher/.MainActivity
```

This installs a normal APK and opens it manually. Back/Home remain available to
leave it. Uninstalling dev.firecube.launcher removes its local favorites. No
instruction here establishes that Home can be remapped on this firmware.

The probe module is a disposable app, dev.firecube.probe, with no services or
permissions. It is intended for a separate approved package disable/enable test.
Installing or running it does not itself verify recovery. A successful recovery
test on the probe will not prove permission to disable Amazon system packages.
