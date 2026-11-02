"""Suite G: generic and portable. Nothing in this tool may assume a person, an organisation, a
forge host, a model, a directory layout or an operating system. These tests are the mandatory
guard against hard-binding, and a change that makes one fail is asking to bind the product to
one setup."""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import CLEAN_CATALOGUE, ENV, PKG, REPO, SRC, project, run_cli, scan

# Patterns that must never appear in the public tree: one machine's paths, private e-mail
# domains, internal hosts. Organisation and person names are NOT listed here, because listing
# them would itself bind the repository. A maintainer adds their own through QUIET_COUNSEL_FORBIDDEN_TOKENS
# ("name1,name2") or a file named by QUIET_COUNSEL_FORBIDDEN_FILE, kept outside the repository.
# The home-directory prefix is split so the release preflight's own scan does not match this line.
GENERIC = (r"(/Us" r"ers/[a-z]|C:\\Users\\|/home/[a-z]+/Projects"
           r"|\b[a-z0-9-]+(\.[a-z0-9-]+)*\.(corp|internal)\b"
           r"|@[a-z0-9-]+\.(com|io)\b)")

PUBLIC = ("src", "docs", "tests", "tools", "examples", "skills", "agents", "evals", "README.md",
          "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
          "RELEASING.md", "pyproject.toml", "install.py", "install.sh", ".scanignore")


def forbidden():
    extra = [t.strip() for t in os.environ.get(f"{ENV}_FORBIDDEN_TOKENS", "").split(",")
             if t.strip()]
    f = os.environ.get(f"{ENV}_FORBIDDEN_FILE")
    if f and Path(f).exists():
        extra += [t.strip() for t in Path(f).read_text(encoding="utf-8").splitlines()
                  if t.strip() and not t.startswith("#")]
    return re.compile(GENERIC + ("|" + "|".join(re.escape(t) for t in extra) if extra else ""),
                      re.IGNORECASE)


def public_files():
    me = Path(__file__).resolve()
    for top in PUBLIC:
        p = REPO / top
        if not p.exists():
            continue
        for f in ([p] if p.is_file() else sorted(p.rglob("*"))):
            if f.is_file() and "__pycache__" not in f.parts and f.resolve() != me \
                    and f.suffix not in (".png", ".pyc"):
                yield f


class NoHardBinding(unittest.TestCase):
    def test_G01_public_tree_names_no_person_org_or_machine(self):
        rx, hits = forbidden(), []
        for f in public_files():
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if "noreply@anthropic.com" in line:
                    continue
                if rx.search(line):
                    hits.append(f"{f.relative_to(REPO)}:{n}: {line.strip()[:90]}")
        self.assertEqual(hits, [], "hard-binding tokens in the public tree:\n" + "\n".join(hits))

    def test_G03_no_module_can_reach_the_network(self):
        banned = {"socket", "urllib", "http", "ssl", "requests", "httpx", "ftplib", "smtplib"}
        found = []
        for f in [*SRC.rglob("*.py"), *(REPO / "tools").glob("*.py"),
                  *(REPO / "skills").rglob("*.py"), REPO / "install.py"]:
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    names = [node.module.split(".")[0]]
                found += [f"{f.name}: {n}" for n in names if n in banned]
        self.assertEqual(found, [], "network-capable imports in the tool")

    def test_G04_help_and_refusals_name_no_product_org_or_person(self):
        texts = [run_cli("--help").stdout]
        for sub in ("classify", "screen", "integrity", "dashboard", "check", "sample"):
            texts.append(run_cli(sub, "--help").stdout)
        texts.append(run_cli("classify", "/nonexistent-dir-for-test").stderr)
        texts.append(run_cli("screen", "/nonexistent-dir-for-test").stderr)
        blob = "\n".join(texts)
        rx = re.compile(r"\b(claude|anthropic|openai|gpt|gemini|copilot|cursor)\b", re.I)
        self.assertIsNone(rx.search(blob), rx.search(blob) and rx.search(blob).group(0))
        self.assertIsNone(forbidden().search(blob))


class AnyDirectory(unittest.TestCase):
    def test_G02_fresh_directory_stdlib_only_end_to_end(self):
        d = Path(tempfile.mkdtemp())
        steps = (["sample", str(d / "proj")],
                 ["screen", str(d / "proj"), "--out", str(d / "cards")],
                 ["check", str(d / "cards" / "proj.json")],
                 ["dashboard", str(d / "cards" / "proj.json"), "--out", str(d / "page.html")])
        for argv in steps:
            r = run_cli(*argv)
            self.assertEqual(r.returncode, 0, f"{argv}: {r.stdout}{r.stderr}")
        self.assertTrue((d / "page.html").stat().st_size > 5000)

    def test_G05_scorecard_carries_no_absolute_path_of_this_machine(self):
        root = project(CLEAN_CATALOGUE)
        parent, name = os.path.split(root)
        cwd = os.getcwd()
        try:
            os.chdir(parent)
            card = scan.screen(name)
        finally:
            os.chdir(cwd)
        self.assertEqual(card["project"]["path"], name)
        self.assertNotIn(parent, json.dumps(card))

    def test_G06_same_tree_same_scorecard_byte_for_byte(self):
        root = project(CLEAN_CATALOGUE)
        a = json.dumps(scan.screen(root), sort_keys=True)
        b = json.dumps(scan.screen(root), sort_keys=True)
        self.assertEqual(a, b)

    def test_G09_a_screen_with_every_socket_refused_matches_a_normal_run_byte_for_byte(self):
        root = Path(project({**CLEAN_CATALOGUE, ".github/workflows/w.yml": "on: push\n"}))
        refuse = "; ".join([
            "import socket, sys",
            "socket.socket = lambda *a, **k: sys.exit('a socket was opened')",
            "from quiet_counsel import cli",
            "sys.exit(cli.main(['screen', 'proj', '--out', 'refused']))"])
        env = {**os.environ, "PYTHONPATH": str(SRC), f"{ENV}_NOW": "2026-09-24T00:00:00Z"}
        outs = []
        for name, cmd in (("normal", [sys.executable, "-m", PKG, "screen", "proj", "--out", "normal"]),
                          ("refused", [sys.executable, "-c", refuse])):
            r = subprocess.run(cmd, cwd=root.parent, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stderr)
            outs.append((root.parent / name / "proj.json").read_bytes())
        self.assertEqual(outs[0], outs[1])

    def test_G07_a_directory_that_is_not_a_repository_still_screens(self):
        card = scan.screen(project(CLEAN_CATALOGUE))
        hist = card["signals"]["history"]["value"]
        self.assertFalse(hist["available"])
        self.assertIn("reason", hist)
        self.assertTrue(any("Provenance was not measured" in l for l in card["limits"]))
