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


def fingerprint(root, skip=()):
    """Every file's path and content hash, so finalize can tell whether the project changed
    during the review. Symbolic links are recorded by target and never followed; pipes and
    devices are recorded by kind and never read. A directory that resolves outside the root (a
    junction, or a link a walk would follow) is recorded as such and not entered, and a file is
    hashed only when it resolves inside the root. `skip` names the review's own files."""
    skip = {os.path.abspath(p) for p in skip if p}
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git" and d not in TOOL_CACHES)
        for d in list(dirnames):
            if not contained(root, os.path.join(dirpath, d)):
                dirnames.remove(d)
                files[os.path.relpath(os.path.join(dirpath, d), root).replace(os.sep, "/")] = "outside"
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
                with open(path, "rb") as fh:
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
        if value.startswith("link:"):
            value = "link:" + label(scan, value[5:])
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
    held = [f["id"] for f in card["flags"] if f.get("caps") == "do-not-score" and f["severity"] != "info"]
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
    return {f["caps"] for f in card["flags"] if f.get("caps") and f["severity"] != "info"}


def cmd_finalize(a):
    dashboard, scan, schema = load()
    with open(a.worksheet, encoding="utf-8") as fh:
        card = json.load(fh)
    # a problem can quote project text (a claim, a flag id), so each one passes the same withholding
    reasons = [scan.withhold_text(p, "problem") for p in schema.problems(card)]
    reasons += tree_changes(card, a.project, skip=(a.worksheet, a.out))
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
            print(f"  {r}")
        return 1

    effective, applied = {}, []
    for d in card["dimensions"]:
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
    # renderer gets both pass the one output filter; the renderer itself filters nothing.
    card = scan.withhold_all(card)
    with open(a.worksheet, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    page = dashboard.build([card], a.title, strict=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"verdict written to {a.out}: mean {card['totals']['mean']} over "
          f"{len(effective)} applicable dimensions" + (f", caps {', '.join(applied)}" if applied else ""))
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
    bad, unverifiable, ok = [], [], 0

    def ref_of(e):
        """A reference as printed: a path that holds a credential or aimed text becomes a notice."""
        return scan.withhold_text(str(e.get("ref")), "reference")

    for d in card["dimensions"]:
        for e in d.get("evidence") or []:
            if e.get("kind") != "file":
                unverifiable.append(f"{d['id']}: {scan.withhold_text(str(e.get('kind')), 'kind')} "
                                    f"{ref_of(e)} (re-run it to check)")
                continue
            head, _, tail = e["ref"].rpartition(":")
            if not tail.isdigit():
                bad.append(f"{d['id']}: {ref_of(e)} has no line number")
                continue
            path = inside(root, head)
            if not path:
                bad.append(f"{d['id']}: {ref_of(e)} is a broken citation: it leaves the project")
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
                if not 1 <= int(tail) <= len(lines):
                    raise IndexError
                line = lines[int(tail) - 1]
            except (OSError, IndexError):
                bad.append(f"{d['id']}: {ref_of(e)} does not exist")
                continue
            want = (e.get("excerpt") or "").strip()
            if want and want not in line:
                # the excerpt is project text the reviewer copied: printed only if it passes the test
                bad.append(f"{d['id']}: {ref_of(e)} no longer reads "
                           f"{scan.withhold_text(want, 'excerpt')!r}")
            else:
                ok += 1
    print(f"{ok} citation(s) match")
    for u in unverifiable:
        print(f"  not checked: {u}")
    for b in bad:
        print(f"  MISMATCH: {b}")
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
