#!/usr/bin/env python3
"""Print the lines behind every flag in a scorecard, so each one can be judged in context.

Exit codes: 0 done, 2 the card or the project could not be read. Nothing here decides; it shows.
"""

import argparse
import json
import os
import sys


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
    a = ap.parse_args(argv)

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
            if e.get("kind") == "file":
                rel, line = locate(e["ref"])
                if line:
                    item["context"], item["error"] = context(root, rel, line, a.context)
            items.append(item)

    if a.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print("no flags to triage")
    for it in items:
        print(f"[{it['severity']}] {it['flag']}: {it['title']}")
        print(f"  at {it['ref']}")
        for row in it.get("context") or []:
            mark = ">" if row["hit"] else " "
            print(f"  {mark} {row['line']:>5} | {row['text']}")
        if it.get("error"):
            print(f"  (could not read: {it['error']})")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
