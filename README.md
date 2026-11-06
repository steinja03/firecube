# Firecube — Fire TV tools

Read-only Windows inventory tools and an API 22 Android launcher prototype.
The supplied device baseline confirms a Fire TV Stick 2nd generation (AFTT),
Fire OS 5.2.9.5 (688806320), API 22, with non-root ADB. The Windows collector
and viewer have been exercised by the user; the Android APKs are not yet
device-tested. Package mutation and Home-button replacement are unverified.

## Download debug APKs

- [Firecube launcher 0.5.0](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/v0.5.0/firecube-launcher-0.5.0-debug.apk)
- [Recovery-test app 0.1.0](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/v0.1.0/firecube-recovery-test-0.1.0-debug.apk)
- [Launcher/helper SHA-256 checksums](downloads/v0.5.0/SHA256SUMS)
- [Recovery-test SHA-256 checksum](downloads/v0.1.0/SHA256SUMS)

These are debug-signed prototypes, not production releases. Both target API 35
with minimum API 22 and have verified v1 signatures for Android 5.1 compatibility.
Build and lint checks pass; physical Fire TV testing remains outstanding.
No device installation or package changes have been performed from this repository.
See [launcher instructions](launcher/README.md) for installation previews.
Preserve Amazon's launcher; the HOME intent filter does not override Fire OS.

## Windows collection

Install Python 3.10 or newer from python.org and Google's official Android
SDK Platform Tools. No Python packages are required. Enable ADB debugging on
the Stick, connect using `adb connect IP:5555`, and accept its authorization
prompt. Run `adb devices -l` to obtain its exact identifier.

From the directory containing inventory.py, run the following as one PowerShell
line, replacing the ADB path and device address with your own:

```powershell
py .\inventory.py --adb 'C:\path\to\platform-tools\adb.exe' --serial '192.168.1.50:5555' --output '.\stick-baseline.json'
```

The output file must not already exist. Use a new filename for later captures.
The tool selects one explicit device, reads properties and package states,
checks consistency, and stops on errors. It never installs, disables, enables,
uninstalls, or launches anything. No root is required. The report includes the
device address and installed package identifiers; review it before sharing.

This baseline is not a backup of app data, APKs, or firmware. Restoration is not
implemented or verified. Enabled status is an observation, not the complete
internal package-manager state. Labels, versions, dependencies, descriptions,
restorability, and disabling risk remain explicitly unknown at this milestone.
Do not use this report alone to decide which packages to disable.

## Validation

```powershell
py -m unittest discover -s tests -v
```

Tests exercise parsing, read-only command selection, and inconsistent-state
failure handling with simulated ADB responses. Windows and physical-device
validation remain required: run the collector and confirm its model, firmware,
package count, and enabled flags. A blank disabled-package list is valid.

## Next milestones

Review the captured inventory before adding package metadata and a Windows GUI.
Preserve Amazon's launcher and essential services. Any device-changing operation
needs an explicit preview and user confirmation. Launcher replacement and package
disable/restore permissions are unverified. Use Kotlin with Android Views for the
API 22 launcher prototype; Compose for TV cannot support this device.

## Windows inventory viewer (milestone 2)

Use Python **3.13** for the GUI: the pinned PySide6 release supports Python
3.10–3.14, not Python 3.15. Python 3.15 can still run the dependency-free collector.
Install Python 3.13 alongside it, then from the extracted project directory run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Select **Open baseline JSON…** and choose the saved Stick baseline. Expect 217
packages, 198 system, 19 non-system, and none disabled for the report reviewed in
this session. Search and combine type/state filters; select a row for details.
The app validates imported structure and rejects duplicate identifiers and invalid
states. Invalid imports leave the existing report loaded. Risk and restorability
remain unknown regardless of imported claims. Non-system does not prove an app
was manually installed. The viewer has no ADB connection or mutation controls.

Run all tests using `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
GUI tests use Qt's offscreen platform. Actual Windows display testing remains
necessary. A baseline is historical and cannot establish current connectivity.

## Launcher and Alexa investigation

`launcher/` now contains an API 22 launcher and a separate disposable recovery
probe. See launcher/README.md for build instructions and installation previews.
The launcher is a prototype; device behavior is not yet verified.

`change_plan.py` records the user's streaming-app keep list. Alexa removal is
explicitly requested, but observed Alexa identifiers remain investigation targets,
not approved disable candidates. No mutation commands are generated yet.
`diagnostics.py` captures package-manager help, home-resolution output, users, and
package metadata for observed Alexa candidates and the Amazon launcher. Unsupported
commands are recorded as failures. Help output does not prove mutation permission.

```
python diagnostics.py --adb PATH_TO_ADB --serial DEVICE:5555 --output evidence.json
```

This read-only evidence may contain device identifiers and package metadata;
review before sharing. Files are never overwritten. A successful probe recovery
cannot establish safe dependencies or permissions for system/Alexa packages.


## Version 0.3.0: workflow and limitations

On Windows, extract the helper ZIP and double-click `Start-Firecube.cmd`. It uses
Python 3.13 and installs pinned GUI requirements in a local virtual environment.
It does not install ADB or change the Stick. Use **Locate ADB…**, select official
platform-tools/adb.exe, and enter the exact connected device identifier. Use
**Export device diagnostics…** to save a read-only report, including memory,
storage, package-manager help, home resolution and package metadata. Unsupported
commands stay distinct from successful checks. Review reports before sharing.
This helper is source-based, not a packaged EXE; the startup script has not been
executed on Windows in this release.

The launcher adds customizable columns, order, visibility and settings transfer.
Discovery and bounded artwork caching run off the main thread. Physical-device
functionality and performance are unverified for this new version.

`recovery_probe.py` is a separate opt-in test of **only dev.firecube.probe**. It
requires the disposable recovery APK already installed and an explicit typed
confirmation. Its default mode prints a command preview and performs no ADB
calls. The apply mode writes a durable audit record before each mutation,
checks the device fingerprint before each command, verifies each result, and
stops on the first failure. It never modifies another package. Final enabled
state can be explicit rather than the original default-enabled override; the
journal records this difference rather than claiming exact restoration.

Preview (does not execute commands):

```
python recovery_probe.py --adb PATH_TO_ADB --serial DEVICE:5555 --journal probe-audit.jsonl
```

Only after reviewing the preview and approving this device test, append `--apply`
and type `TEST PROBE` when prompted. If interrupted or a check fails, inspect the
journal. The narrowly scoped recovery command is:

```
adb -s DEVICE:5555 shell pm enable --user 0 dev.firecube.probe
```

A successful probe test does not establish Amazon-package permission, dependency
safety, default-home behavior or stock-launcher recovery. This release does not
remove Alexa, disable existing apps, replace Fire OS, or authorize disabling
Amazon home. Full avoidance of Amazon's home screen remains an unverified
firmware capability, not a promised feature. Do not root or flash this device.


## Version 0.4.0: design and next device test

The launcher adds Midnight, Forest and Plum color themes, a remote-editable home
heading, selected-navigation styling, coordinated focus rings and elevation, a
focused-app caption, and app-information access from the long-press menu. Existing
favorites and settings remain in place on a same-signer `adb install -r` update.
Theme and heading now round-trip with exported settings; older exports use defaults.
These UI changes are build/lint validated, not yet physically tested on the Stick.

[Download Windows helper ZIP](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/v0.4.0/firecube-windows-0.4.0.zip)

Extract the helper and double-click `Start-Firecube.cmd`. Locate official ADB and
enter the connected device identifier. **Test disposable app disable/enable…**
shows the exact commands and requires typing `TEST PROBE`; cancelling performs no
mutation. Install the separately supplied recovery-test APK first. This feature
never disables Amazon home, Alexa, existing apps or streaming packages. It locks
the device fields during the test and saves a durable audit. Share the resulting
JSONL log after reviewing its device address. Do not treat a successful ordinary
app test as permission to disable system apps. Windows execution is still pending.

See [observed firmware compatibility](docs/device-compatibility.md) and the
[device test walkthrough](docs/next-steps.md). No modern default-home command is
advertised in the supplied Fire OS 5 pm usage. The Home button still opens Amazon
home according to the user's physical-device test. No claim of full replacement
is made, and no stock-launcher-disable instructions are supplied.


## Consolidated acceptance build 0.5.0

[Download acceptance helper ZIP](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/v0.5.0/firecube-windows-0.5.0.zip)

This is a test candidate, not a 1.0 readiness claim. The launcher has a static
ambient backdrop, compact typography/navigation and responsive 16:9 artwork
spaces. Existing themes, heading, favorites and ordering are preserved when
updating in place with the same signing key. See [one-round acceptance
instructions](docs/acceptance-round.md).

In the Windows helper, **Acceptance checklist** collects explicit user results
for all eight streaming apps, navigation, settings, design and reboot persistence.
**Export one acceptance bundle…** reads fresh diagnostics, captures the current
TV screen, and optionally includes a selected disposable-probe audit. It makes
no device changes. Keep Firecube visible if the screenshot should show the design.
The ZIP contains acceptance.json, device-diagnostics.json, an optional PNG and an
optional probe audit. Review identifiers and visible content before sharing.
Failed screenshot capture is recorded without inventing an image. Unrun, failed,
unavailable and passed checks stay distinct. Imported audit claims are not
independently authenticated and never authorize broader device changes.

The export includes process/CPU snapshots and metadata for installed streaming,
Alexa-review and ordinary non-system packages. Snapshots are not performance
benchmarks. Unsupported commands stay explicit. A failed export can leave an
incomplete file; discard it and choose a new filename after diagnosing the error.

Remaining full-scope blockers: actual Alexa cleanup, existing-app disabling and
restoration, and verified Home-button replacement with recovery. The helper
reports these as unresolved even if every manual launcher check passes. Nothing
in this release disables Amazon home or modifies existing applications.


## Root/firmware assessment and optional Home-redirect trial

The user's scope now allows research into root and firmware options. See the
[exact-device assessment](docs/definitive-options.md) for tested facts, source
links and unresolved physical eligibility. The located software-root port guards
build 688805020; this unit is 688806320. It must not be run with its guard removed.
A tank bootloader-unlock route is documented but not verified for this physical
unit; its scripts write boot-critical storage. LineageOS conversion has reported
streaming limitations and is not a verified replacement for this keep list.

[Download reversible Home Bridge trial](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/home-bridge-0.1.1/firecube-home-bridge-trial-0.1.1.zip)

The optional trial uses a separate paused-by-default accessibility app. It asks
for a typed confirmation, saves existing settings, adds only its service, verifies
one Home event and attempts rollback on failure. It does not disable packages,
remove Amazon home, change Alexa, obtain root or flash anything. Its receipt and
result bundle keep successes, denials and unresolved rollback states distinct.
No extra Python dependencies are needed beyond Python 3.13 and official ADB.
Follow the [trial and rollback instructions](docs/home-bridge-trial.md). The APK
build/lint/signature and mocked safety checks pass; physical compatibility and
Windows execution remain unverified. A single successful redirect is not full
home replacement, root, or a reboot/streaming acceptance result.


### Home Bridge helper 0.1.1

Fixes a legacy ADB install-handling bug: successful installs can emit file-push
progress on stderr. The helper now uses exit status and explicit error markers,
retains both streams for install diagnosis, and still rejects permission denials
and zero-exit package failures. The bridge APK remains 0.1.0 with the same SHA-256;
this is a Windows/Python helper fix, not a new Android behavior change.

If a 0.1.0 receipt ended at install_intent/failed with only a file-push progress
line, it did not reach accessibility writes. APK installation may have succeeded.
Extract 0.1.1 into a new folder, keep the old receipt and rerun Run-Home-Bridge.cmd.
The -r install uses the same signed APK; no Firecube update or full acceptance
retest is needed. Share the new bridge-result ZIP to assess actual device behavior.


## Query-only Home API inspector

The complete user trial showed service-list write/readback failure followed by
verified restoration to the original empty list and disabled accessibility flag.
No Home event was tested. The shell package also reports SET_PREFERRED_APPLICATIONS,
which warrants inspecting the separate Android 5.1 preferred-Home API without
calling a setter. This is a lead, not proof that Fire OS allows a default change.

[Download Home Inspector](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/home-inspector-0.1.0/firecube-home-inspector-0.1.0.zip)

Extract and run Run-Home-Inspector.cmd, then share the resulting home-inspection
ZIP. No app installation, settings writes, Home key injection, root or firmware
operation is performed. A verified code container is copied to /data/local/tmp and
queried through app_process at shell UID 2000. The container is not installed.
The query gateway rejects all mutation method names. It reports individual query
errors without claiming unsupported interfaces work. See
[mechanism, evidence and instructions](docs/home-inspection.md).


## Preferred Home trial from the confirmed permission/candidate report

The user report now confirms the private Android 5.1 Home API is exposed,
SET_PREFERRED_APPLICATIONS is effectively granted to the shell, and Firecube is
an enabled Home candidate. Current preferred Home is null, saved Home filters are
empty, and resolution still returns Amazon. These observations justify a guarded
preferred-Home experiment; they do not prove the setter or physical Home works.

[Download preferred-Home trial](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/preferred-home-0.1.0/firecube-preferred-home-trial-0.1.0.zip)

Extract and run Set-Firecube-Home.cmd. Its typed confirmation approves only the
fixed Firecube Home preference for user 0 and one injected Home test. It refuses
existing Home/Firecube defaults, saves a device-bound baseline before mutation,
verifies results and attempts scoped rollback if unsuccessful. The supplied
Restore-Original-Home.cmd restores the query-visible original empty preference
and Amazon fallback, provided no unrelated Firecube defaults were introduced.
It never resets other apps' defaults or disables Amazon packages.

No app installation, accessibility modification, root or firmware flashing is
performed. Keep the local audit, remote backup and pointer file for restoration.
The result ZIP is the single next evidence package. See
[exact operation and rollback instructions](docs/preferred-home-trial.md).


## Next Home mechanism: PC-assisted activity events

The preferred-Home setter accepted Firecube, but Home resolution stayed Amazon;
the trial verified rollback. The accessibility trial also restored its baseline.
The independent next experiment watches fresh user-0 Amazon Home resume events
via ADB and explicitly opens Firecube only while Amazon Home is foreground.

[Download the Home event trial](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/home-events-0.1.1/firecube-home-events-trial-0.1.1.zip)

Extract and run Test-Home-Events.cmd. Review and type TEST HOME EVENTS. Keep the
PC connected for the approximately 90-second trial; after automatic success,
try remote Home from a streaming app. Upload the home-events-result ZIP.
It installs nothing, changes no system settings, and stops automatically.
Amazon Home normally returns once monitoring ends. This is an unverified,
PC-dependent experiment, not autonomous startup, Alexa removal or root.
See [details and current firmware constraints](docs/home-event-trial.md).


## Device-side Home candidate and optional reboot startup

[Download the combined observer + boot-controller bundle](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/device-observer-0.1.0/firecube-device-home-candidate-0.1.0.zip)

The user's last event trial verified two Home redirects before its PC stream
closed. This candidate moves the observer onto the Stick, isolates its Unix
session, verifies a device-side Home test, and supplies Start, Stop and Status
commands. A locked runtime directory, duplicate-process lock, foreground checks,
loop protection and bounded stream reconnection are included. No root or package
disabling is performed. The launcher does not need another upgrade.

Start-Device-Observer.cmd performs setup and verification for this boot. Test
with the PC disconnected before calling it independent. Install-Boot-Helper.cmd
optionally installs Firecube Home Controller; on-TV Pair / Start requests a
separate local ADB authorization. Boot start defaults off and must be enabled
explicitly after pairing. The helper connects only to 127.0.0.1:5555, retains a
private RSA key, and uses only fixed observer control commands. That key grants
ADB shell trust; it is not a cloud permission or a root grant.

Disconnect the PC, test streaming/Home, then enable the optional controller and
test a normal reboot. Reconnect for Observer-Status.cmd reports. New device-side,
local-pairing and reboot behavior remain unverified until those results return.
Amazon/Alexa removal remains blocked by the existing privilege limitations.
See [combined setup, acceptance and recovery](docs/device-observer.md).
