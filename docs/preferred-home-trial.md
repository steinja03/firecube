# Reversible preferred-Home trial for the observed empty baseline

## Evidence, not a guarantee

The user's query-only report confirmed shell UID 2000, API 22/tank, effective
SET_PREFERRED_APPLICATIONS=0 (granted), WRITE_SECURE_SETTINGS=0 and
CHANGE_COMPONENT_ENABLED_STATE=-1 (denied). It exposed the Android 5.1
replacePreferredActivity interface, listed Firecube as enabled/exported, showed
no preferred Home or saved Home filters, and resolved Home to Amazon's activity.
This justifies testing the separate Home preference route. It does not prove the
setter is allowed by Amazon's implementation or that remote Home will honor it.

The previous Home Bridge trial failed its service-list readback and verified
rollback to empty/0. Leave it paused. This new trial never writes accessibility
settings, installs an app, disables Amazon packages, obtains root or flashes.

## What the trial changes

The helper copies a checksum-verified DEX container to /data/local/tmp and runs
it as shell. The native tool is guarded to UID 2000, tank, API 22 and the exact
688806320 fingerprint. It permits only a fixed Firecube Home target for user 0.
Before mutation it refuses existing Home preferences, other Firecube defaults,
missing permission or a disabled/unexported target.

It durably saves a device-bound baseline in a unique owner-readable temporary
file, verifies the baseline again, then calls Android's replacePreferredActivity
for MAIN/HOME/DEFAULT, using the live candidate set and fixed Firecube component.
It verifies a query-visible Firecube Home entry and resolution, then the Windows
helper injects one Home key and records the resumed activity. This single injected
key test does not establish physical remote, long-press, reboot or playback results.

If the preferred entry does not stick, or Home still shows Amazon, it attempts
rollback. The original baseline is specifically unconfigured. To restore it,
the tool may clear Firecube preferences only if its only current preference is
the exact Home entry created by the trial. If other Firecube defaults appeared,
it refuses the broad clear. It verifies the query-visible empty Home preference
and original resolved fallback. Amazon stays installed throughout. Other apps'
defaults are not cleared. Automatic rollback is not retried blindly; unresolved
restoration remains explicit in the report.

## Run on Windows

1. Extract the entire ZIP into a new folder. Python 3.13 and official ADB are
   required; no extra Python dependencies are installed.
2. Make sure the Stick is connected, then double-click Set-Firecube-Home.cmd.
3. Enter adb.exe and the current Stick identifier. Review the scope and type
   SET FIRECUBE HOME only if approving this preferred-Home change and test.
4. Leave the window open until it finishes. Keep every audit/backup file and
   homepref-last-trial.txt. Do not delete the device's temporary backup.
5. Review and upload the homepref-result ZIP. It includes the operation audit,
   original device backup when retrievable, result status and a screenshot.
   These can include device identifiers and visible TV content.

No Firecube APK upgrade is required. The tool container is not installed. It
leaves its small temporary tool and backup files in /data/local/tmp for recovery.

## Restore the original behavior

Run Restore-Original-Home.cmd, use the original trial audit, and type
RESTORE ORIGINAL HOME. It verifies identity/build and clears only the trial's
owned preference subject to the guards above. It does not run a general
reset-preferred-apps operation. If restoration is refused or unverified, retain
the report; do not substitute package disabling, app uninstall or broad default
clearing. The normal Amazon launcher has not been removed by this workflow.

After a successful trial, test the actual remote Home button from a streaming
app. Only then test a normal reboot. Neither result is assumed by this build.
Alexa remains enabled; this operation does not grant package-state permission.
