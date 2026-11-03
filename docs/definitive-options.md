# Exact-device assessment and next decisive test

This assessment separates observed facts from upstream claims and missing device
tests. Broad user authorization now permits researching root and firmware paths.
No exploit, flash, hardware short, root installation or device-side trial has
been executed from this cloud task. The environment still has no VPN/TCP grant
to the Stick. Physical and Windows-side steps require the user's local machine.

## Confirmed on this device

- AFTT/tank, Android 5.1.1/API 22, Fire OS 5.2.9.5 build 688806320.
- Shell UID 2000. The disposable-app disable-user command throws a permission
  denial; its later user-0 enabled override matches the original 0.
- No set-home-activity command is advertised in the supplied pm usage.
- Opening Android home settings did not make physical Home open Firecube.
- The user reports 14 manual acceptance passes. Amazon home was visible in the
  supplied acceptance screenshot. None of these establishes post-root playback.

## Route 1: privileged app control through ordinary ADB

The tested disable-user route is blocked. A GUI wrapping that same command does
not gain privileges. This does not prove every hypothetical method impossible;
it rules out claiming this tested workflow can disable Alexa or Amazon home.
Official settings can still be used for actions actually exposed there.
Uninstall/hide operations have different permission checks; a disable-user denial
must not be presented as proof that every other package operation is impossible.
The trial result bundle collects the shell package's permission report for that
assessment, without trying those mutations or claiming reversibility for system
packages. User-specific system uninstall is not an approved substitute without a
verified restoration path, particularly since install-existing is not advertised.

## Route 2: non-root Home redirection

LauncherHijack historically documents Fire TV support, but is deprecated and
reports package blocking. Its code uses accessibility and other Home-detection
mechanisms. Historical support is not a compatibility result for this unit.

Sources read:
- https://github.com/BaronKiko/LauncherHijack/blob/master/README.md
- https://github.com/BaronKiko/LauncherHijack/blob/master/HELP.md
- https://github.com/BaronKiko/LauncherHijack/blob/master/app/src/main/java/com/baronkiko/launcherhijack/AccServ.java

The new independent Firecube Home Bridge is an experimental window-only trial,
not a claim that LauncherHijack or Home interception works. It watches only
Amazon launcher's two known Home activity names, requests no screen-content
retrieval, no key filtering, no microphone, network or overlay permission, and
starts paused. On an eligible event it asks Android to open Firecube. It can
show Amazon home briefly and leaves Amazon home running. It cannot remove Alexa.

The local trial preserves both accessibility settings, keeps other services,
verifies readbacks, then resumes our bridge and presses Home once. It polls the
foreground and records what it actually sees. On failure it pauses our app and
attempts an exact saved-settings rollback, refusing to overwrite outside changes.
It checks a stable device identity and fingerprint, scopes changes to user 0,
and verifies the exact bundled APK hash before installing. No root, package
disabling or firmware writes are included. Rollback itself can fail; the receipt
distinguishes verified restoration from an unresolved rollback.

This trial requires the user's PC. A build/lint pass is not a device result.
Its foreground observation is a single trial, not proof of reboot persistence,
latency, long-press behavior or complete elimination of Amazon components.

## Route 3: software root on the exact firmware

The GhostLock project explicitly targets AFTT/tank on Fire OS 5.2.9.5, but only
incremental build 288.6.8.8_user_688805020. This unit is 688806320. The README and
require_build check restrict the build because the payload uses fixed addresses.
Do not remove the guard, assume shared version names imply shared layouts, or
claim it supports this unit. The underlying CVE's existence does not verify this
vendor build's exploitability or the port's reliability.

Sources read:
- https://github.com/Anezium/ghostlock-firetv-tank/blob/main/README.md
- https://github.com/Anezium/ghostlock-firetv-tank/blob/main/scripts/gl_bench.py
- https://github.com/Anezium/ghostlock-firetv-tank/blob/main/scripts/gl_root.py
- https://github.com/CVEProject/cvelistV5/blob/main/cves/2026/43xxx/CVE-2026-43499.json

Conclusion: no exact-build-verified software root tool was established in this
investigation. This is not a mathematical proof that root is impossible. Porting
an exploit would be new build-specific research, not installing a verified tool.

## Route 4: hardware bootloader unlock, retaining Fire OS

The tank-convert project supplies a tank Amonet kit and links the original unlock
thread. Its source writes boot-critical data, including preloader and RPMB. This
is not a read-only detector. Do not start it just to check eligibility or follow
advice to comment out downgrade checks.

A separate author's report describes hardware unlocking a different tank unit,
on build 688805020, retaining Fire OS, adding root and changing Home. That is a
useful device-family lead, not independent verification of this user's hardware.
The report explicitly leaves real video playback and remote use untested.
Eligibility depends on physical bootrom access and the particular board/unit;
neither is established by model name, kernel version or a recent OTA alone.

Sources read:
- https://github.com/kerta1n/tank-convert
- https://github.com/kerta1n/tank-convert/blob/main/amonet-tank-v1.2.2/amonet/modules/main.py
- https://github.com/chaosmaster/amonet/tree/mt8127-tank
- https://github.com/Anezium/ghostlock-firetv-tank/blob/main/docs/RESULTAT-ROOT-DEBLOAT.md

Primary XDA thread identified, but its request was denied by the environment's
CONNECT policy (HTTP 403); it was not read or independently validated here:
https://xdaforums.com/t/unlock-root-twrp-unbrick-fire-tv-stick-2nd-gen-tank.3907002/

The hardware route requires local physical access, correct board identification,
proper tools and a validated recovery/backup plan before any write. It can damage
or brick the device. Rooted stock Fire OS may also change streaming-app behavior;
the eight required services need post-change testing. It is not remotely verified.

## Route 5: replace Fire OS with LineageOS

The tank-convert README documents a LineageOS 12.1/Android 5.1 conversion, warns
that a newer device tree's completeness is unconfirmed, and reports Netflix,
Disney+ and other app-availability/playback problems. It also documents remote
compatibility/setup limitations. Therefore this is not an established way to
preserve this user's eight working streaming services. It is a separate tradeoff,
not the recommended first route for a daily streaming device.

## Current verdict

Full Amazon removal is NOT verified on this exact unit. Known ADB mutations are
blocked; the discovered software exploit excludes this build; hardware unlock
remains a physical eligibility question. Home redirection has a separate,
reversible trial, but cannot itself remove the Amazon launcher or Alexa.

The next actionable software test is the scoped Home Bridge trial. To obtain a
definitive hardware-unlock result for this physical unit requires local hardware
inspection and a non-flashing USB/bootrom eligibility assessment by a competent
operator. More app restyling cannot settle that question. No stock-launcher
corruption, exploit-guard bypass or unverified firmware image is part of this plan.
