# One reversible Home-redirect trial

This is an experimental, different mechanism from the failed package-disable
test. It is not root and does not remove Amazon home or Alexa. It can make Home
return to Firecube after Amazon home briefly appears, only if this firmware
allows accessibility activation and delivers the expected window event.

## What running it approves

Run-Home-Bridge.cmd asks for official adb.exe and the Stick identifier, previews
the scope, and requires typing ENABLE BRIDGE. Before that confirmation no ADB
operation is executed. After confirmation it:

1. Verifies tank, a stable device identity, fingerprint, only user 0 running, and
   Firecube installed. Reads the two existing accessibility settings.
2. Refuses unexpected service values, an already-listed bridge, or a configured
   inactive service list that enabling accessibility would activate unexpectedly.
3. Verifies the included APK hash and installs only dev.firecube.homebridge.
4. Pauses that app, rechecks the device/settings, and adds its service while
   preserving other configured services. Enables accessibility if necessary.
5. Verifies readbacks, resumes only our bridge, presses Home once and checks
   whether Firecube actually becomes the resumed activity.
6. On failure, pauses our app and attempts exact settings restoration. It checks
   identity and refuses to overwrite unrelated changes. A rollback can fail and
   is reported as unverified; it is never silently called successful.

The bridge does not read screen content, filter keys, use an overlay, request
network/microphone access, poll continuously, disable packages or write firmware.
It listens only for Amazon launcher's known Home window classes. It is installed
paused and remains inactive unless accessibility and its pause state allow it.
Settings and control broadcasts target user 0. Ordinary ADB APK installation may
register the APK for other device profiles, but each starts paused and no other
profile's accessibility settings or pause preference are changed by this trial.
The control receiver requires Android's DUMP permission; if the shell lacks it,
the trial must stop rather than weaken that restriction.

## Run on Windows

1. Extract the whole trial ZIP to a writable folder. Python 3.13 is required;
   no extra Python packages are needed.
2. Ensure the Stick is connected in official platform-tools. If necessary:

   ```powershell
   .\adb.exe connect 192.168.50.39:5555
   ```

3. Double-click Run-Home-Bridge.cmd. Enter the adb.exe path and current device
   identifier. Review the preview. Type ENABLE BRIDGE only if approving it.
4. Let it finish. Keep the receipt JSONL and bridge-last-receipt.txt in the folder.
   Review and upload the resulting bridge-result ZIP. It includes a screenshot,
   device/permission/accessibility metadata and the receipt; review before sharing.

If the helper cannot create a receipt or preflight fails, it may stop without a
bundle. Send that exact message; do not improvise root/disable commands.

## Roll back

Double-click Restore-Home-Bridge.cmd, select the original trial receipt and type
RESTORE BRIDGE. It pauses our app and restores the original settings only when
the original device and expected current settings are verified. It leaves the
small helper APK installed and paused; it can then be removed through Fire OS's
ordinary installed-app settings if offered. It never removes other services.

If settings restoration is refused or fails, retain the receipt. To request only
our app to pause, the scoped recovery command is:

```powershell
.\adb.exe -s 192.168.50.39:5555 shell am broadcast --user 0 --include-stopped-packages -n dev.firecube.homebridge/.BridgeControlReceiver -a dev.firecube.homebridge.SET_PAUSED --ez paused true
```

The app confirms a committed pause with Broadcast completed: result=1. This
command does not restore Android settings; it stops only this app's redirect.
Device settings remain independently accessible; the service ignores them.

## Outcome limits

A positive foreground observation means the single trial saw Firecube after a
Home event. Reboot behavior, repeated remote presses, flicker and streaming
navigation still need physical testing. A failure is not proof that all possible
Home mechanisms are impossible. Neither result provides root, removes Alexa or
justifies disabling Amazon home. For full-control options see definitive-options.md.
