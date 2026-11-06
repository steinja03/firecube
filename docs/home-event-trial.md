# PC-assisted Home event trial

## Why this is the next experiment

On tank/API22/Fire OS build 688806320, the preferred-Home trial actually saved
Firecube as the preferred Home component, but resolveIntent still returned
Amazon. Its scoped rollback verified the original empty preference state.
The trial stopped before injecting Home. This proves the setter was accepted;
it does not prove the physical Home key was tested with that preference active.
The earlier accessibility trial failed its settings readback and restored empty/0.
Repeating those same writes offers no new compatibility evidence.

The next independent mechanism watches Android activity-resume events through an
ADB shell logcat stream. Android 5.1's source specifies am_resume_activity as
[User, Token, Task ID, Component Name]. The helper accepts only user 0 and exact
known Amazon Home components, verifies Amazon Home is still the resumed activity,
then explicitly launches the installed Firecube activity. It does not inspect
screen content or arbitrary app logs. Logcat filters include only the resume tag
and our readiness-marker tag; unrelated app events are not saved in the report.

Primary event-schema source reviewed:
https://github.com/aosp-mirror/platform_frameworks_base/blob/android-5.1.1_r38/services/core/java/com/android/server/am/EventLogTags.logtags

This mechanism is unverified on the user's Fire OS until the trial runs.
Log visibility, event format, explicit launches and actual foreground transitions
can each fail. Source compatibility is not a device result.

## Run it

Extract the whole ZIP. Python 3.13 and official ADB are the only requirements.
Run Test-Home-Events.cmd, enter the ADB path and Stick identifier, then review the
scope and type TEST HOME EVENTS. Keep the PC awake and connected.

The helper verifies the exact inspected firmware and only user 0 running. It
opens Firecube first to verify availability. That explicit open is not counted
as Home success. It starts a filtered event stream and writes a unique log marker;
no historical event is acted on before the marker arrives. It then injects Home
once. Only a fresh Home event, a subsequent explicit redirect and a verified
Firecube foreground count as automatic-test success.

If that succeeds, use the remaining time to open a streaming app and press the
physical remote's Home button. Watch for Amazon briefly appearing and Firecube
following it. The monitor runs for about 90 seconds after the injected Home,
with a maximum of eight redirects. Fast repeated redirects stop the trial rather
than creating a loop. Missing events or an unverified foreground stop it too.
Ctrl+C stops early and still saves a result. ADB timeouts can extend total duration.

Upload home-events-result-*.zip and tell us whether the physical remote returned
to Firecube during the trial. The report does not automatically label physical
remote behavior as verified. It contains endpoint, operation timestamps and
scoped event results, without screenshots or full logcat history.

## What persists

No app, tool container or device background service is installed. No package
states, accessibility settings, Home preferences, firmware or root state are
changed. The device gets one diagnostic log marker and ordinary activity/key
operations. Ending the trial closes its PC-side logcat client. There is no new
Home behavior configured to restore. Normal Amazon Home behavior is expected
afterward. No reboot is needed to stop this trial.

This is a PC-dependent compatibility test, not the final autonomous launcher.
It may briefly display Amazon, does not stop Amazon's processes, and does not
remove Alexa. Reboot persistence and playback compatibility are unverified.
If successful, it supports developing a device-side shell observer with a
controlled start/stop mechanism; automatic startup after reboot is a separate
requirement. If it fails, the result identifies whether logs, events or launches
were unavailable rather than inferring root is necessary from one failed API.

## Root status checked again

The upstream GhostLock README and gl_root.py still explicitly target build
688805020 and fixed addresses; this Stick is 688806320. No compatible ready-to-run
software-root tool has been established by this review. Do not bypass its guard.
https://github.com/Anezium/ghostlock-firetv-tank/blob/main/README.md
https://github.com/Anezium/ghostlock-firetv-tank/blob/main/scripts/gl_root.py

The previously identified Amonet hardware route remains a physical eligibility
question. This software trial cannot establish board/bootrom accessibility and
performs no exploit, downgrade, preloader/RPMB write or firmware flash.
