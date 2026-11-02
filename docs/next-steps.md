# Device test walkthrough

These are previews for user-initiated actions on the Stick. They do not run from
the cloud. Confirm the exact device address in `adb devices -l` before running.
Commands below use the address previously supplied by the user.

## Update the launcher

Download the 0.4.0 launcher APK into official platform-tools. Update preserves
Firecube's preferences and changes only the installed Firecube app:

```powershell
.\adb.exe -s 192.168.50.39:5555 install -r .\firecube-launcher-0.4.0-debug.apk
```

Only after `Success`:

```powershell
.\adb.exe -s 192.168.50.39:5555 shell am start -n dev.firecube.launcher/.MainActivity
```

Check both rows of favorites with the remote. Verify selected tabs, app launch,
Back behavior, long-press app menu, theme selection and a custom home heading.
Existing favorites should remain. Screenshot the new screen for visual review.
File-picker-dependent import/export can still be unavailable on Fire OS.

## Install the disposable recovery app

This installs a second app, dev.firecube.probe. It does not disable anything.
Download the recovery-test APK from downloads/v0.1.0 and, if approving that install:

```powershell
.\adb.exe -s 192.168.50.39:5555 install -r .\firecube-recovery-test-0.1.0-debug.apk
```

Only after `Success`, open the Windows helper from the 0.4.0 ZIP. Select ADB,
enter the same device identifier, and select **Test disposable app disable/enable…**.
Read the two-command preview; type `TEST PROBE` only if approving that test.
Choose a new audit filename. The helper disables only dev.firecube.probe,
verifies its user-0 state, enables it, and verifies again. It stops on errors.
The final override can differ from default-enabled; the audit records that fact.

On failure, inspect the audit. The scoped recovery command, if needed, is:

```powershell
.\adb.exe -s 192.168.50.39:5555 shell pm enable --user 0 dev.firecube.probe
```

Share the audit and a new diagnostic export after reviewing identifiers. Do not
substitute another package in these commands. A probe test is not proof that
Alexa or Amazon home may safely be disabled. There is no auto-debloat profile.
Amazon home remains installed/enabled throughout. No root or firmware change.
