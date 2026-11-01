# Firecube — Fire TV tools

Read-only Windows inventory tools and an API 22 Android launcher prototype.
The supplied device baseline confirms a Fire TV Stick 2nd generation (AFTT),
Fire OS 5.2.9.5 (688806320), API 22, with non-root ADB. The Windows collector
and viewer have been exercised by the user; the Android APKs are not yet
device-tested. Package mutation and Home-button replacement are unverified.

## Download debug APKs

- [Firecube launcher 0.1.0](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/v0.1.0/firecube-launcher-0.1.0-debug.apk)
- [Recovery-test app 0.1.0](https://github.com/steinja03/firecube/raw/refs/heads/main/downloads/v0.1.0/firecube-recovery-test-0.1.0-debug.apk)
- [SHA-256 checksums](downloads/v0.1.0/SHA256SUMS)

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
