#!/usr/bin/env python3
"""Install this repository's skills and agent roles into any agent host.

  python3 install.py --dest <skills-dir> [--agents-dest <agents-dir>] [--dry-run] [--force]
  python3 install.py --list

Each skill is copied whole, with its scripts and references, to <skills-dir>/<skill-name>/.
Each role is copied to <agents-dir>/<role>.md. Nothing is ever deleted. An existing skill or
role is left alone unless --force is given, and then only the files this repository ships are
overwritten.

Exit codes: 0 installed (or nothing to do), 1 refused because something already exists,
2 bad arguments.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "quiet_counsel"


def skills():
    root = os.path.join(HERE, "skills")
    return sorted(d for d in os.listdir(root)
                  if os.path.isfile(os.path.join(root, d, "SKILL.md")))


def roles():
    root = os.path.join(HERE, "agents")
    return sorted(f for f in os.listdir(root) if f.endswith(".md"))


def files_of(skill):
    base = os.path.join(HERE, "skills", skill)
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            src = os.path.join(dirpath, name)
            yield src, os.path.relpath(src, base)


def plan(dest, agents_dest):
    steps, conflicts = [], []
    if dest:
        for s in skills():
            target = os.path.join(dest, s)
            if os.path.exists(target):
                conflicts.append(target)
            for src, rel in files_of(s):
                steps.append((src, os.path.join(target, rel)))
    if agents_dest:
        for r in roles():
            target = os.path.join(agents_dest, r)
            if os.path.exists(target):
                conflicts.append(target)
            steps.append((os.path.join(HERE, "agents", r), target))
    return steps, conflicts


def importable():
    r = subprocess.run([sys.executable, "-c", f"import {PACKAGE}"], capture_output=True)
    return r.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dest", help="the directory your host reads skills from")
    ap.add_argument("--agents-dest", help="the directory your host reads agent roles from")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    ap.add_argument("--force", action="store_true", help="overwrite files this repository ships")
    ap.add_argument("--list", action="store_true", help="list the skills and roles, then stop")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    a = ap.parse_args(argv)

    if a.list:
        out = {"skills": skills(), "agents": [r[:-3] for r in roles()]}
        print(json.dumps(out, indent=2) if a.json else
              "skills: " + ", ".join(out["skills"]) + "\nagents: " + ", ".join(out["agents"]))
        return 0
    if not a.dest and not a.agents_dest:
        ap.print_usage(sys.stderr)
        print("give --dest, --agents-dest, or both", file=sys.stderr)
        return 2

    steps, conflicts = plan(a.dest, a.agents_dest)
    if conflicts and not a.force:
        print("refused: these already exist, and nothing was written:", file=sys.stderr)
        for c in conflicts:
            print(f"  {c}", file=sys.stderr)
        print("re-run with --force to overwrite the files this repository ships", file=sys.stderr)
        return 1

    for src, dst in steps:
        if a.dry_run:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    ok = importable()
    result = {"dry_run": a.dry_run, "files": len(steps),
              "skills": [os.path.join(a.dest, s) for s in skills()] if a.dest else [],
              "agents": [os.path.join(a.agents_dest, r) for r in roles()] if a.agents_dest else [],
              "package_importable": ok}
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        verb = "would install" if a.dry_run else "installed"
        for p in result["skills"]:
            print(f"{verb} skill {p}")
        for p in result["agents"]:
            print(f"{verb} role  {p}")
        if not ok:
            print(f"\nThe skills' scripts need the {PACKAGE} package. From this directory, run: "
                  f"pip install .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
