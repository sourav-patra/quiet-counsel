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


def fingerprint(root, skip=()):
    """Every file's path and content hash, so finalize can tell whether the project changed
    during the review. Symbolic links are recorded by target and never followed; pipes and
    devices are recorded by kind and never read. `skip` names the review's own files."""
    skip = {os.path.abspath(p) for p in skip if p}
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git" and d not in TOOL_CACHES)
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
            h = hashlib.sha256()
            try:
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                files[rel] = h.hexdigest()
            except OSError:
                files[rel] = "unreadable"
    return files


def digest(files):
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(f"{rel}\0{files[rel]}\n".encode("utf-8"))
    return h.hexdigest()


def cmd_prepare(a):
    _, scan, _ = load()
    if not os.path.isdir(a.project):
        print(f"not a directory: {a.project}", file=sys.stderr)
        return 2
    card = scan.screen(a.project, a.corpus, honour_ignore=False)
    card["mode"] = "deep"
    files = fingerprint(a.project, skip=(a.out,))
    card["project"]["tree_sha256"] = digest(files)
    card["project"]["tree_files"] = {rel: files[rel] for rel in sorted(files)}
    card["project"]["tree_root"] = os.path.abspath(a.project)
    for d in card["dimensions"]:
        d["confidence"] = "judged"
        d["rationale"] = ""
        d["evidence"] = []
        if d["applicable"]:
            d["anchor"] = ANCHOR[d["id"]]
            d["look_at"] = LOOK_AT[d["id"]]
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
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
    proj = card.get("project", {})
    old = proj.get("tree_files")
    if old is None:
        return ["the worksheet has no tree fingerprint; prepare it again with this version"]
    root = project or proj.get("tree_root") or proj["path"]
    if not os.path.isdir(root):
        return [f"cannot find the project at {root} to confirm it is unchanged; pass --project"]
    skipped = {os.path.relpath(os.path.abspath(p), os.path.abspath(root)).replace(os.sep, "/")
               for p in skip if p}
    old = {r: v for r, v in old.items() if r not in skipped}
    new = fingerprint(root, skip=skip)
    changed = sorted(r for r in set(old) | set(new) if old.get(r) != new.get(r))
    if not changed:
        return []
    shown = ", ".join(changed[:5]) + (f" and {len(changed) - 5} more" if len(changed) > 5 else "")
    return [f"the project changed after prepare ({len(changed)} file(s): {shown}); a review "
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
    dashboard, _, schema = load()
    with open(a.worksheet, encoding="utf-8") as fh:
        card = json.load(fh)
    reasons = list(schema.problems(card))
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
    with open(a.worksheet, encoding="utf-8") as fh:
        card = json.load(fh)
    root = a.project or card["project"]["path"]
    bad, unverifiable, ok = [], [], 0
    for d in card["dimensions"]:
        for e in d.get("evidence") or []:
            if e.get("kind") != "file":
                unverifiable.append(f"{d['id']}: {e.get('kind')} {e.get('ref')} (re-run it to check)")
                continue
            head, _, tail = e["ref"].rpartition(":")
            if not tail.isdigit():
                bad.append(f"{d['id']}: {e['ref']} has no line number")
                continue
            path = inside(root, head)
            if not path:
                bad.append(f"{d['id']}: {e['ref']} is a broken citation: it leaves the project")
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
                if not 1 <= int(tail) <= len(lines):
                    raise IndexError
                line = lines[int(tail) - 1]
            except (OSError, IndexError):
                bad.append(f"{d['id']}: {e['ref']} does not exist")
                continue
            want = (e.get("excerpt") or "").strip()
            if want and want not in line:
                bad.append(f"{d['id']}: {e['ref']} no longer reads {want!r}")
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
