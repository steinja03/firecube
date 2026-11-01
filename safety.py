"""Conservative display policy, not a device-tested disable recommendation."""

CORE = {
    "android": "Android framework package",
    "com.android.systemui": "Android system interface",
    "com.android.providers.settings": "Android settings provider",
    "com.android.settings": "Android settings application",
    "com.android.packageinstaller": "Android package installer interface",
    "com.android.bluetooth": "Android Bluetooth component",
    "com.android.providers.downloads": "Android download provider",
    "com.android.providers.media": "Android media provider",
    "com.android.shell": "Android shell package",
}

# Exact identifiers previously observed in the supplied Fire TV inventory.
# Their internals and dependencies have not been inspected.
FIRE_GUARDS = {
    "com.amazon.tv.launcher", "com.amazon.firehomestarter",
    "com.amazon.fireinputdevices", "com.amazon.tv.keypolicymanager",
    "com.amazon.tv.settings.v2", "com.amazon.tv.settings.core",
    "com.amazon.device.bluetoothkeymaplib", "com.amazon.bluetoothinternals",
    "com.amazon.tv.devicecontrol", "com.amazon.tv.devicecontrolsettings",
    "com.amazon.android.service.networkmonitor", "com.amazon.wifilocker",
}


def assess(package):
    name = package["package"]
    if name in CORE:
        category = "Protected Android component"
        reason = CORE[name] + ". Protected by policy; firmware-specific behavior is unverified."
    elif name in FIRE_GUARDS:
        category = "Protected Fire TV candidate"
        reason = "Exact identifier is on the conservative launcher/input/settings/connectivity guard list. Its role and dependencies are unverified."
    elif package["system"]:
        category = "Unreviewed system package"
        reason = "Reported as system by Android package manager. This does not establish its role or whether it is essential."
    else:
        category = "Unreviewed non-system package"
        reason = "Not reported as system. This does not prove manual installation or that disabling is safe."
    return {
        "category": category, "reason": reason,
        "risk": "Unverified - no disable recommendation",
        "protected": name in CORE or name in FIRE_GUARDS,
        "policy": "Safety display policy v1; not a complete dependency or protection map.",
    }


def details(package):
    assessment = assess(package)
    return (
        f"{package['package']}\n\n"
        f"Category: {assessment['category']}\n"
        f"Basis: {assessment['reason']}\n"
        f"Disabling risk: {assessment['risk']}\n"
        "Name/version/dependencies: not collected.\n"
        "Restoration: unverified. No change controls are available.\n"
        "Alexa is preserved by policy; its complete package set is not identified.\n"
        f"{assessment['policy']}"
    )
