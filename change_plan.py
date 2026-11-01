"""Preview-only selection policy. No commands are executed by this module."""
from safety import assess

KEEP = {
    "com.netflix.ninja", "com.amazon.firetv.youtube", "org.chromium.youtube_apk",
    "com.cbs.ott", "com.hulu.plus", "com.hbo.hbonow", "com.wbd.stream",
    "com.disney.disneyplus", "com.plexapp.android", "com.peacocktv.peacockandroid",
    "dev.firecube.launcher",
}

# Observed identifiers, not assertions that these packages can safely be disabled.
ALEXA_REVIEW = {
    "com.amazon.alexa.datastore.app", "com.amazon.alexa.externalmediaplayer.fireos",
    "com.amazon.alexamediaplayer.runtime.ftv", "com.amazon.alexashopping",
    "com.amazon.tv.alexaalerts", "com.amazon.tv.alexanotifications",
    "com.amazon.vizzini", "com.ivona.orchestrator", "com.ivona.tts.oem",
}


def preview(report):
    rows = []
    for package in report["packages"]:
        name = package["package"]
        if name in KEEP:
            status = "keep"
        elif assess(package)["protected"]:
            status = "protected"
        elif name in ALEXA_REVIEW:
            status = "Alexa investigation: dependencies and recovery unverified"
        elif package["system"]:
            status = "system: review required"
        else:
            status = "optional app: user selection and recovery test required"
        rows.append({"package": name, "status": status, "commands": [], "apply_allowed": False})
    return rows
