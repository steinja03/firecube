# Observed Fire TV Stick compatibility

Device evidence supplied by the user: AFTT/tank (Fire TV Stick 2nd generation),
Fire OS 5.2.9.5 (688806320), Android 5.1.1/API 22, non-root shell UID 2000.
The supplied baseline contained 217 packages and none disabled at capture time.
These are historical observations, not live status.

Confirmed by user testing:

- Firecube 0.3.0 installs and opens manually; launcher settings operate.
- Opening Android home settings and then pressing remote Home returns Amazon home.
- `am get-current-user`, `cmd`, and `pm help` are unsupported.
- `pm help` still printed pm's usage list. No `set-home-activity` or
  `resolve-activity` command is advertised in that list.
- `pm disable-user` and `pm enable` are advertised, including a user argument.
  Actual mutation permissions and recovery have not been tested.

This rules out assuming the usual modern `cmd package set-home-activity` path.
It does not prove the safety or success of disabling Amazon home. No stock-home
disable, Home interception, accessibility workaround, boot receiver, rooting or
firmware change is included. Android system and playback dependencies remain
required even if another firmware eventually permits a different home UI.

## Next device test

Install the disposable `dev.firecube.probe` recovery APK, then use the audited
probe workflow. Installation and mutations require the user's concrete approval.
Only that package may be disabled/enabled by the workflow. Never substitute an
Amazon or streaming package. Keep a durable audit and stop on the first failure.

If successful, the result demonstrates mutation permission for that one ordinary
app. It does not validate disabling Alexa, system packages or the stock launcher.
If the original probe override was 0 (default), `pm enable` leaves it 1 (explicit
enabled); the report must retain this distinction. Existing app data is not
backed up by package-state reports.

For Alexa, inspect package-level metadata and shared UID/dependency observations
before selecting candidates. Do not equate an Alexa-like name or absence from
favorites with a safe removal. Streaming apps, networking, remote control, input,
settings, HDMI and package management remain protected.
