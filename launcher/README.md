# Firecube launcher prototype

API 22 Android Views launcher written in Kotlin. Favorites initially match the
user's Netflix, YouTube (both known identifiers), Paramount+, Hulu, Max, Disney+,
Plex and Peacock choices. Only installed launchable apps are shown; identifiers
can vary. All apps discovers other entries. Hold Select to change favorites.
No Internet, microphone, accessibility, usage access, or background-service
permissions are requested. Version 0.3.0 adds asynchronous app discovery/artwork loading, artwork scaled to
at most 288x162 and a 4 MB bitmap cache, 3–5 columns, app ordering/hiding, clock,
label and focus-animation toggles, and JSON settings import/export. Artwork falls
back to the installed icon when no banner is available. Hidden apps are hidden
only in Firecube; their packages and background behavior are unchanged. Manage
hidden apps from Settings to unhide them. Long-press Select opens app actions.

Settings import/export uses the system document picker without storage permissions.
If Fire OS lacks a usable picker, the launcher reports that limitation. Imports
are capped at 64 KiB, validated before applying, and need explicit confirmation.
Only launcher preferences are imported; no package commands are executed.

Settings includes a user-initiated Android Home Settings shortcut. Fire OS may
not provide or allow that screen. It never disables Amazon home or silently
changes the default. Even a selected default must be tested with the remote Home
button, app return, reboot and a verified recovery path before any stock-launcher
change is considered. Firmware services required by playback, networking, input
and DRM remain needed even if Amazon's home UI can be avoided.

Version 0.4.0 adds three dark color themes, a custom home heading, selected tabs,
focused-app footer text, app-information access and more distinct card focus.
Theme and heading persist and are included in settings exports. Older settings
exports remain importable with default theme/heading values.
Wallpaper editing, custom app labels and light themes remain future work.
Performance changes are implementation improvements, not a measured speedup;
resource use and remote navigation need physical API 22 device testing.

Version 0.5.0 refines the home layout with a static ambient vector backdrop,
pill navigation, responsive 16:9 artwork space, smaller card labels and compact
header spacing. This uses no wallpaper downloads, blur buffers or animation loop.
Settings serialization is isolated in LauncherSettings and has five JVM tests
covering round trips, backward compatibility and invalid data. Run
`./gradlew :app:testDebugUnitTest` to exercise them.

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
