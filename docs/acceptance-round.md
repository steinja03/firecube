# One consolidated acceptance round

Goal: return one report rather than a series of one-command replies. This tests
the 0.5.0 candidate, not a completed 1.0. Leave anything you cannot test as unrun.

## 1. Update Firecube, preserving preferences

Download firecube-launcher-0.5.0-debug.apk into your platform-tools folder. These
commands are a preview: running them approves an update of Firecube only.

```powershell
.\adb.exe -s 192.168.50.39:5555 install -r .\firecube-launcher-0.5.0-debug.apk
```

Only after `Success`:

```powershell
.\adb.exe -s 192.168.50.39:5555 shell am start -n dev.firecube.launcher/.MainActivity
```

Use the current device identifier if its address changed. This changes neither
Amazon home nor Alexa. Existing preferences should survive the update.

## 2. Work through the checklist at your pace

Extract firecube-windows-0.5.0.zip. Double-click Start-Firecube.cmd, then use
Locate ADB and enter the connected device identifier on the Inventory tab.
Python 3.13 is required and the helper installs pinned GUI dependencies locally.
No app is installed on the Stick by starting the helper.

Open Acceptance checklist. For each of Netflix, YouTube, Paramount+, Hulu,
Max/HBO Max, Disney+, Plex and Peacock, test launching, brief playback, remote
pause/Select as applicable, and returning. Do not enter streaming credentials
into reports. Record an unavailable required app as Unavailable; do not call it
a pass. Also check D-pad focus, Back, long press, order/hiding, themes and heading.

After a normal user-initiated reboot, manually open Firecube again and check
preferences. We are not testing or promising automatic startup. Record what the
physical Home button opens. Amazon home is the previously observed result.
Try settings export/import if a file picker is available; otherwise mark it
Unavailable. None of these tests requires disabling Amazon home.

## 3. Optional disposable-app test

The helper ZIP includes firecube-recovery-test-0.1.0-debug.apk. If approving its
installation, copy it to platform-tools and run:

```powershell
.\adb.exe -s 192.168.50.39:5555 install -r .\firecube-recovery-test-0.1.0-debug.apk
```

After Success, use Test disposable app disable/enable on the Inventory tab.
Read its command preview and type TEST PROBE only if approving those operations.
Save the audit and attach it to the acceptance checklist. This tests only
dev.firecube.probe. It does not establish system-package or launcher recovery.
If it fails, stop and include the audit rather than retrying or substituting
another package. See next-steps.md for the probe-only recovery command.

## 4. Export and share one bundle

Leave Firecube open on the TV. Fill in notes about visual issues or failures.
Select Export one acceptance bundle and choose a new filename. This reads
diagnostics and captures whatever screen is currently visible; it changes no
apps or settings. No screenshot is fabricated if capture is unsupported.

Review the ZIP: it contains device identifiers, package metadata, the screenshot
and any selected audit. Then upload that one ZIP to the conversation. Checks
you did not run must remain Not tested. Manual results are explicitly user
observations, separate from automated tests and current device evidence.

Unresolved 1.0 requirements remain Alexa cleanup, existing-app disable/restore
and full Home replacement with recovery. Passing launcher checks alone does not
resolve these. Firmware limitations may require an explicitly agreed scope.
