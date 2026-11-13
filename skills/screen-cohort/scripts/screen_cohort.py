#!/usr/bin/env python3
"""Screen one or many agent projects and build the cohort dashboard in one step.

Exit codes: 0 done, 2 nothing to screen. Findings never change the exit code: a screen reports,
it does not fail.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load():
    try:
        import quiet_counsel as pkg  # noqa: F401
    except ImportError:
        for up in Path(__file__).resolve().parents:
            if (up / "src" / "quiet_counsel").is_dir():
                sys.path.insert(0, str(up / "src"))
                break
    try:
        from quiet_counsel import dashboard, scan
    except ImportError:
        print("quiet-counsel is not importable. From a clone of its repository, run: "
              "pip install .", file=sys.stderr)
        raise SystemExit(2)
    return dashboard, scan


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="project directories")
    ap.add_argument("--out", default="cards", help="directory for scorecards and the dashboard")
    ap.add_argument("--corpus", help="directory of known public projects, for duplication checks")
    ap.add_argument("--dashboard", help="dashboard path (default: <out>/cohort.html)")
    ap.add_argument("--title", default="Cohort screen", help="dashboard title")
    ap.add_argument("--no-ignore", action="store_true", help="accepted and does nothing; a .scanignore is never applied here")
    ap.add_argument("--json", action="store_true", help="print a JSON summary")
    a = ap.parse_args(argv)
    dashboard, scan = load()

    dirs = [p for p in a.paths if os.path.isdir(p)]
    for p in a.paths:
        if p not in dirs:
            print(f"skipped, not a directory: {p}", file=sys.stderr)
    if not dirs:
        return 2
    os.makedirs(a.out, exist_ok=True)
    cards, written = [], []
    for n, p in enumerate(dirs, 1):
        card = scan.screen(p, a.corpus, honour_ignore=False)
        dest = os.path.join(a.out, scan.card_file_name(card["project"]["name"], n))
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(card, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        cards.append(card)
        written.append(dest)
    page = a.dashboard or os.path.join(a.out, "cohort.html")
    with open(page, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dashboard.build(cards, a.title))

    order = {"blocked": 0, "review": 1, "shortlist": 2, "screened": 3}
    cards.sort(key=lambda c: (order[c["totals"]["band"]], c["project"]["name"]))
    if a.json:
        print(json.dumps({
            "dashboard": page, "cards": written,
            "projects": [{"name": c["project"]["name"], "band": c["totals"]["band"],
                          "archetype": c["project"]["archetype"],
                          "flags": [f"{f['severity']}:{f['id']}" for f in c["flags"]]}
                         for c in cards]}, indent=2))
    else:
        for c in cards:
            flags = ", ".join(f"{f['severity']}:{f['id']}" for f in c["flags"]) or "no flags"
            print(f"{c['totals']['band']:<10} {c['project']['name']:<32} {c['project']['archetype']:<13} {flags}")
        print(f"dashboard: {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
