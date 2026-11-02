"""Conservative interpretation of read-only firmware evidence."""
import re


def summarize(evidence):
    help_result = evidence.get("package_manager_help", {})
    raw_help = help_result.get("output", "")
    # Some older pm versions return an error status while printing valid usage.
    # Retain advertised syntax without calling the command or permission successful.
    help_text = raw_help if help_result.get("ok") or re.search(r"(?im)^\s*usage:\s*pm\b", raw_help) else ""
    resolution = evidence.get("home_resolution", {})
    text = resolution.get("output", "") if resolution.get("ok") else ""
    matches = re.findall(r"(?m)^\s*([A-Za-z0-9_.]+/[A-Za-z0-9_.$]+)\s*$", text)
    # A single component is an observation of intent resolution, not physical Home-key behavior.
    component = matches[0] if len(matches) == 1 else None
    return {
        "resolved_home_component": component,
        "pm_set_home_advertised": bool(re.search(r"(?m)^\s*(?:pm\s+)?set-home-activity\b", help_text)),
        "pm_disable_user_advertised": bool(re.search(r"(?m)^\s*(?:pm\s+)?disable-user\b", help_text)),
        "pm_default_state_advertised": bool(re.search(r"(?m)^\s*(?:pm\s+)?default-state\b", help_text)),
        "home_button_verified": False,
        "reboot_verified": False,
        "recovery_verified": False,
        "stock_launcher_disable_allowed": False,
        "explanation": "Help advertises syntax only. Default-home permission, remote Home behavior, reboot behavior and recovery require device tests. Keep Amazon home enabled.",
    }
