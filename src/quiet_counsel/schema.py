"""A structural check of a scorecard, standard library only.

The JSON Schema in scorecard.schema.json is the contract for other tools. This module checks
the parts the dashboard depends on, so a malformed card is refused with a reason instead of
rendering as a page that looks fine and says something false.
"""

DIMENSIONS = ("A1", "A2", "A3", "A4", "B1", "B2", "B3", "C1", "C2", "C3", "C4",
              "D1", "D2", "E1", "E2", "E3")
GROUPS = {"A": "methodology", "B": "evidence", "C": "safety", "D": "integrity", "E": "product"}
SEVERITIES = ("critical", "serious", "warning", "info")
BANDS = ("blocked", "review", "shortlist", "screened")
CONFIDENCE = ("measured", "judged", "unverified")
CLAIM_STATUS = ("confirmed", "unsupported", "contradicted", "unchecked")


def problems(card):
    """Return a list of human-readable problems; an empty list means the card is usable."""
    out = []
    for key in ("schema", "project", "mode", "signals", "flags", "dimensions"):
        if key not in card:
            out.append(f"missing top-level key: {key}")
    if out:
        return out
    if card["schema"] != "scorecard/1":
        out.append(f"unknown schema: {card['schema']!r}")
    if card["mode"] not in ("screen", "deep"):
        out.append(f"unknown mode: {card['mode']!r}")
    for key in ("name", "path", "measured_at"):
        if key not in card["project"]:
            out.append(f"project.{key} missing")
    for name, sig in card["signals"].items():
        if "value" not in sig:
            out.append(f"signal {name} has no value")
        if not sig.get("command"):
            out.append(f"signal {name} does not say how it was measured")
    for f in card["flags"]:
        if f.get("severity") not in SEVERITIES:
            out.append(f"flag {f.get('id')} has severity {f.get('severity')!r}")
        if not f.get("evidence"):
            out.append(f"flag {f.get('id')} carries no evidence")
    seen = set()
    for d in card["dimensions"]:
        did = d.get("id")
        if did not in DIMENSIONS:
            out.append(f"unknown dimension {did!r}")
            continue
        seen.add(did)
        if d.get("group") != GROUPS[did[0]]:
            out.append(f"{did} is in group {d.get('group')!r}, expected {GROUPS[did[0]]!r}")
        if d.get("applicable") is False and not d.get("na_reason"):
            out.append(f"{did} is marked not applicable with no reason")
        score = d.get("score")
        if score is not None:
            if not 0 <= score <= 10 or (score * 2) != int(score * 2):
                out.append(f"{did} score {score} is not 0 to 10 in halves")
            if card["mode"] == "screen":
                out.append(f"{did} is scored in a screen pass, which never scores")
            if not d.get("evidence"):
                out.append(f"{did} is scored with no evidence")
        if d.get("confidence") not in CONFIDENCE:
            out.append(f"{did} confidence {d.get('confidence')!r}")
    missing = [d for d in DIMENSIONS if d not in seen]
    if missing:
        out.append(f"dimensions missing: {', '.join(missing)}")
    band = card.get("totals", {}).get("band")
    if band is not None and band not in BANDS:
        out.append(f"unknown band {band!r}")
    for c in card.get("claims", []):
        if c.get("status") not in CLAIM_STATUS:
            out.append(f"claim {c.get('claim')!r} has status {c.get('status')!r}")
    return out
