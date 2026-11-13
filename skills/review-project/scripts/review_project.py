#!/usr/bin/env python3
"""Deep review of one agent project: prepare a worksheet, finalize a verdict, verify citations.

  prepare  <project> --out worksheet.json   screen it and lay out every dimension to score
  finalize <worksheet> --out verdict.html   refuse or render: caps applied, means computed;
                                            refuses if the project changed since prepare
  verify   <worksheet> [--project DIR]      check every file:line citation still matches

Exit codes: 0 done, 1 refused (with the reasons printed), 2 bad input.
"""

import argparse
import hashlib
import json
import os
import re
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
        from quiet_counsel import dashboard, scan, schema
    except ImportError:
        print("quiet-counsel is not importable. From a clone of its repository, run: "
              "pip install .", file=sys.stderr)
        raise SystemExit(2)
    return dashboard, scan, schema


ANCHOR = {
    "A1": "every definition passes its format's validator; descriptions say what and when",
    "A2": "always-loaded cost measured, budgeted and enforced; detail loads on demand",
    "A3": "each component declares its tools; reviewers cannot write; a host can enforce it",
    "A4": "dependencies and external references pinned; a run repeats at a stated revision",
    "B1": "behaviour and selection evals run automatically, results committed, a control",
    "B2": "every number the project states about itself reproduces from the repository",
    "B3": "run records and receipts written as things happen; history not rewritten",
    "C1": "no credential in the tree or history; secrets from the environment or a store",
    "C2": "outside text treated as data, enforced, and instruction text scanned for hidden text",
    "C3": "actions pinned by digest, lockfiles, no download piped into a shell",
    "C4": "delete, deploy and spend gated by a dry run, a confirmation or a host permission",
    "D1": "own licence declared; every redistributed component compliant and attributed",
    "D2": "the work is the authors'; borrowed material credited at file level",
    "E1": "a useful span of work, reusable beyond one team",
    "E2": "runs anywhere its format is supported; no absolute paths or host-only keys",
    "E3": "computed indexes, help and stable diagnostics; a newcomer can start unaided",
}
LOOK_AT = {
    "A1": ["skill_definitions", "non_spec_frontmatter_keys", "descriptions_without_when"],
    "A2": ["always_loaded_description_tokens_est", "always_loaded_rulebook_bytes",
           "rulebook_missing_paths", "flag:stale-instructions"],
    "A3": ["definitions_declaring_tools", "agent_definitions"],
    "A4": ["lockfiles", "ci_actions_pinned_by_digest"],
    "B1": ["test_files", "eval_dirs", "ci_workflow_files", "jenkinsfile"],
    "B2": ["claims"],
    "B3": ["history"],
    "C1": ["secret_pattern_hits", "flag:secret-in-tree"],
    "C2": ["untrusted_content_guidance_hits", "hidden_character_hits", "flag:evaluator-directed-text"],
    "C3": ["supply_chain_hits", "ci_actions_pinned_by_digest", "lockfiles"],
    "C4": ["host_config_writes", "flag:writes-host-config", "flag:open-time-hook",
           "flag:agent-hook", "flag:install-time-script", "flag:workflow-data-out",
           "flag:untrusted-code-with-power",
           "read the scripts that delete, deploy or spend"],
    "D1": ["licence_declared", "nested_licence_files", "third_party_declarations",
           "flag:copyleft-in-permissive-tree", "flag:no-licence", "flag:share-alike-text",
           "flag:restricted-licence-text", "flag:licence-needs-reading"],
    "D2": ["corpus_duplicate_files", "copies_credited", "history", "flag:corpus-duplication",
           "flag:copied-without-attribution"],
    "E1": ["skill_definitions", "agent_definitions", "command_definitions"],
    "E2": ["absolute_path_hits"],
    "E3": ["readme_bytes"],
}
GROUP_OF = {"A": "methodology", "B": "evidence", "C": "safety", "D": "integrity", "E": "product"}


# Directories a reviewer's own tooling writes while reading a project: bytecode and test
# caches. Everything else, hidden folders and CI configuration included, is part of the tree.
TOOL_CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis"}


def contained(root, path):
    """True when the real path of `path` is the real root or inside it. The same test as
    `quiet_counsel.scan.contained`, kept here so the fingerprint never depends on an import that
    could fail: a directory or file that resolves outside the project is not part of it."""
    base, real = os.path.realpath(root), os.path.realpath(path)
    try:
        return os.path.commonpath([base, real]) == base
    except ValueError:  # another drive
        return False


def is_dir_link(path):
    """True for a directory that is a symbolic link or a Windows junction. `os.path.isjunction`
    exists from Python 3.12; before that, a directory whose real path is not its own name inside its
    parent's real path is taken as a link."""
    if os.path.islink(path):
        return True
    junction = getattr(os.path, "isjunction", None)
    if junction is not None and junction(path):
        return True
    parent, name = os.path.split(os.path.abspath(path))
    return os.path.normcase(os.path.realpath(path)) != os.path.normcase(
        os.path.join(os.path.realpath(parent), name))


def fingerprint(root, skip=()):
    """Every file's path and content hash, so finalize can tell whether the project changed
    during the review. Symbolic links are recorded by target and never followed; pipes and
    devices are recorded by kind and never read. A directory that resolves outside the root is
    recorded as such and not entered. A directory link or junction that stays inside the root is
    recorded as `dirlink:` with the root-relative path it resolves to, so pointing `alias` at `b`
    instead of `a` changes the fingerprint even when both hold the same files. A file is hashed
    only when it resolves inside the root. `skip` names the review's own files."""
    skip = {os.path.abspath(p) for p in skip if p}
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git" and d not in TOOL_CACHES)
        for d in list(dirnames):
            path = os.path.join(dirpath, d)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if not contained(root, path):
                dirnames.remove(d)
                files[rel] = "outside"
            elif is_dir_link(path):
                target = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
                files[rel] = "dirlink:" + target.replace(os.sep, "/")
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.abspath(path) in skip:
                continue
            if os.path.islink(path):
                files[rel] = "link:" + os.readlink(path)
                continue
            if not os.path.isfile(path):
                files[rel] = "special"
                continue
            if not contained(root, path):
                files[rel] = "outside"
                continue
            h = hashlib.sha256()
            try:
                fh = load()[1].open_regular(path, root)
                if fh is None:
                    files[rel] = "special"  # swapped for a pipe or device after the check above
                    continue
                with fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                files[rel] = h.hexdigest()
            except OSError:
                files[rel] = "unreadable"
    return files


def raw_bytes(text):
    """The bytes of a name or a value exactly as the file system gave it. A lone surrogate (a name
    that is not valid text) is kept, so two different names never hash alike."""
    return text.encode("utf-8", "surrogatepass")


def digest(files):
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(raw_bytes(f"{rel}\0{files[rel]}\n"))
    return h.hexdigest()


def sha(text):
    return hashlib.sha256(raw_bytes(text)).hexdigest()


def label(scan, text):
    """A file name or link target as it is written or printed. Text that holds a credential or is
    addressed to the evaluator becomes a notice followed by a short hash of the real text, so two
    different withheld names stay different entries and a rename of one is still a change. The
    fingerprint itself keeps the real names; only what leaves this script goes through here."""
    out = scan.withhold_text(text, "name")
    if out != text:
        out += "~" + hashlib.sha256(text.encode("utf-8", "backslashreplace")).hexdigest()[:8]
    return out


def shown(scan, files):
    """The fingerprint as it is stored in the worksheet and compared by finalize: every name and
    link target passes `label`. A hash is a content digest and passes unchanged."""
    out = {}
    for rel in sorted(files):
        value = files[rel]
        for prefix in ("link:", "dirlink:"):
            if value.startswith(prefix):
                value = prefix + label(scan, value[len(prefix):])
                break
        out[label(scan, rel)] = value
    return out


def identities(scan, files):
    """The comparison form of a fingerprint: for each file, the full SHA-256 of its raw path mapped
    to the full SHA-256 of its raw value (a content digest, a link target or a kind), with the
    display label beside it. Nothing here is shortened or withheld, so two names that print alike
    are still two entries and a rename is a change. The labels are for printing only."""
    return {sha(rel): [sha(files[rel]), label(scan, rel)] for rel in sorted(files)}


def cmd_prepare(a):
    _, scan, _ = load()
    if not os.path.isdir(a.project):
        print(f"not a directory: {a.project}", file=sys.stderr)
        return 2
    card = scan.screen(a.project, a.corpus, honour_ignore=False)
    card["mode"] = "deep"
    files = fingerprint(a.project, skip=(a.out,))
    card["project"]["tree_sha256"] = digest(files)
    card["project"]["tree_files"] = shown(scan, files)  # display only: finalize never compares it
    card["project"]["tree_ids"] = identities(scan, files)
    card["project"]["tree_root"] = os.path.abspath(a.project)
    for d in card["dimensions"]:
        d["confidence"] = "judged"
        d["rationale"] = ""
        d["evidence"] = []
        if d["applicable"]:
            d["anchor"] = ANCHOR[d["id"]]
            d["look_at"] = LOOK_AT[d["id"]]
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(scan.withhold_all(card), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    todo = [d["id"] for d in card["dimensions"] if d["applicable"]]
    print(f"worksheet written to {a.out}: score {len(todo)} dimensions ({', '.join(todo)})")
    held = [f["id"] for f in card.get("flags", []) if f.get("caps") == "do-not-score" and f["severity"] != "info"]
    if held:
        print(f"note: {', '.join(held)} must be ruled on by a person before this can be finalized")
    return 0


def tree_changes(card, project=None, skip=()):
    """Reasons to refuse if the project is not the tree the worksheet was prepared from. A
    reviewer is meant to read the project and never change it; this is where that is checked.
    The review's own worksheet and verdict are left out on both sides of the comparison."""
    _, scan, _ = load()
    proj = card.get("project", {})
    ids = proj.get("tree_ids")
    if not isinstance(ids, dict) or not all(isinstance(v, list) and len(v) == 2 for v in ids.values()):
        return ["the worksheet has no tree fingerprint; prepare it again with this version"]
    root = project or proj.get("tree_root") or proj["path"]
    if not os.path.isdir(root):
        return [f"cannot find the project at {scan.withhold_text(root, 'path')} to confirm it is "
                "unchanged; pass --project"]
    # The comparison is on the full SHA-256 of each raw path and its raw value. The review's own
    # worksheet and verdict are left out of both sides, by the hash of their raw path.
    skipped = set()
    for p in skip:
        try:
            if p:
                skipped.add(sha(os.path.relpath(os.path.abspath(p), os.path.abspath(root)).replace(os.sep, "/")))
        except ValueError:  # another drive: the file cannot be inside the project
            pass
    old = {k: v[0] for k, v in ids.items() if k not in skipped}
    names = {k: v[1] for k, v in ids.items()}
    new_ids = identities(scan, fingerprint(root, skip=skip))
    new = {k: v[0] for k, v in new_ids.items()}
    names.update({k: v[1] for k, v in new_ids.items()})
    changed = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    if not changed:
        return []
    # names come from the worksheet and from the tree: the tree's already passed `label`, and a
    # worksheet written by an older version or edited by hand passes it here
    shown_names = ", ".join(label(scan, str(names[k])) for k in changed[:5]) + (
        f" and {len(changed) - 5} more" if len(changed) > 5 else "")
    return [f"the project changed after prepare ({len(changed)} file(s): {shown_names}); a review "
            "reads the project and never edits it, so prepare again from a clean tree"]


def _ceiling(cap, dim):
    """The highest score a cap allows on a dimension, or None when it does not touch it.
    Caps read "D1=0" or "D2<=3" for one dimension, and "safety<=3" for every C dimension."""
    m = re.match(r"^(safety|[A-E]\d)(=|<=)(\d+(?:\.\d+)?)$", cap)
    if not m:
        return None
    target, _, value = m.groups()
    if (target == "safety" and dim.startswith("C")) or target == dim:
        return float(value)
    return None


def _caps(card):
    return {f["caps"] for f in card.get("flags", []) if f.get("caps") and f["severity"] != "info"}


NOTICE_RE = re.compile(r"^<[a-z]+ withheld: (credential|text addressed to the evaluator)>$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
# The two limits on a withheld excerpt, defined once for finalize and verify. Verify searches the
# first LINE_LIMIT characters of the cited line for a part of at most FRAGMENT_LIMIT characters
# (edges trimmed) that hashes to the stored digest. Finalize replaces an excerpt by a notice only
# when verify could later check it, so it refuses an excerpt over either limit.
LINE_LIMIT = 5000
FRAGMENT_LIMIT = 400


def excerpt_sha(text):
    """The SHA-256 of an excerpt as `verify` compares it: the text with its edges trimmed."""
    return sha(text.strip())


def keep_digests(scan, card):
    """Beside every excerpt that the output filter will replace by a notice, store `excerpt_sha256`
    of the raw excerpt (an internal field: the renderer never prints it). An excerpt that is already a
    notice keeps the digest it has."""
    for group in (card.get("flags") or [], card.get("dimensions") or []):
        for item in group if isinstance(group, list) else []:
            for e in (item.get("evidence") or []) if isinstance(item, dict) else []:
                text = e.get("excerpt") if isinstance(e, dict) else None
                if isinstance(text, str) and scan.withhold_text(text) != text:
                    e["excerpt_sha256"] = excerpt_sha(text)


def holds_excerpt(line, digest):
    """True when some part of `line` (edges trimmed, at most FRAGMENT_LIMIT characters, in its first
    LINE_LIMIT characters) hashes to `digest`: the raw excerpt is on the line, though neither is shown."""
    line = line[:LINE_LIMIT]
    if sha(line.strip()) == digest:  # the usual case: the whole line was copied
        return True
    starts = [i for i, ch in enumerate(line) if not ch.isspace()]
    ends = [j for j in range(1, len(line) + 1) if not line[j - 1].isspace()]
    for i in starts:
        for j in ends:
            if j <= i:
                continue
            if j - i > FRAGMENT_LIMIT:
                break
            if sha(line[i:j]) == digest:
                return True
    return False


def cited_line(root, ref):
    """(line, None) for a `path:line` citation that resolves inside `root`, else (None, the reason
    it does not), worded to follow the reference in a printed line. Verify and finalize both read
    a cited line through this."""
    head, _, tail = str(ref).rpartition(":")
    if not tail.isdigit():
        return None, "has no line number"
    path = inside(root, head)
    if not path:
        return None, "is a broken citation: it leaves the project"
    try:
        fh = load()[1].open_text(path, root)
        if fh is None:
            return None, ("does not exist" if not os.path.exists(path)
                          else "is not a regular file, so it was not read")
        with fh:
            lines = fh.read().splitlines()
        if not 1 <= int(tail) <= len(lines):
            raise IndexError
        return lines[int(tail) - 1], None
    except (OSError, IndexError):
        return None, "does not exist"


def excerpt_problems(scan, card, root):
    """Reasons to refuse an excerpt that finalize would replace by a notice but verify could not
    check afterwards: one over FRAGMENT_LIMIT characters, or one that sits past LINE_LIMIT characters
    of its cited line. Only a file citation on a dimension is checked by verify, so only those count.
    A wrong citation is not refused here: verify reports it as a mismatch."""
    out = []
    for d in card.get("dimensions") or []:
        for n, e in enumerate((d.get("evidence") or []) if isinstance(d, dict) else [], 1):
            text = e.get("excerpt") if isinstance(e, dict) else None
            if not (isinstance(text, str) and e.get("kind") == "file" and scan.withhold_text(text) != text):
                continue
            raw, where = text.strip(), f"{d.get('id')} evidence {n}"
            if len(raw) > FRAGMENT_LIMIT:
                out.append(f"{where}: the excerpt is {len(raw)} characters, too long to withhold and verify "
                           f"(limit {FRAGMENT_LIMIT}); cite a shorter part of the line")
                continue
            line, _ = cited_line(root, e.get("ref"))
            if line is not None and raw in line and raw not in line[:LINE_LIMIT]:
                out.append(f"{where}: the excerpt sits past character {LINE_LIMIT} of its line, too long "
                           "to withhold and verify; cite a part nearer the start of the line")
    return out


def shown_line(scan, text):
    """A line of command output that quotes the worksheet (a dimension id, a reason): the worksheet is
    read from a file, so the line passes the output filter whatever built it."""
    return scan.withhold_text(text, "line")


def cmd_finalize(a):
    dashboard, scan, schema = load()
    with open(a.worksheet, encoding="utf-8") as fh:
        card = json.load(fh)
    # a problem can quote project text (a claim, a flag id), so each one passes the same withholding
    reasons = [scan.withhold_text(p, "problem") for p in schema.problems(card)]
    reasons += tree_changes(card, a.project, skip=(a.worksheet, a.out))
    root = a.project or card.get("project", {}).get("tree_root") or card.get("project", {}).get("path")
    if root and os.path.isdir(root):
        reasons += excerpt_problems(scan, card, root)
    if card.get("mode") != "deep":
        reasons.append("this is a screen card; run prepare first")
    for d in card["dimensions"]:
        if d.get("applicable") and d.get("score") is None:
            reasons.append(f"{d['id']} is applicable and unscored")
        if d.get("applicable") and d.get("score") is not None and not (d.get("rationale") or "").strip():
            reasons.append(f"{d['id']} has a score and no rationale")
    caps = _caps(card)
    if "do-not-score" in caps:
        reasons.append("a flag requires a person to rule before this project is scored")
    if reasons:
        print("refused:")
        for r in reasons:
            print(f"  {shown_line(scan, r)}")
        return 1

    effective, applied = {}, []
    for d in card["dimensions"]:
        d.pop("capped_to", None)  # derived: a cap ruled away since the last finalize must not survive it
        if not d.get("applicable"):
            continue
        s = float(d["score"])
        for ceiling in (_ceiling(c, d["id"]) for c in caps):
            if ceiling is not None and s > ceiling:
                d["capped_to"] = ceiling
                s = ceiling
        effective[d["id"]] = s
    for c in sorted(caps):
        applied.append(c)
    groups = {}
    for did, s in effective.items():
        groups.setdefault(GROUP_OF[did[0]], []).append(s)
    card["totals"] = {
        **card.get("totals", {}),
        "mean": round(sum(effective.values()) / len(effective), 2) if effective else None,
        "group_means": {g: round(sum(v) / len(v), 2) for g, v in groups.items()},
        "caps_applied": applied,
    }
    # The reviewer copies project text into rationale and evidence. The worksheet and the card the
    # renderer gets both pass the one output filter; the renderer itself filters nothing. An excerpt
    # the filter is about to replace by a notice first gets the SHA-256 of its raw text beside it, so
    # `verify` can still tell a correct citation of a withheld line from a wrong one.
    keep_digests(scan, card)
    card = scan.withhold_all(card)
    with open(a.worksheet, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    page = dashboard.build([card], a.title, strict=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    # the cap strings come from the flags of a worksheet read from a file, so what is printed is the
    # filtered card's, never `applied`
    shown_caps = card["totals"]["caps_applied"]
    print(shown_line(scan, f"verdict written to {a.out}: mean {card['totals']['mean']} over "
                           f"{len(effective)} applicable dimensions"
                           + (f", caps {', '.join(shown_caps)}" if shown_caps else "")))
    return 0


def inside(root, rel):
    """The real path of rel under root, or None for an absolute reference or one that leaves root."""
    if os.path.isabs(rel) or rel.startswith(("/", "\\")) or os.path.splitdrive(rel)[0]:
        return None
    base, full = os.path.realpath(root), os.path.realpath(os.path.join(root, rel))
    try:
        return full if os.path.commonpath([base, full]) == base else None
    except ValueError:  # another drive
        return None


def cmd_verify(a):
    _, scan, _ = load()
    with open(a.worksheet, encoding="utf-8") as fh:
        card = json.load(fh)
    root = a.project or card["project"]["path"]
    bad, unverifiable, ok, by_digest = [], [], 0, []

    def ref_of(e):
        """A reference as printed: a path that holds a credential or aimed text becomes a notice."""
        return scan.withhold_text(str(e.get("ref")), "reference")

    for d in card["dimensions"]:
        for e in d.get("evidence") or []:
            if e.get("kind") != "file":
                unverifiable.append(f"{d['id']}: {scan.withhold_text(str(e.get('kind')), 'kind')} "
                                    f"{ref_of(e)} (re-run it to check)")
                continue
            line, problem = cited_line(root, e["ref"])
            if problem:
                bad.append(f"{d['id']}: {ref_of(e)} {problem}")
                continue
            want = (e.get("excerpt") or "").strip()
            digest = e.get("excerpt_sha256")
            if not want:
                ok += 1
            elif NOTICE_RE.match(want):
                # A notice is recognised before any text match: a cited line can hold the literal notice
                # (a hostile project can supply one), so only the digest of the raw excerpt vouches for it.
                # A digest of the notice text itself is no digest of an excerpt: finalize never writes one.
                if not (isinstance(digest, str) and DIGEST_RE.match(digest)) or digest == excerpt_sha(want):
                    bad.append(f"{d['id']}: {ref_of(e)} cites a withheld excerpt with no digest of its own, "
                               "so it cannot be checked; copy the line again and finalize")
                elif holds_excerpt(line, digest):
                    ok += 1
                    by_digest.append(f"{d['id']}: {ref_of(e)}")
                else:
                    bad.append(f"{d['id']}: {ref_of(e)} no longer reads the withheld excerpt it cited")
            elif want in line:
                ok += 1
            else:
                # the excerpt is project text the reviewer copied: printed only if it passes the test
                bad.append(f"{d['id']}: {ref_of(e)} no longer reads "
                           f"{scan.withhold_text(want, 'excerpt')!r}")
    print(f"{ok} citation(s) match")
    for w in by_digest:
        print(f"  withheld, verified by digest: {shown_line(scan, w)}")
    for u in unverifiable:
        print(f"  not checked: {shown_line(scan, u)}")
    for b in bad:
        print(f"  MISMATCH: {shown_line(scan, b)}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="screen a project and lay out a deep-review worksheet")
    p.add_argument("project")
    p.add_argument("--out", default="worksheet.json")
    p.add_argument("--corpus")
    p.add_argument("--no-ignore", action="store_true")
    f = sub.add_parser("finalize", help="refuse, or apply caps and render the verdict")
    f.add_argument("worksheet")
    f.add_argument("--out", default="verdict.html")
    f.add_argument("--title", default="Project review")
    f.add_argument("--project", help="the project directory, when it has moved since prepare")
    v = sub.add_parser("verify", help="check every file:line citation still matches")
    v.add_argument("worksheet")
    v.add_argument("--project")
    a = ap.parse_args(argv)
    return {"prepare": cmd_prepare, "finalize": cmd_finalize, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
