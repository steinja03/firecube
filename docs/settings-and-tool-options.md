# Fire OS controls and launcher-tool investigation

Target: user-supplied AFTT/tank, Fire OS 5.2.9.5 (688806320), API 22.
Read-only research only. No tool installed, accessibility setting changed,
bootloader unlocked, firmware flashed, or app removed by this investigation.

## Scope clarification

The original pasted brief included “Never use root exploits or firmware
modifications.” The user has questioned this restriction. It is a revisable user
preference, not an immutable platform constraint. Root/bootloader/firmware options
may be researched. Applying them requires a concrete compatible procedure,
recovery assessment and explicit approval; questioning the old restriction does
not itself authorize a destructive firmware operation.

## Built-in controls to review first

Menu availability and labels vary; do not assume every entry exists on Fire OS 5.

- Preferences > Featured Content: disable video/audio autoplay if available.
  This reduces preview activity, not the presence of advertising tiles.
- Preferences > Privacy Settings: review Device Usage Data, Collect App Usage
  Data and Interest-based Ads, if present. These control supported preferences;
  they do not prove all telemetry stops or all ads disappear.
- Applications > Manage Installed Applications: uninstall only ordinary apps the
  user recognizes and chooses as unused. Preserve the requested streaming apps
  and Firecube. Available Uninstall controls are the authority for this path.
- Notification settings: mute unwanted app notifications where supported.

Do not clear streaming-app data, factory reset, corrupt the stock launcher,
remove profiles, or bulk-disable Amazon packages as part of this cleanup.
Existing inventory includes Spotify, Kodi, Firefox, Apple TV, ES File Explorer
and an AT&T/DIRECTV identifier as possible user-review candidates. Their presence
alone does not establish they are unused or safe system dependencies.

## LauncherHijack research

Sources read:
- https://github.com/BaronKiko/LauncherHijack/blob/master/README.md
- https://github.com/BaronKiko/LauncherHijack/blob/master/HELP.md

Upstream documents Fire TV support and an accessibility-service Home interception
approach. It is deprecated, unsupported by its author, and the README reports
Amazon package-name blocking on many devices. Historical claims are not evidence
that this particular 5.2.9.5 firmware supports it. Accessibility permission,
installation, reboot behavior, latency and resource use remain unverified.

The published Fire TV setup writes enabled_accessibility_services directly.
Do not copy that command blindly: it can replace existing enabled services.
A future trial must first read and preserve accessibility_enabled and the whole
enabled_accessibility_services value, identify the exact APK/source and service,
preview an additive change, and provide a rollback to the exact saved values.
No such write has been performed. Keep Amazon home installed/enabled.

The HELP file also contains a destructive tablet launcher-corruption technique.
It is not an approved Fire TV procedure and is excluded from this plan.

## Other tools and firmware work

Tools relying on the same pm disable-user call inherit the tested prerequisite:
our shell attempt to disable dev.firecube.probe was denied. A manager interface
alone does not establish different privileges. Different mechanisms must be
inspected individually rather than assumed equivalent or compatible.

The README at https://github.com/xyzz/amonet describes Fire HD 8 (2018)/karnak,
not this tank Stick. It must not be used as a tank flashing/rooting guide.
No exact-build-compatible root or bootloader procedure is established here.
Further model-specific evidence is needed before any implementation proposal.
