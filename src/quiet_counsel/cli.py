"""Command line: classify, screen, integrity, dashboard, check, verdict, sample."""

import argparse
import json
import os
import sys

from . import __version__, dashboard, sample, scan, schema, verdict

PROG = "quiet-counsel"


def _load(paths):
    cards = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            cards.append(json.load(fh))
    return cards


def build_parser():
    ap = argparse.ArgumentParser(
        prog=PROG,
        description="Score an agent project on what its repository contains, with evidence "
                    "for every number. Measures and flags; a person decides.")
    ap.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classify", help="what kind of project this is, and on what evidence")
    c.add_argument("path", help="the project directory")
    c.add_argument("--json", action="store_true", help="print the result as JSON")

    s = sub.add_parser("screen", help="a mechanical pass over one or many projects")
    s.add_argument("paths", nargs="+", help="one or more project directories")
    s.add_argument("--corpus", help="a directory of known projects, for duplication checks")
    s.add_argument("--out", help="write one scorecard per project into this directory")
    s.add_argument("--event-start", help="the date the event opened, to flag earlier history")
    s.add_argument("--event-end", help="the date the event closed")
    ig = s.add_mutually_exclusive_group()
    ig.add_argument("--honour-ignore", action="store_true",
                    help="apply the project's .scanignore to one project: findings in the paths it lists "
                         "become information, so a project can lower its own band under this option")
    ig.add_argument("--no-ignore", action="store_true",
                    help="accepted and does nothing: a .scanignore is not applied unless --honour-ignore is passed")

    i = sub.add_parser("integrity", help="provenance, duplication, licence and claim checks")
    i.add_argument("path", help="the project directory")
    i.add_argument("--corpus", help="a directory of known projects, for duplication checks")
    i.add_argument("--min-bytes", type=int, default=400,
                   help="ignore files smaller than this when comparing (default 400)")

    d = sub.add_parser("dashboard", help="render scorecards as one HTML page")
    d.add_argument("cards", nargs="+", help="scorecard JSON files")
    d.add_argument("--out", default="cohort.html", help="where to write the page")
    d.add_argument("--title", default="Quiet Counsel review", help="the page title")
    d.add_argument("--strict", action="store_true",
                   help="refuse to build if any scored dimension carries no evidence")

    k = sub.add_parser("check", help="check scorecards against the contract the dashboard needs")
    k.add_argument("cards", nargs="+", help="scorecard JSON files")

    v = sub.add_parser("verdict", help="write a release verdict from one scorecard")
    v.add_argument("scorecard", help="the scorecard JSON file")
    v.add_argument("--gate-status", choices=("passed", "failed", "missing"), default="missing",
                   help="result of the project's own release gate (default: missing)")
    v.add_argument("--out", required=True, help="where to write the verdict JSON")

    m = sub.add_parser("sample", help="write the synthetic sample project with planted problems")
    m.add_argument("dest", help="the directory to create")
    m.add_argument("--git", action="store_true", help="also make it a git repository")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)

    if a.cmd == "classify":
        if not os.path.isdir(a.path):
            print(f"not a directory: {a.path}", file=sys.stderr)
            return 2
        arch, scores, evidence, found = scan.classify(os.path.abspath(a.path))
        # The evidence names files and quotes lines of the project, so every string passes the same
        # withholding as the rest of the output: credential text and text aimed at the evaluator
        # are replaced by a notice. The archetype and scores are the tool's own.
        evidence = scan.withhold_all(evidence)
        if a.json:
            print(json.dumps({"archetype": arch, "scores": scores, "evidence": evidence},
                             indent=2))
        else:
            print(f"archetype: {arch}")
            print("scores:    " + ", ".join(
                f"{k}={v:g}" for k, v in sorted(scores.items(), key=lambda kv: -kv[1])))
            for e in evidence:
                print(f"  evidence: {e['ref']}" + (f" ({e['excerpt']})" if e.get("excerpt") else ""))
        return 0

    if a.cmd == "screen":
        dirs = [p for p in a.paths if os.path.isdir(p)]
        skipped = [p for p in a.paths if not os.path.isdir(p)]
        for p in skipped:
            print(f"skipped, not a directory: {p}", file=sys.stderr)
        if not dirs:
            return 2
        if a.honour_ignore and len(a.paths) != 1:
            print("--honour-ignore applies to one project at a time", file=sys.stderr)
            return 2
        event = (a.event_start, a.event_end) if a.event_start else None
        cards = [scan.screen(p, a.corpus, event, honour_ignore=a.honour_ignore) for p in dirs]
        if not a.out:
            print(json.dumps(cards if len(cards) > 1 else cards[0], indent=2, default=str))
            return 0
        os.makedirs(a.out, exist_ok=True)
        for card in cards:
            dest = os.path.join(a.out, f"{card['project']['name']}.json")
            with open(dest, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(card, fh, indent=2, default=str, ensure_ascii=False)
                fh.write("\n")
        print(f"{len(cards)} scorecard(s) written to {a.out}")
        order = {"blocked": 0, "review": 1, "shortlist": 2, "screened": 3}
        for card in sorted(cards, key=lambda c: order[c["totals"]["band"]]):
            flags = ", ".join(f"{f['severity']}:{f['id']}" for f in card["flags"]) or "no flags"
            print(f"  {card['totals']['band']:<10} {card['project']['name']:<34} "
                  f"{card['project']['archetype']:<13} {flags}")
        return 0

    if a.cmd == "integrity":
        if not os.path.isdir(a.path):
            print(f"not a directory: {a.path}", file=sys.stderr)
            return 2
        root = os.path.abspath(a.path)
        quoted = []
        directed = scan.evaluator_directed_hits(root, judged_quoted=quoted)
        out = {"history": scan.history_facts(root), "licence": scan.licence_facts(root),
               "third_party": scan.provenance_facts(root),
               "claims": scan.extract_claims(root),
               "hidden_characters": [{"file": h[0], "line": h[1], "codepoints": h[2]}
                                     for h in scan.hidden_char_hits(root)],
               "evaluator_directed": [{"file": h[1], "line": h[2], "text": scan.clip(h[3])}
                                      for h in directed],
               "evaluator_text_judged_quoted": [{"file": h[1], "line": h[2], "text": scan.clip(h[3])}
                                                for h in quoted]}
        if a.corpus:
            dups, checked, indexed = scan.corpus_duplicates(root, a.corpus, a.min_bytes)
            out["duplication"] = {"matches": dups, "files_compared": checked,
                                  "corpus_files_indexed": indexed}
        print(json.dumps(out, indent=2, default=str))
        return 0

    if a.cmd == "dashboard":
        cards = _load(a.cards)
        try:
            page = dashboard.build(cards, a.title, strict=a.strict)
        except dashboard.Unevidenced as exc:
            print(f"refusing to build: scored with no evidence: {exc}", file=sys.stderr)
            return 1
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(page)
        print(f"{a.out}: {len(cards)} project(s), {os.path.getsize(a.out):,} bytes")
        return 0

    if a.cmd == "check":
        bad = 0
        for path, card in zip(a.cards, _load(a.cards)):
            found = schema.problems(card)
            if found:
                bad += 1
                print(f"{path}: {len(found)} problem(s)")
                for p in found:
                    print(f"  {p}")
            else:
                print(f"{path}: ok")
        return 1 if bad else 0

    if a.cmd == "verdict":
        with open(a.scorecard, "rb") as fh:
            raw = fh.read()
        result = verdict.make(json.loads(raw), raw, a.gate_status)
        with open(a.out, "wb") as fh:
            fh.write(verdict.render(result))
        return 0

    if a.cmd == "sample":
        sample.write(a.dest, with_git=a.git)
        print(f"sample project written to {a.dest}")
        return 0
    return 2
