"""Turn a scorecard and release gate result into a deterministic release verdict."""

import hashlib
import json

from . import __version__


def reason(rule, flag=None):
    ref = next((e.get("ref", "") for e in (flag or {}).get("evidence", [])
                if e.get("kind") == "file"), "")
    path, sep, line = ref.rpartition(":")
    return {"rule": rule, "flag_id": (flag or {}).get("id"),
            "file": path if sep and line.isdigit() else (ref or None),
            "line": int(line) if sep and line.isdigit() else None}


def make(card, scorecard_bytes, gate_status="missing"):
    """Apply the worst matching row in the documented verdict table."""
    reasons = []
    levels = []
    for flag in card.get("flags", []):
        # The test-path versions of the directed-text and copyleft flags carry their own lower
        # severity. A flag the project's own ignore file lowered keeps its original severity here,
        # until a person approves the downgrade.
        excluded = bool(flag.get("excluded") and flag.get("original_severity"))
        severity = flag.get("original_severity") if excluded else flag.get("severity")
        level = {"critical": 3, "serious": 2, "warning": 1}.get(severity)
        if level:
            levels.append(level)
            reasons.append(reason(f"{severity} flag" + (" excluded by the project's ignore file" if excluded else ""), flag))
    if gate_status == "failed":
        levels.append(3)
        reasons.append(reason("gate failed"))
    project = card.get("project", {})
    return {"schema": "verdict/1", "verdict": ("PASS", "PATCH", "MINOR", "MAJOR")[max(levels, default=0)],
            "scorer_version": __version__, "scorecard_sha256": hashlib.sha256(scorecard_bytes).hexdigest(),
            "reasons": reasons, "tag": project.get("tag"), "commit": project.get("commit")}


def render(result):
    return (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
