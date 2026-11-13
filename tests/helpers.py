"""Shared fixtures. Every project a test needs is built in a temporary directory from a dict of
files, so no test depends on a real repository and none leaves anything behind in the tree."""

import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
PKG = "quiet_counsel"
ENV = "QUIET_COUNSEL"
os.environ[f"{ENV}_NOW"] = "2026-09-24T00:00:00Z"

# One scratch folder per test process: every mkdtemp in the suite lands inside it, and it is
# removed at exit (read-only git objects included) so repeated runs leave nothing in %TEMP%.
SCRATCH = tempfile.mkdtemp(prefix="scan-test-run-")
tempfile.tempdir = SCRATCH


def _make_writable_and_retry(func, path, _exc):
    """rmtree error hook: read-only git objects get their mode fixed; a path that has already
    vanished (a background git job removed it) is not an error."""
    if not os.path.lexists(path):
        return
    os.chmod(path, 0o700)
    func(path)


def _remove_scratch(tries=6):
    """Remove the scratch folder without writing to stderr. A background git job (auto gc or
    maintenance) can still be writing into a fixture repo while the tree is deleted, which makes
    rmtree fail on a directory that is not yet empty; waiting briefly and deleting again clears it."""
    for attempt in range(tries):
        try:
            shutil.rmtree(SCRATCH, onerror=_make_writable_and_retry)
        except OSError:
            pass
        if not os.path.exists(SCRATCH):
            return
        time.sleep(0.25 * (attempt + 1))
    shutil.rmtree(SCRATCH, ignore_errors=True)


atexit.register(_remove_scratch)

from quiet_counsel import dashboard, sample, scan, schema  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
           "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
           # No background gc or maintenance job may outlive a fixture git call and write into
           # the folder while it is being deleted at exit.
           "GIT_CONFIG_COUNT": "2",
           "GIT_CONFIG_KEY_0": "gc.auto", "GIT_CONFIG_VALUE_0": "0",
           "GIT_CONFIG_KEY_1": "maintenance.auto", "GIT_CONFIG_VALUE_1": "false"}


def fake_key():
    """A string with the shape of a cloud access key, assembled so no literal one is committed."""
    return "AK" + "IA" + "Q3XW7PLMNB4TR2ZE"


def fake_shapes():
    """One planted value per credential shape, assembled at run time."""
    return {"aws": fake_key(), "github": "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3",
            "slack": "xo" + "xb-" + "1234567890-abcdefghij",
            "google": "AI" + "za" + "Sy" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q",
            "stripe": "sk" + "_live_" + "A1b2C3d4E5f6G7h8I9j0K1l2",
            "jwt": "ey" + "Jhbgcioijiuzi1nigabc." + "eyJzdWIiOiIxMjM0NTY3ODkw." + "abcdefghijKLMNOP1234"}


def fake_secret_value():
    """A 40-character secret-access-key-shaped value, assembled from short pieces."""
    return "".join(["wJalr", "XUtnF", "EMI/K", "7MDEN", "G/bPx", "RfiCY", "QZ91A", "BCDEF"])


def fake_pem():
    return "-----BEGIN " + "RSA PRIVATE KEY" + "-----"


def project(files, git=False, commits=None, name=None):
    """Write files (relative path -> text) into a fresh directory and return its path."""
    base = Path(tempfile.mkdtemp(prefix="scan-test-"))
    root = base / (name or "proj")
    root.mkdir()
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    if git or commits:
        env = {**os.environ, **GIT_ENV}
        run = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, env=env,
                                        capture_output=True)
        run("init", "-q")
        for attempt in range(4):
            try:
                run("add", "-A")
                break
            except subprocess.CalledProcessError as e:
                # Windows briefly locks .git/objects (about 1 run in 40); any other failure raises.
                err = e.stderr or b""
                if attempt == 3 or e.returncode != 128 or b".git/objects" not in err                         or b"Permission denied" not in err:
                    raise
                time.sleep(0.2)
        run("commit", "-qm", "first", "--date", (commits or {}).get("first_date",
                                                                  "2026-09-20T10:00:00Z"))
    return str(root)


class ReadLog:
    """Record every path the code under test touches. While it is active, `open`, `os.scandir`,
    `os.listdir` and `subprocess.run` (git calls: the folder, `-C`, and the GIT_* variables handed
    over) log what they are given, then run as usual. `walk` and `glob` list through `os.scandir`,
    so their listings are in `paths` too. Create the fixtures first; enter it around one call."""

    def __init__(self):
        self.paths, self.git_calls, self._undo = [], [], []

    def __enter__(self):
        import builtins
        import io
        from unittest import mock
        real_open, real_io_open, real_scandir = builtins.open, io.open, os.scandir
        real_listdir, real_run = os.listdir, subprocess.run

        def note(path):
            if isinstance(path, (str, bytes, os.PathLike)):
                self.paths.append(os.fsdecode(path))

        def opening(file, *a, **kw):
            note(file)
            return real_open(file, *a, **kw)

        def io_opening(file, *a, **kw):
            note(file)
            return real_io_open(file, *a, **kw)

        def scanning(path=None):
            note(path if path is not None else ".")
            return real_scandir(path) if path is not None else real_scandir()

        def listing(path=None):
            note(path if path is not None else ".")
            return real_listdir(path) if path is not None else real_listdir()

        def running(cmd, *a, **kw):
            if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
                env = kw.get("env") or {}
                call = {"args": list(cmd), "cwd": kw.get("cwd"),
                        "git_dir": env.get("GIT_DIR"), "work_tree": env.get("GIT_WORK_TREE"),
                        "ceiling": env.get("GIT_CEILING_DIRECTORIES")}
                if "-C" in cmd:
                    call["cwd"] = cmd[cmd.index("-C") + 1]
                self.git_calls.append(call)
            return real_run(cmd, *a, **kw)

        for target, name, repl in ((builtins, "open", opening), (io, "open", io_opening),
                                   (os, "scandir", scanning), (os, "listdir", listing),
                                   (subprocess, "run", running)):
            patcher = mock.patch.object(target, name, repl)
            patcher.start()
            self._undo.append(patcher)
        return self

    def __exit__(self, *exc):
        for patcher in reversed(self._undo):
            patcher.stop()
        return False

    @staticmethod
    def _inside(root, path):
        base = os.path.normcase(os.path.realpath(root))
        real = os.path.normcase(os.path.realpath(path))
        try:
            return os.path.commonpath([base, real]) == base
        except ValueError:
            return False

    def outside(self, root):
        """Every logged path, and every folder or git location a git call was given, that
        resolves outside `root`."""
        out = [p for p in self.paths if not self._inside(root, p)]
        for call in self.git_calls:
            out += [p for p in (call["cwd"], call["git_dir"], call["work_tree"])
                    if p and not self._inside(root, p)]
        return out

    def touched(self, folder):
        """True when some logged path is, or is under, `folder` once links are resolved."""
        return any(self._inside(folder, p) for p in self.paths)


def screen(files, **kw):
    return scan.screen(project(files, **kw))


def flag_ids(card):
    return {f["id"] for f in card["flags"]}


def flag(card, fid):
    return next((f for f in card["flags"] if f["id"] == fid), None)


def run_cli(*args, cwd=None):
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    return subprocess.run([sys.executable, "-m", PKG, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, cwd=cwd)


MINIMAL = {
    "README.md": "# Tool\n\nDoes one thing.\n",
    "LICENSE": "MIT License\n\nCopyright (c) 2026 Someone\n",
}

CLEAN_CATALOGUE = {
    **MINIMAL,
    "skills/alpha/SKILL.md": "---\nname: alpha\ndescription: Does alpha. Use when alpha is needed.\n---\nBody.\n",
    "skills/beta/SKILL.md": "---\nname: beta\ndescription: Does beta. Use when beta is needed.\n---\nBody.\n",
    "tests/test_alpha.py": "def test_alpha():\n    assert True\n",
    ".github/workflows/ci.yml": "on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
                                "      - uses: actions/checkout@" + "a" * 40 + "\n",
}
