"""Read-only firmware evidence collector. Does not test mutations on real packages."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from inventory import collect, run
from change_plan import preview, ALEXA_REVIEW
from home_compat import summarize


def capture(adb, serial):
    baseline = collect(adb, serial)
    evidence = {}
    commands = [
        ("package_manager_help", ["pm", "help"]),
        ("users", ["pm", "list", "users"]),
        ("home_resolution", ["pm", "resolve-activity", "--brief", "-a",
                             "android.intent.action.MAIN", "-c", "android.intent.category.HOME"]),
        ("storage", ["df", "/data"]),
        ("memory", ["cat", "/proc/meminfo"]),
        ("launcher_memory", ["dumpsys", "meminfo", "dev.firecube.launcher"]),
    ]
    names = {p["package"] for p in baseline["packages"]}
    for name in sorted((ALEXA_REVIEW | {"com.amazon.tv.launcher", "dev.firecube.launcher"}) & names):
        commands.append((name, ["dumpsys", "package", name]))
    for label, args in commands:
        try:
            evidence[label] = {"ok": True, "output": run(adb, serial, "shell", *args)}
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            evidence[label] = {"ok": False, "error": str(error)}
    return {
        "schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
        "baseline": baseline, "read_only": True, "evidence": evidence,
        "preview": preview(baseline),
        "home_compatibility": summarize(evidence),
        "limitations": "Help text is not proof of mutation permission. No package changes were tested.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = capture(args.adb, args.serial)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Diagnostics stopped: {error}\n")
    print(f"Saved read-only evidence to {args.output}")


if __name__ == "__main__":
    main()
