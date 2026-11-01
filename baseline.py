"""Validate imported reports without trusting their metadata as instructions."""
import json
import re
from pathlib import Path


def load_report(path):
    path = Path(path)
    if path.stat().st_size > 10_000_000:
        raise ValueError("Report exceeds the 10 MB limit")
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise ValueError("Expected a version 1 baseline")
    properties = report.get("properties")
    if not isinstance(properties, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in properties.items()):
        raise ValueError("Invalid device properties")
    packages = report.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("Report contains no package inventory")
    seen = set()
    for item in packages:
        if not isinstance(item, dict):
            raise ValueError("Invalid package entry")
        name = item.get("package")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", name):
            raise ValueError("Invalid package identifier")
        if name in seen:
            raise ValueError("Duplicate package identifier")
        seen.add(name)
        if type(item.get("system")) is not bool or type(item.get("enabled")) is not bool:
            raise ValueError("Package states must be true or false")
    return report
