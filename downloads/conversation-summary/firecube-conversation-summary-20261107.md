# Firecube conversation and project summary

Prepared November 7, 2026. Local IP address and Windows username omitted from this published copy. This summarizes the conversation and reported results; it is not a new device inspection.

## Goal and user preferences

Build a modern, sleek Fire TV home screen and reduce unnecessary apps/processes, ideally without depending on Amazon’s launcher. The user specifically wants Alexa removed.

Preserve Netflix, YouTube, Paramount+, Hulu, Max/HBO Max, Disney+, Plex, and Peacock. Preserve working streaming playback and remote navigation.

The user authorized implementation and research into launcher interception, root, and firmware options, explicitly broadening the original brief’s restrictions on exploits and firmware modifications. That authorization does not establish compatibility with any particular exploit or firmware image. No root exploit, bootloader unlock, firmware flash, or hardware modification was executed.

## Project and access

- Repository: https://github.com/steinja03/firecube
- Local repository: `/workspace/firecube`
- Changes and download bundles were uploaded to GitHub `main`.
- Latest delivered commit: `44bb8a7` — detached device Home observer and optional local ADB boot controller.
- The cloud environment was published earlier by the user. The user instructed that previous changes not be reapplied or the environment republished. This work did not republish it.
- The user explored Tailscale and Codex permissions. During the later work, the cloud environment had no configured VPN/TCP access to the Stick. Device operations therefore ran through scripts on the user’s Windows PC, followed by uploaded reports. Codex permissions alone do not grant access to the user’s PC or local network.

## Device established in the conversation

| Item | Observed value |
|---|---|
| Device | Fire TV Stick, second generation |
| Model / codename | AFTT / tank |
| Fire OS | 5.2.9.5 |
| Firmware build | 688806320 |
| Android | 5.1.1, API 22 |
| Fingerprint | `Amazon/full_tank/tank:5.1.1/LVY48F/288.6.8.8_user_688806320:user/release-keys` |
| ADB identity | UID 2000, shell; not root |
| Last reported ADB endpoint | `YOUR_STICK_IP:5555` — local address omitted from this download |
| Active user | User 0; secondary user 10 was present but not running |

Windows ADB location used:

`C:\Users\YOUR_USERNAME\Downloads\platform-tools-latest-windows\platform-tools\adb.exe`

Python 3.13 was installed for the project. Python 3.15 was also present. PySide6 6.10.2 installed successfully for the desktop companion.

## Early setup and inventory

Several PowerShell commands were accidentally pasted together, producing parser errors. Missing Python and missing script files caused additional setup problems. Artifact downloads also failed repeatedly, motivating directly created scripts and later GitHub-hosted downloads.

The inventory script initially rejected blank package-list lines. After correcting that parser, it saved a baseline of **217 packages**:

`stick-baseline-20261101-162710-475581.json`

That baseline records package states; it is not an app-data, APK, or firmware backup. No package restoration capability was inferred merely from having the inventory.

The Windows companion opened and the user reported its functions working.

## Launcher delivered

The latest installed launcher discussed was **Firecube 0.5.0**, implemented with Kotlin/Android Views for API 22.

Features include:

- Static gradient background and artwork cards.
- Three dark color themes and a custom Home heading.
- Clock/date and configurable grid columns.
- Favorites, hiding, ordering, and app information controls.
- Settings export/import and device-settings access.

The user confirmed color themes and the heading worked and supplied acceptance results reporting 14 manual checks passing. These reports do not establish later reboot interception, rooted playback, or every installed streaming package’s identity. Peacock was requested and reported passing manually, but its installed package was not independently identified in the earlier inventory assessment.

Opening Firecube manually worked. The physical Home button continued returning to Amazon. Screenshots showed both the Amazon screen and an earlier plain Firecube layout, prompting the subsequent visual improvements and Home-routing work.

## Compatibility findings and experiments

### 1. Package disabling

A disposable probe package, `dev.firecube.probe`, was used to assess package-state control. `pm disable-user --user 0` failed with a permission-denial SecurityException. Later inspection showed its enabled override unchanged from the original state.

Effective permission checks showed:

- `SET_PREFERRED_APPLICATIONS`: granted.
- `WRITE_SECURE_SETTINGS`: granted by the permission check; this alone did not prove every settings write would take effect.
- `CHANGE_COMPONENT_ENABLED_STATE`: denied.

The tested disabling route cannot remove Alexa or disable Amazon Home. Uninstall/hide are separate mechanisms and were not automatically declared impossible from that one denial, but no verified system-package removal/restoration workflow was established. No Amazon or Alexa package was disabled or removed by the delivered work.

This Fire OS also lacks several newer Android command interfaces: `cmd` was unavailable, and the supplied package-manager usage did not advertise `set-home-activity`. Missing CLI commands were not treated as proof that the underlying Android API was absent.

### 2. Accessibility Home Bridge

An experimental, paused-by-default accessibility bridge was delivered as `dev.firecube.homebridge`. It watched known Amazon Home activity names and requested Firecube launch without screen-content retrieval or key filtering.

The completed trial installed the bridge and verified it was paused. The accessibility-service setting write failed its readback. Rollback verified the original empty service list and accessibility flag `0`; the bridge remained installed and paused. No successful Home interception was established through this route.

An earlier installer-wrapper bug incorrectly treated ordinary ADB progress on stderr as failure. That was fixed before the completed bridge result was assessed.

### 3. Read-only Home API inspection

A checksum-verified temporary tool queried the actual Android Home interfaces as shell UID 2000 without installing an app or changing Home settings.

It confirmed:

- Firecube was an enabled/exported Home candidate.
- The preferred-Home setter interface existed.
- Shell had the preferred-app permission.
- No saved Home preference was present initially.
- Home resolution still returned `com.amazon.tv.launcher/.ui.HomeActivity_vNext`.

The Amazon activity’s enabled metadata and actual resolution were not treated as grounds to alter component states.

### 4. Preferred-Home trial

A guarded trial saved a device-bound baseline and called Android’s preferred-Home API for the fixed Firecube component.

**Actual result:** Firecube was successfully stored as the preferred Home component, but `resolveIntent` still returned Amazon. The trial therefore stopped before injecting Home and cleared only its newly created preference. Rollback verified the original empty preference and Amazon resolution.

This proves that saving the preference was permitted. It does not prove a physical Home-key test occurred while that preference was active, or that shell lacked the setter permission.

### 5. PC-assisted Home event trials

A different mechanism watched fresh user-0 `am_resume_activity` log events. It acted only on exact Amazon Home components, rechecked the foreground, and explicitly launched Firecube. It did not require accessibility activation or a preferred-Home write.

The first returned report stopped before monitoring because the immediate initial foreground check did not see Firecube. Version 0.1.1 added a bounded wait and launch/foreground evidence; a timing race was possible, not proven.

The next report, `home-events-result-20261106-132003-392196.zip`, established:

1. Firecube opened and became foreground.
2. A fresh log marker was observed.
3. The injected Home key brought Amazon Home forward.
4. The monitor launched Firecube and verified its foreground.
5. A second Amazon Home event was also redirected, with Firecube foreground verified.
6. The log stream later closed and the trial ended with an error.

**Confirmed:** two successful event-driven Home redirects. **Not established:** sustained device-only operation, reboot persistence, the source of the second Home event, or Netflix playback success. The user’s earlier report that opening Netflix returned to Amazon was associated with a trial in which monitoring had not started; its cause was not established.

## Latest deliverable: combined device Home candidate

Download:

https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/device-observer-0.1.0/firecube-device-home-candidate-0.1.0.zip

Full setup, behavior, and recovery:

https://github.com/steinja03/firecube/blob/main/docs/device-observer.md

The bundle contains:

- `Start-Device-Observer.cmd`
- `Stop-Device-Observer.cmd`
- `Observer-Status.cmd`
- `Install-Boot-Helper.cmd`
- Device observer tool and optional boot-controller APK.
- Python controls, tests, instructions, and third-party notice.

### Device-side observer

The observer is designed to run as shell on the Stick in a detached Unix session, rather than leaving the PC to monitor logs. It is scoped to the exact inspected firmware and uses:

- A private runtime directory and a lock preventing duplicate observers.
- Fresh log readiness markers and user-0 Amazon Home matching.
- Foreground rechecks and verified Firecube launches.
- Reconciliation when Amazon Home is already visible at startup.
- Bounded reconnect attempts for a closed log stream.
- Loop/burst protection, command timeouts, stop signaling, and bounded status storage.

The Windows start script requires a new ready session and an increased native redirect count plus Firecube foreground before calling its Home test successful. Failure attempts to stop the new observer and records whether stopping was verified.

The tool container is copied to `/data/local/tmp`; it is not installed as an Android application. Existing launcher settings remain unchanged.

### Optional boot controller

`Firecube Home Controller` is a separate installed Android app. It requests network and boot-completed permissions, connects only to **127.0.0.1:5555**, and implements fixed observer start/status/stop commands.

The app generates a private RSA key in its own private, non-backed-up storage. The user must use **Pair / Start** and approve the device-local ADB authorization if prompted. That key grants ADB shell trust; it is separate from Codex/cloud permissions and does not grant root. Private keys are not included in support reports.

**Boot start defaults off.** After successful pairing, the user can explicitly enable it. The service makes finite startup attempts after boot. Local ADB availability, retained authorization, boot broadcast delivery, and detached-process survival must all work on this firmware. The helper does not bypass the package-disable permission denial.

The current build prevents an old pre-reboot ready status from counting as a newly started observer session.

### Validation completed in the cloud

- 82 Python tests passed.
- 10 native unit tests passed, including observer policy, ADB framing, RSA format/signature, and stale-session checks.
- Both Android builds and lint passed.
- APK signature checks passed.
- Extracted bundle tests and pinned payload hashes passed.
- A fresh GitHub checkout verified all published download checksums.

**These checks do not replace the physical device tests. No user result for this combined candidate had been received when this summary was written.**

## Next combined device test

1. Extract the whole latest bundle and run `Start-Device-Observer.cmd`.
2. After its Home test passes, disconnect the PC and test streaming plus remote Home without rebooting.
3. Reconnect and collect an `Observer-Status.cmd` report.
4. Optionally run `Install-Boot-Helper.cmd`; on TV, pair the local ADB key and explicitly enable boot start.
5. Disconnect the PC again, reboot normally, and test streaming/Home, then sleep/wake.
6. Reconnect and collect another status report. Upload the generated `observer-result-*.zip` files together with the manual results.

If a stage fails, preserve its report and stop there. No additional launcher APK upgrade is required for this candidate.

### Recovery

On TV, turn boot start off in Firecube Home Controller and choose **Stop**. Turning off the switch alone does not end an existing observer.

The PC Stop command ends the current shell observer and verifies lock release; it cannot change the controller’s private boot-start toggle. A reboot ends the shell session, but an enabled, working controller can start it again. If needed, force-stop or uninstall the controller in Fire OS application settings before rebooting. Amazon remains available.

## Root, firmware, and full Amazon-removal status

The reviewed GhostLock software-root project targets tank build **688805020**, whereas this Stick is **688806320**. Its fixed-address build guard must not be removed. No compatible, ready-to-run software-root tool was established for this exact build.

Amonet/tank hardware unlock sources were identified, but physical board/bootrom eligibility and a recovery plan were not established. Those tools write boot-critical data; they were not run as a detector. A primary XDA thread could not be independently read because of an access-policy denial.

LineageOS conversion was not an established fit for preserving all eight requested streaming services; reviewed documentation reported compatibility limitations.

Important distinction:

- A successful observer/controller could provide Home redirection without an always-connected PC.
- It still depends on Amazon Home activity behavior, may briefly show Amazon, and does not stop Amazon’s background processes.
- Alexa and unused system-package removal remain unresolved privilege/recovery work.
- Do not describe the current candidate as accepted 1.0, full Amazon removal, or proven reboot autonomy before the device results establish the relevant behavior.

## Useful repository references

- Device candidate instructions: `docs/device-observer.md`
- Broader compatibility assessment: `docs/definitive-options.md`
- Earlier preferred-Home trial: `docs/preferred-home-trial.md`
- Earlier event trial: `docs/home-event-trial.md`
- Windows device controls: `observer_control.py`
- Native observer: `launcher/observer/`
- Optional reboot controller: `launcher/boothelper/`
- Launcher: `launcher/app/`

The most recent active request before this summary was to move toward the end goal rather than continue small desktop trials. The combined candidate was built and uploaded in response; its next necessary evidence is the batched physical acceptance test above.
