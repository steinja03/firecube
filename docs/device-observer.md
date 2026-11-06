# Firecube device-side Home candidate

## What has actually worked

The user's latest PC trial verified two separate Amazon Home → Firecube
foreground transitions. It then reported a closed log stream. That establishes
the event/redirection mechanism on tank build 688806320, not independent device
operation or reboot persistence. This candidate moves the event reader onto
the Stick and adds an optional, explicitly paired local-ADB boot controller.
Neither new component has been device-verified by the cloud build.

## One bundle, combined acceptance

Keep Python 3.13 and official ADB. Extract the whole ZIP into a new folder.
The installed Firecube launcher 0.5.0 remains usable; no launcher upgrade is
required and its heading, theme and favorites are not reset.

1. Run **Start-Device-Observer.cmd**. Enter ADB and the Stick identifier. Review
   scope and type START DEVICE OBSERVER. It stages a hash-verified DEX container,
   starts a detached shell observer, verifies its new session and performs one
   Home test. Failure attempts to stop the new observer, recording whether stop
   was verified. Keep its observer-result-start ZIP.
2. After success, close the PC's ADB session or disconnect the PC's network.
   Do not reboot yet. On TV, open Netflix, play briefly, then press remote Home.
   Try the other kept streaming apps. Firecube should return while the PC is
   disconnected. Amazon can appear briefly. This is the important independence
   test; a cloud compile or connected-PC test does not establish it.
3. Reconnect the PC and run **Observer-Status.cmd**. Keep the status ZIP. It
   reports a held process lock, readiness, session, redirect count, reconnect
   count and stop/failure reason. A stale status file alone is never liveness.
4. For reboot recovery, run **Install-Boot-Helper.cmd** only after the observer
   has been verified ready. Type INSTALL LOCAL BOOT HELPER. It installs the
   separately hash-verified Firecube Home Controller for user 0 and opens it.
5. On TV, choose **Pair / Start**. The helper connects only to this device's
   127.0.0.1:5555 ADB endpoint. If the TV requests authorization, review and
   approve the key for this operation. Select its persistent/always-allow option
   only if you want the key to remain authorized after reboot. This grants the
   helper ADB shell access to this Stick; it is a separate authorization from
   Codex/cloud permissions. The app keeps its private RSA key in its own private,
   non-backed-up app storage and does not contact any remote host.
6. Once Pair / Start succeeds, explicitly turn on **Start Home observer after
   reboot**. It defaults off. Disconnect the PC again. Perform a normal reboot,
   wait for Fire OS to finish starting, then test remote Home from Netflix and
   the other streaming apps. Local ADB availability, retained authorization,
   delivery of BOOT_COMPLETED and detached-shell survival are all firmware
   prerequisites; none is assumed proven by this candidate.
7. Reconnect and run **Observer-Status.cmd** again. Upload the start ZIP and
   both status ZIPs together, with your manual results for PC-disconnected Home,
   reboot Home, playback, and sleep/wake. A new native session after reboot is
   expected. If a stage fails, retain its result and stop there rather than
   repeating package/default mutations.

## Stop and recover

On TV, open **Firecube Home Controller**, turn boot start off and choose **Stop**.
Stop turns future boot starts off even if its ADB stop attempt fails. Verify its
reported result. Turning the switch off alone does not stop an existing observer.

The PC **Stop-Device-Observer.cmd** stops and verifies the current shell observer;
it cannot change the controller's private boot preference. Turn that switch off
on TV if it was enabled. A reboot ends a shell observer, but an enabled, working
boot helper will start it again. For recovery when pairing is unavailable,
force-stop/uninstall the ordinary Firecube Home Controller in Fire OS application
settings before rebooting. Force-stop suppresses its boot receiver until the app
is opened again. Amazon remains installed throughout.

Stop signals only the observer's private stop file and checks the advisory lock
is released. No PID kill list, broad setting reset or package disabling is used.
Files under /data/local/tmp/firecube-observer and the versioned tool APK remain
for status/restart. Keep the bundle and result files. Native status contains
component names/session metadata; review before sharing. No private ADB key,
full logcat history, screenshot or streaming account data is exported.

## Runtime behavior and efficiency

The shell observer is guarded to UID 2000, tank, API22 and the exact observed
fingerprint. The app controller is also exact-build guarded. A new Unix session detaches the observer from the launching ADB shell; a
system-wide file lock prevents two observers. The observer reads a filtered event stream and acts
only on known user-0 Amazon Home components, after rechecking the resumed
foreground. It verifies Firecube after each launch. It also reconciles an
already-visible Amazon Home after establishing a fresh stream, so it can handle
a boot that reached Home before the observer started. Another foreground app
is left alone.

There is no foreground polling loop while idle. A small watchdog checks the
private stop flag twice a second and updates one bounded status file every
30 seconds. Commands have timeouts and bounded output. No wake lock, remote
server or full device-log recording is used. Memory/CPU and sleep behavior still
need measurement on the physical unit. There is no claim of zero overhead.

If logcat closes, the observer reopens it with a fresh readiness marker and a
bounded retry backoff. Five stream failures in one minute stop it. Rapid Home
loops, a redirect burst, unverified Firecube foreground or command failure stop
it too. Native status reports the reason. The optional boot service retries
startup finitely and exits; it is not a permanent second background monitor.

The boot helper uses Internet permission for the hardcoded local socket, and
RECEIVE_BOOT_COMPLETED for its opt-in receiver. Services are not exported.
Only three fixed commands are implemented: observer status, observer stop and
the private startup script. It never issues root, firmware, package disabling
or arbitrary user-supplied shell commands. The authorized key nonetheless grants
ADB-level trust and must be treated as such. Uninstalling the helper removes its
private key; the device's trusted-public-key list is not edited automatically.

ADB authentication/frame code is based on the reviewed BSD AdbLib protocol and
RSA-layout implementation. Its license is included in the helper APK assets and
bundle's third-party notice. Tests cover checksums, invalid frames, command
allowlisting, RSA key layout and signing. Socket/authentication/boot behavior on
Fire OS remains a device acceptance requirement, not a unit-test conclusion.
Source: https://github.com/cgutman/AdbLib

## End-state boundaries

If the independence and reboot tests pass, this is a candidate for a Firecube
Home experience without an always-connected PC. It still redirects from Amazon;
it does not uninstall Amazon, prevent every momentary Amazon screen or stop its
processes. It does not remove Alexa or unused system apps. The tested component
state permission remains denied, and the known software-root project still
excludes build 688806320. A paired ADB client does not elevate shell above those
same restrictions. No exploit, bootloader or firmware write is included.

Full Amazon/Alexa removal remains a separate exact-build privilege/recovery
problem. All eight kept services, long-press behavior, sleep/wake and reboot must
pass on-device before calling this an accepted daily build. If local ADB or
boot delivery is blocked, the current-boot observer may still work with manual
ADB startup, but reboot autonomy is not achieved. Do not call that 1.0 full Home
replacement or bypass an exploit's firmware guard to force the conclusion.
