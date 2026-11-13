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
# A block that carries a secret as lines of ordinary-looking text (a PEM-style key body is
# base64, which no credential-shape rule matches line by line).
BLOCK_BEGIN = re.compile(r"-{5}BEGIN [A-Z0-9 ]+-{5}")
BLOCK_END = re.compile(r"-{5}END [A-Z0-9 ]+-{5}")
BLOCK_NOTICE = "<line withheld: credential>"


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


_ASSIGNED = {}


def credential_assignment(scan, text):
    """True when `text` holds a credential word followed by an assignment and a value (`password=x`,
    `"api_key": "x"`, `token: x`), or a URL with a user and password. A credential word alone
    (`token_utils.py`) does not count, so a path or a title can still say which file a flag is
    about."""
    rx = _ASSIGNED.get("rx")
    if rx is None:
        words = scan.SECRET_WORD_RE.pattern.replace("(?i)", "", 1)  # the scan's own word list
        url = r"://[^/\s:@]+:[^/\s@]+@"
        rx = _ASSIGNED["rx"] = re.compile(r"(?:" + words + r")\w*[\"'\]]*\s*[=:]\s*[\"']?[^\s\"']|" + url, re.I)
    return bool(rx.search(text))


def withhold(scan, text, show_directed, what="line", strict=False):
    """The text to print for anything that came from the scanned project (a source line, a path,
    a title, an error string): the text itself, or a notice that it was withheld. `what` names
    the kind of text in the notice. Every such field is withheld when it holds a credential shape
    or a credential word with an assignment and a value, and (unless `show_directed`) text
    addressed to the evaluator. `strict` is for a source line quoted from a file, which is also
    withheld for a credential word alone. The tool's own flag id and severity are not passed
    through here: the project does not produce them."""
    if not isinstance(text, str):
        return text
    if strict:
        secret = scan.holds_secret(text)
    else:
        secret = any(rx.search(text) for _, rx in scan.SHAPE_RES) or credential_assignment(scan, text)
    if secret:
        return f"<{what} withheld: credential>"
    if not show_directed and any(re.search(p, text) for p in scan.EVALUATOR_DIRECTED):
        return f"<{what} withheld: text addressed to the evaluator>"
    return text


def withhold_reference(scan, ref, show_directed):
    """A reference (path and line) for printing: the path withheld as `<path withheld>` with the
    line number kept when the path holds a credential or evaluator-directed text."""
    if not isinstance(ref, str):
        return ref
    head, line = locate(ref)
    if withhold(scan, head, show_directed, "path") != head:
        return "<path withheld>" + (f":{line}" if line else "")
    return ref


def block_lines(lines):
    """The 1-based numbers of every line inside a BEGIN to END block, both marker lines included.
    The whole file is scanned, so a block whose opening marker lies outside the lines a caller
    shows is still found. A block that never closes runs to the end of the file."""
    inside, out = False, set()
    for i, text in enumerate(lines, 1):
        opened = None if inside else BLOCK_BEGIN.search(text)
        if opened:
            inside = True
            out.add(i)
            inside = not BLOCK_END.search(text, opened.end())  # opened and closed on one line
        elif inside:
            out.add(i)
            inside = not BLOCK_END.search(text)
    return out


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


def read_lines(root, rel):
    """(lines, error) for a file named by a reference."""
    path = inside(root, rel)
    if not path:
        return None, "broken citation: the reference leaves the project"
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines(), None
    except OSError as exc:
        return None, str(exc)


def context(lines, line, n, blocked):
    """The rows around `line`. A line inside a sensitive block is replaced by a notice here, so
    no caller can print it by forgetting to check."""
    lo, hi = max(1, line - n), min(len(lines), line + n)
    return [{"line": i, "text": BLOCK_NOTICE if i in blocked else lines[i - 1], "hit": i == line}
            for i in range(lo, hi + 1)]


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
    # Source lines hold any character. A console or pipe on a non-UTF-8 locale (Windows by
    # default) would stop the run with UnicodeEncodeError, so the streams are set to UTF-8 here.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    scan = load()

    try:
        with open(a.card, encoding="utf-8") as fh:
            card = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"cannot read the scorecard: {exc}", file=sys.stderr)
        return 2
    root = a.project or card["project"]["path"]
    if not os.path.isdir(root):
        # the path may come from the card, so it passes the same test as any project text
        shown = withhold(scan, root, a.show_directed_text, "path")
        print(f"project not found at {shown}; pass --project", file=sys.stderr)
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
            else:
                if e.get("kind") == "file":
                    rel, line = locate(e["ref"])
                    if line:
                        item["context"] = None
                        lines, item["error"] = read_lines(root, rel)
                        if lines is not None:
                            blocked = block_lines(lines)
                            if line in blocked:
                                item["excerpt"] = BLOCK_NOTICE if item["excerpt"] else item["excerpt"]
                            item["context"] = context(lines, line, a.context, blocked)
                            for row in item["context"]:
                                row["text"] = withhold(scan, row["text"], a.show_directed_text, strict=True)
            # Every string the project produced (a path, a title, an excerpt, an error text)
            # passes the credential and evaluator-text test, so a file name cannot carry either
            # kind of text past it. The flag id and severity come from the tool and are exempt.
            # A withheld path prints as a notice with its line number.
            for key, what in (("title", "title"), ("excerpt", "excerpt"), ("error", "error")):
                if key in item:
                    item[key] = withhold(scan, item[key], a.show_directed_text, what)
            item["ref"] = withhold_reference(scan, item["ref"], a.show_directed_text)
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
