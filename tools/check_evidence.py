#!/usr/bin/env python3
"""Measure whether the numbers in a screen link to a file and line.

Screens a tree, then reports for every flag and every numeric signal whether it cites a file and
line that exist, and whether the cited line contains the excerpt the card claims it holds. It
changes nothing and judges nothing: it counts, so a claim about the card can be set against the
count. Standard library only.

    python3 tools/check_evidence.py PATH [--list]

Exit 0 when every cited file and line exists, 1 when a citation points at nothing, 2 on bad input.
The comparison: the excerpt, whitespace collapsed, must appear in the cited line. Only the
decorations the tool itself adds for that flag are set aside (a shape or licence label, a code point
list, a gate note). "<line withheld>" matches only a line the scanner withholds, and quoted text
never matches one. A notice such as "<text withheld: text addressed to the evaluator>" matches only a
line that `scan.withhold_text` withholds for that same reason. An excerpt with nothing left to compare
does not match. Every line the tool prints passes `scan.withhold_text`.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from quiet_counsel import scan  # noqa: E402

NOTICE_RE = re.compile(r"^<text withheld: (credential|text addressed to the evaluator)>$")
REF_RE = re.compile(r"^(?P<path>[^\s:][^:\n]*):(?P<line>\d+)$")
CITE_RE = re.compile(r"([\w./-]+\.\w+):(\d+)\b")


def inside(root, rel):
    """The real path of rel under root, or None for an absolute reference or one that leaves root."""
    if os.path.isabs(rel) or rel.startswith(("/", "\\")) or os.path.splitdrive(rel)[0]:
        return None
    base, full = os.path.realpath(root), os.path.realpath(os.path.join(root, rel))
    try:
        return full if os.path.commonpath([base, full]) == base else None
    except ValueError:  # another drive
        return None


def _norm(text):
    return " ".join(text.split())


# What the card adds around a line it quotes, by the flag that made the evidence. Only these
# decorations are set aside, and only for the flags that generate them; a bracketed word in any
# other excerpt is text the repository wrote and has to be on the line.
SECRET_LABELS = {label for label, _ in scan.SECRET_PATTERNS}
COPYLEFT_LABELS = {label for label, _ in scan.COPYLEFT_MARKERS}
DECORATIONS = {
    "secret-in-tree": {"labels": SECRET_LABELS},
    "credential-shaped-fixtures": {"labels": SECRET_LABELS},
    "copyleft-in-permissive-tree": {"labels": COPYLEFT_LABELS},
    "hidden-characters": {"codepoints": True},
    "writes-host-config": {"suffix": "  [no gate in file]"},
}
CODEPOINT_PREFIX_RE = re.compile(r"^U\+[0-9A-F]{4}(?: U\+[0-9A-F]{4})* in: ")


def _contains(line, excerpt, flag_id=None):
    rules = DECORATIONS.get(flag_id, {})
    ex = excerpt.rstrip("\u2026")
    m = re.match(r"\[([^\]]+)\] ", ex)
    if m and m.group(1) in rules.get("labels", ()):
        ex = ex[m.end():]
    if rules.get("codepoints"):
        ex = CODEPOINT_PREFIX_RE.sub("", ex, count=1)
    if rules.get("suffix") and ex.endswith(rules["suffix"]):
        ex = ex[:-len(rules["suffix"])]
    ex = _norm(ex)
    if not ex:
        return False  # nothing left to compare is not a match
    if ex == scan.WITHHELD:
        return scan.holds_secret(line)
    return not scan.holds_secret(line) and ex in _norm(line)


def check_ref(root, path, line, excerpt=None, flag_id=None):
    """'broken' when the file or line does not exist, 'match' or 'differs' otherwise. With no
    excerpt to compare, an existing line is 'match'."""
    full = inside(root, path)
    if not full or not scan.is_regular(full):
        return "broken"
    lines = scan.read_text(full, 5_000_000).splitlines()
    if not 1 <= int(line) <= len(lines):
        return "broken"
    if excerpt is None:
        return "match"
    text = lines[int(line) - 1]
    if NOTICE_RE.match(_norm(excerpt)):
        # a notice matches only a line the output filter withholds, and only for the reason it gives:
        # a credential notice does not vouch for a line aimed at the evaluator, nor the reverse
        return "withheld" if scan.withhold_text(text) == _norm(excerpt) else "differs"
    if not _contains(text, excerpt, flag_id):
        return "differs"
    return "withheld" if scan.holds_secret(text) else "match"


def _has_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(re.fullmatch(r"\d+/\d+", value))
    if isinstance(value, dict):
        return any(_has_number(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_number(v) for v in value)
    return False


def measure(root):
    card = scan.screen(root)
    out = {"flags": {"file and line, excerpt on the line": [], "file and line, excerpt differs": [],
                     "command, commit, note or path only": [], "no evidence": []},
           "items": {"match": 0, "withheld": 0, "differs": 0, "broken": 0, "no line": 0},
           "signals": {"file and line": [], "command only": [], "neither": []},
           "claims": {"file and line": [], "command only": [], "neither": []},
           "truncated": [], "broken": []}
    for f in card["flags"]:
        located = []
        for e in f.get("evidence", []):
            m = REF_RE.match(e.get("ref", "")) if e.get("kind") == "file" else None
            if not m:
                out["items"]["no line"] += 1
                continue
            r = check_ref(root, m["path"], m["line"], e.get("excerpt"), f["id"])
            out["items"][r] += 1
            located.append(r)
            if r == "broken":
                out["broken"].append(f"{f['id']}: {e['ref']}")
        if not f.get("evidence"):
            cls = "no evidence"
        elif "match" in located or "withheld" in located or "differs" in located:
            cls = ("file and line, excerpt on the line" if "differs" not in located
                   else "file and line, excerpt differs")
        else:
            cls = "command, commit, note or path only"
        out["flags"][cls].append(f["id"])
        n = re.search(r"\d+", f.get("title", ""))
        listed = len(f.get("evidence", []))
        if n and listed in (3, 5) and int(n.group()) > listed:  # lists are cut at 3 or 5
            out["truncated"].append(f["id"])
    for name, s in card["signals"].items():
        if not _has_number(s.get("value")):
            continue
        text = f"{s.get('command', '')} {s.get('note', '') or ''}"
        cites = [c for c in CITE_RE.findall(text) if check_ref(root, c[0], c[1]) == "match"]
        cls = "file and line" if cites else "command only" if s.get("command") else "neither"
        out["signals"][cls].append(name)
    for c in card.get("claims", []):
        text = f"{c.get('location', '')} " + " ".join(e.get("ref", "") for e in c.get("evidence", []))
        cites = [x for x in CITE_RE.findall(text) if check_ref(root, x[0], x[1]) == "match"]
        cls = "file and line" if cites else "command only" if c.get("evidence") else "neither"
        out["claims"][cls].append(c["claim"])
    out["signal_count"] = len(card["signals"])
    return out


def report(root, names=False):
    m = measure(root)
    lines = [f"screened {root}"]
    n = sum(len(v) for v in m["flags"].values())
    lines.append(f"flags: {n}")
    for k, v in m["flags"].items():
        lines.append(f"  {k}: {len(v)}" + (f"  ({', '.join(v)})" if names and v else ""))
    lines.append("evidence items on flags: " + ", ".join(f"{k} {v}" for k, v in m["items"].items()))
    lines.append(f"flags whose title counts more than the evidence listed (heuristic): "
                 f"{len(m['truncated'])}" + (f"  ({', '.join(m['truncated'])})" if names and m["truncated"] else ""))
    s = sum(len(v) for v in m["signals"].values())
    lines.append(f"numeric signals: {s} of {m['signal_count']} signals")
    for k, v in m["signals"].items():
        lines.append(f"  {k}: {len(v)}" + (f"  ({', '.join(v)})" if names and v else ""))
    c = sum(len(v) for v in m["claims"].values())
    lines.append(f"claims: {c}")
    for k, v in m["claims"].items():
        lines.append(f"  {k}: {len(v)}")
    for b in m["broken"]:
        lines.append(f"BROKEN {b}")
    return "\n".join(lines), m


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or not os.path.isdir(args[0]) or "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0 if "--help" in argv or "-h" in argv else 2
    text, m = report(args[0], "--list" in argv)
    # The report names the project path and quotes citations from the project, so each line passes the
    # one output filter before it is printed.
    print(chr(10).join(scan.withhold_text(line, "line") for line in text.split(chr(10))))
    return 1 if m["broken"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
