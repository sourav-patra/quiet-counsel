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


def _dim(i, did):
    """The path of a dimension, with its id only when the id is one of the sixteen the tool defines."""
    return f"$.dimensions[{i}]" + (f" ({did})" if did in DIMENSIONS else "")


def problems(card):
    """Return a list of problems, each a JSON path and a rule; an empty list means the card is
    usable. A message never repeats a value from the card (a version string, a flag id, a claim, a
    score): the card is another party's input, so the path says where and the rule says what.
    A signal's name is the one key the path carries, because it is the only way to find that signal."""
    out = []
    for key in ("schema", "project", "mode", "signals", "flags", "dimensions"):
        if key not in card:
            out.append(f"$: missing top-level key {key}")
    if out:
        return out
    if card["schema"] != "scorecard/1":
        out.append("$.schema: is not scorecard/1")
    if card["mode"] not in ("screen", "deep"):
        out.append("$.mode: is neither screen nor deep")
    for key in ("name", "path", "measured_at"):
        if key not in card["project"]:
            out.append(f"$.project.{key}: missing")
    for name, sig in card["signals"].items():
        if "value" not in sig:
            out.append(f"$.signals.{name}: has no value")
        if not sig.get("command"):
            out.append(f"$.signals.{name}: does not say how it was measured")
    for n, f in enumerate(card["flags"]):
        if f.get("severity") not in SEVERITIES:
            out.append(f"$.flags[{n}].severity: is not one of critical, serious, warning, info")
        if not f.get("evidence"):
            out.append(f"$.flags[{n}].evidence: carries no evidence")
    seen = set()
    for n, d in enumerate(card["dimensions"]):
        did = d.get("id")
        where = _dim(n, did)
        if did not in DIMENSIONS:
            out.append(f"{where}.id: is not a dimension the tool defines")
            continue
        seen.add(did)
        if d.get("group") != GROUPS[did[0]]:
            out.append(f"{where}.group: is not the group of {did}")
        if d.get("applicable") is False and not d.get("na_reason"):
            out.append(f"{where}: is marked not applicable with no reason")
        score = d.get("score")
        if score is not None:
            if (not isinstance(score, (int, float)) or isinstance(score, bool)
                    or not 0 <= score <= 10 or (score * 2) != int(score * 2)):
                out.append(f"{where}.score: is not 0 to 10 in halves")
            if card["mode"] == "screen":
                out.append(f"{where}.score: is scored in a screen pass, which never scores")
            if not d.get("evidence"):
                out.append(f"{where}: is scored with no evidence")
        if d.get("confidence") not in CONFIDENCE:
            out.append(f"{where}.confidence: is not measured, judged or unverified")
    missing = [d for d in DIMENSIONS if d not in seen]
    if missing:
        out.append(f"$.dimensions: missing {', '.join(missing)}")
    band = card.get("totals", {}).get("band")
    if band is not None and band not in BANDS:
        out.append("$.totals.band: is not a band the tool defines")
    for n, c in enumerate(card.get("claims", [])):
        if c.get("status") not in CLAIM_STATUS:
            out.append(f"$.claims[{n}].status: is not a status the tool defines")
    return out
