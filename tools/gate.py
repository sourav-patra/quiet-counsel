"""The release gate, run on a workstation and by the `gate` workflow.

The workflow runs this script, so what passes here passes there.

    python3 tools/gate.py                      # the suite on every Python it finds, and the C-locale run
    python3 tools/gate.py --release 0.0.2      # the same, plus the checks a release commit must pass
    python3 tools/gate.py --require-all        # a missing Python version is a failure, not a note

Exit 0 when every check passed, 1 when any failed (each failure is printed), 2 on bad input.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
VERSIONS = ("3.11", "3.12", "3.13")
SUITE = ["-m", "unittest", "discover", "-s", "tests", "-t", "tests"]
NO_UTF8 = {"LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"}
# builds nothing; it runs the README lint (case R-08)
NO_GATE_WORKFLOW = "docs-lint.yml"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(-rc\.\d+)?$")


def interpreters():
    """Every supported Python on PATH, by version, plus the one running this script."""
    found = {}
    for v in VERSIONS:
        exe = shutil.which(f"python{v}")
        if exe:
            found[v] = exe
    here = f"{sys.version_info.major}.{sys.version_info.minor}"
    if here in VERSIONS and here not in found:
        found[here] = sys.executable
    return found


def run_suite(exe, root, extra_env=None):
    env = dict(os.environ, TZ="UTC",
               PYTHONPATH=os.pathsep.join([os.path.join(root, "src"), os.path.join(root, "tests")]))
    env.update(extra_env or {})
    r = subprocess.run([exe, *SUITE], cwd=root, env=env, capture_output=True, text=True)
    tail = [ln for ln in r.stderr.strip().splitlines() if ln.strip()][-2:]
    return r.returncode == 0, " ".join(tail)


def package_init(root):
    src = os.path.join(root, "src")
    for name in sorted(os.listdir(src)) if os.path.isdir(src) else []:
        p = os.path.join(src, name, "__init__.py")
        if os.path.isfile(p):
            return p
    return None


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def release_problems(root, version):
    """What a release commit for `version` must carry. Returns a list of problems."""
    problems = []
    pyproject = read(os.path.join(root, "pyproject.toml")) or ""
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject)
    if not m or m.group(1) != version:
        problems.append(f"pyproject.toml carries version {m.group(1) if m else 'none'}, not {version}")
    init = package_init(root)
    m = re.search(r'__version__\s*=\s*"([^"]+)"', read(init) or "") if init else None
    if not m or m.group(1) != version:
        problems.append(f"the package carries __version__ {m.group(1) if m else 'none'}, not {version}")
    changelog = read(os.path.join(root, "CHANGELOG.md")) or ""
    top = re.search(r"(?m)^## (.+)$", changelog)
    if not top or not top.group(1).startswith(f"{version} ("):
        problems.append(f"the top section of CHANGELOG.md is '{top.group(1) if top else 'none'}', "
                        f"not '{version} (YYYY-MM-DD)'")
    readme = read(os.path.join(root, "README.md")) or ""
    named = sorted(set(re.findall(r"\bv(\d+\.\d+\.\d+)\b", readme)))
    if named != [version.split("-")[0]]:
        problems.append(f"README.md names {', '.join('v' + n for n in named) or 'no version'}; "
                        f"its status line and install line should both name v{version.split('-')[0]}")
    wf_dir = os.path.join(root, ".github", "workflows")
    for name in sorted(os.listdir(wf_dir)) if os.path.isdir(wf_dir) else []:
        if name != NO_GATE_WORKFLOW and "tools/gate.py" not in (read(os.path.join(wf_dir, name)) or ""):
            problems.append(f".github/workflows/{name} does not run tools/gate.py; "
                            "every workflow must run the same gate")
    if os.path.isdir(os.path.join(root, ".git")):
        r = subprocess.run(["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            problems.append("the working tree has uncommitted changes:\n" + r.stdout.rstrip())
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gate", description="The release gate, run locally.")
    ap.add_argument("--release", metavar="X.Y.Z", help="also check the tree is a release commit for this version")
    ap.add_argument("--require-all", action="store_true",
                    help=f"fail when any of Python {', '.join(VERSIONS)} is missing")
    ap.add_argument("--skip-tests", action="store_true", help="run only the release checks")
    ap.add_argument("--root", default=REPO, help="the tree to gate (default: this repository)")
    a = ap.parse_args(argv)
    if a.release and not SEMVER.match(a.release):
        print(f"gate: --release takes X.Y.Z or X.Y.Z-rc.N, not {a.release!r}", file=sys.stderr)
        return 2
    root = os.path.abspath(a.root)
    failed = False

    if not a.skip_tests:
        found = interpreters()
        if not found:
            print(f"FAIL  no supported Python on PATH ({', '.join(VERSIONS)}); this one is "
                  f"{sys.version_info.major}.{sys.version_info.minor}")
            return 1
        for v in VERSIONS:
            if v not in found:
                print(f"{'FAIL' if a.require_all else 'NOTE'}  Python {v}: not on PATH, not run")
                failed |= a.require_all
                continue
            ok, tail = run_suite(found[v], root)
            print(f"{'PASS' if ok else 'FAIL'}  suite on Python {v}: {tail}")
            failed |= not ok
        if os.name == "posix":
            v = sorted(found)[0]
            ok, tail = run_suite(found[v], root, NO_UTF8)
            print(f"{'PASS' if ok else 'FAIL'}  suite without a UTF-8 locale, Python {v}: {tail}")
            failed |= not ok
        else:
            print("NOTE  the run without a UTF-8 locale needs a POSIX shell, not run")

    if a.release:
        problems = release_problems(root, a.release)
        for p in problems:
            print(f"FAIL  release {a.release}: {p}")
        if not problems:
            print(f"PASS  release {a.release}: versions, changelog, README and working tree agree")
        failed |= bool(problems)

    print("gate: failed" if failed else "gate: passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
