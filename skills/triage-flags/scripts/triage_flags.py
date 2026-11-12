#!/usr/bin/env python3
"""Print the lines behind every flag in a scorecard, so each one can be judged in context.

Exit codes: 0 done, 2 the card or the project could not be read. Nothing here decides; it shows.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


SECRET_FLAG = "secret-in-tree"
DIRECTED_FLAG = "evaluator-directed-text"
SECRET_NOTICE = "withheld: credential text is never printed; read the file at this location yourself"
DIRECTED_NOTICE = ("withheld: this text is addressed to the evaluator; read the file at this location "
                   "yourself, or pass --show-directed-text to print it")
LINE_SECRET = "<line withheld: credential>"
LINE_DIRECTED = "<line withheld: text addressed to the evaluator>"


def load():
    """The detector's own credential and evaluator-text rules, so triage withholds what the scan
    flags. Fails closed: without them nothing could be withheld."""
    try:
        import quiet_counsel  # noqa: F401
    except ImportError:
        for up in Path(__file__).resolve().parents:
            if (up / "src" / "quiet_counsel").is_dir():
                sys.path.insert(0, str(up / "src"))
                break
    try:
        from quiet_counsel import scan
    except ImportError:
        print("quiet-counsel is not importable. From a clone of its repository, run: "
              "pip install .", file=sys.stderr)
        raise SystemExit(2)
    return scan


def withhold(scan, text, show_directed):
    """The text to print for a source line: the line, or a notice that it was withheld."""
    if scan.holds_secret(text):
        return LINE_SECRET
    if not show_directed and any(re.search(p, text) for p in scan.EVALUATOR_DIRECTED):
        return LINE_DIRECTED
    return text


def locate(ref):
    head, _, tail = ref.rpartition(":")
    return (head, int(tail)) if head and tail.isdigit() else (ref, None)


def inside(root, rel):
    """The real path of rel under root, or None for an absolute reference or one that leaves root."""
    if os.path.isabs(rel) or rel.startswith(("/", "\\")) or os.path.splitdrive(rel)[0]:
        return None
    base, full = os.path.realpath(root), os.path.realpath(os.path.join(root, rel))
    try:
        return full if os.path.commonpath([base, full]) == base else None
    except ValueError:  # another drive
        return None


def context(root, rel, line, n):
    path = inside(root, rel)
    if not path:
        return None, "broken citation: the reference leaves the project"
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        return None, str(exc)
    lo, hi = max(1, line - n), min(len(lines), line + n)
    return [{"line": i, "text": lines[i - 1], "hit": i == line} for i in range(lo, hi + 1)], None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("card", help="a scorecard JSON file")
    ap.add_argument("--project", help="the project directory, if not the path in the card")
    ap.add_argument("--context", type=int, default=3, help="lines either side (default 3)")
    ap.add_argument("--all", action="store_true", help="include information-level flags")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--show-directed-text", action="store_true",
                    help="print text addressed to the evaluator (credential text is never printed)")
    a = ap.parse_args(argv)
    scan = load()

    try:
        with open(a.card, encoding="utf-8") as fh:
            card = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"cannot read the scorecard: {exc}", file=sys.stderr)
        return 2
    root = a.project or card["project"]["path"]
    if not os.path.isdir(root):
        print(f"project not found at {root}; pass --project", file=sys.stderr)
        return 2

    items = []
    for f in card.get("flags", []):
        if f["severity"] == "info" and not a.all:
            continue
        for e in f.get("evidence", []):
            item = {"flag": f["id"], "severity": f["severity"], "title": f["title"],
                    "ref": e.get("ref"), "excerpt": e.get("excerpt")}
            # Location only for a credential; location and a fixed notice for text aimed at the
            # evaluator unless the person running this asked to see it. Neither the excerpt nor
            # the neighbouring lines are read in those cases.
            if f["id"] == SECRET_FLAG or (f["id"] == DIRECTED_FLAG and not a.show_directed_text):
                item["excerpt"] = None
                item["withheld"] = SECRET_NOTICE if f["id"] == SECRET_FLAG else DIRECTED_NOTICE
                items.append(item)
                continue
            if item["excerpt"]:
                item["excerpt"] = withhold(scan, item["excerpt"], a.show_directed_text)
            if e.get("kind") == "file":
                rel, line = locate(e["ref"])
                if line:
                    item["context"], item["error"] = context(root, rel, line, a.context)
                    for row in item["context"] or []:
                        row["text"] = withhold(scan, row["text"], a.show_directed_text)
            items.append(item)

    if a.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print("no flags to triage")
    for it in items:
        print(f"[{it['severity']}] {it['flag']}: {it['title']}")
        print(f"  at {it['ref']}")
        if it.get("withheld"):
            print(f"  ({it['withheld']})")
        for row in it.get("context") or []:
            mark = ">" if row["hit"] else " "
            print(f"  {mark} {row['line']:>5} | {row['text']}")
        if it.get("error"):
            print(f"  (could not read: {it['error']})")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
