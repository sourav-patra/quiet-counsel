"""Shared fixtures. Every project a test needs is built in a temporary directory from a dict of
files, so no test depends on a real repository and none leaves anything behind in the tree."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
PKG = "quiet_counsel"
ENV = "QUIET_COUNSEL"
os.environ[f"{ENV}_NOW"] = "2026-09-24T00:00:00Z"

from quiet_counsel import dashboard, sample, scan, schema  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
           "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}


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
        run("add", "-A")
        run("commit", "-qm", "first", "--date", (commits or {}).get("first_date",
                                                                  "2026-09-20T10:00:00Z"))
    return str(root)


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
