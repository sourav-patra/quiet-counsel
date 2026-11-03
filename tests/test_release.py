"""Suite R: the release gate. tools/gate.py stands between a release branch and a tag, locally and
in the gate workflow, so it is held to the same standard as the tool."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO

GATE = REPO / "tools" / "gate.py"


def release_tree(version="1.2.3", changelog_top=None, readme=None, pyproject=None, workflows=False):
    root = Path(tempfile.mkdtemp(prefix="gate-test-"))
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (root / "pyproject.toml").write_text(f'[project]\nname = "pkg"\nversion = "{pyproject or version}"\n',
                                         encoding="utf-8")
    top = changelog_top or f"{version} (2026-09-25)"
    (root / "CHANGELOG.md").write_text(f"# Changelog\n\n## {top}\n\n- a change\n\n## 0.0.1 (2026-09-24)\n",
                                       encoding="utf-8")
    (root / "README.md").write_text(readme or f"Status: v{version}.\n\npip install \"git+<url>@v{version}\"\n",
                                    encoding="utf-8")
    if workflows:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "ci.yml").write_text(workflows, encoding="utf-8")
    return root


def runs(workflow_text, command):
    """True when a line is exactly a `- run:` step for the command, so no comment can satisfy it."""
    return re.search(r"^\s*-\s*run:\s*" + re.escape(command) + r"\s*$", workflow_text, re.M) is not None


def gate(*args):
    return subprocess.run([sys.executable, str(GATE), *args], capture_output=True, text=True)


class ReleaseGate(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for r in self.roots:
            shutil.rmtree(r, ignore_errors=True)

    def tree(self, **kw):
        root = release_tree(**kw)
        self.roots.append(root)
        return str(root)

    def test_R01_a_tree_whose_versions_agree_passes_the_release_checks(self):
        r = gate("--release", "1.2.3", "--skip-tests", "--root", self.tree())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gate: passed", r.stdout)

    def test_R02_a_version_the_tree_does_not_carry_is_refused_by_name(self):
        r = gate("--release", "1.2.3", "--skip-tests", "--root", self.tree(pyproject="1.2.2"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("pyproject.toml carries version 1.2.2", r.stdout)

    def test_R03_an_unreleased_changelog_or_a_stale_readme_is_refused(self):
        r = gate("--release", "1.2.3", "--skip-tests", "--root", self.tree(changelog_top="Unreleased"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHANGELOG.md", r.stdout)
        r = gate("--release", "1.2.3", "--skip-tests", "--root",
                 self.tree(readme="Status: v1.2.3.\n\npip install \"git+<url>@v0.0.1\"\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("README.md names v0.0.1, v1.2.3", r.stdout)

    def test_R04_a_workflow_that_skips_the_gate_is_refused(self):
        r = gate("--release", "1.2.3", "--skip-tests", "--root", self.tree(workflows="on: push\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn(".github/workflows/ci.yml does not run tools/gate.py", r.stdout)
        r = gate("--release", "1.2.3", "--skip-tests", "--root",
                 self.tree(workflows="on: push\njobs:\n  g:\n    steps:\n      - run: python3 tools/gate.py\n"))
        self.assertNotIn("does not run tools/gate.py", r.stdout)
        root = self.tree(workflows="on: push\n")
        (Path(root) / ".github" / "workflows" / "docs-lint.yml").write_text("on: pull_request\n", encoding="utf-8")
        r = gate("--release", "1.2.3", "--skip-tests", "--root", root)
        self.assertIn(".github/workflows/ci.yml does not run tools/gate.py", r.stdout)
        self.assertNotIn("docs-lint.yml", r.stdout)

    def test_R05_build_workflows_in_this_repository_run_the_gate(self):
        wf = REPO / ".github" / "workflows"
        for f in sorted(wf.iterdir()) if wf.is_dir() else []:
            if f.name != "docs-lint.yml":  # builds nothing; R-08 holds it to the README lint
                self.assertIn("tools/gate.py", f.read_text(encoding="utf-8"), f.name)

    def test_R08_the_docs_lint_workflow_runs_both_readme_lint_commands(self):
        both = ("python3 scripts/readme_lint.py --self-test", "python3 scripts/readme_lint.py README.md")
        text = (REPO / ".github" / "workflows" / "docs-lint.yml").read_text(encoding="utf-8")
        for cmd in both:
            self.assertTrue(runs(text, cmd), cmd)
        self.assertFalse(runs("".join(f"# - run: {c}\n" for c in both), both[0]))
        self.assertFalse(runs("name: docs-lint # " + both[0] + "\n", both[0]))

    def test_R06_a_malformed_version_is_bad_input(self):
        r = gate("--release", "v1.2", "--skip-tests")
        self.assertEqual(r.returncode, 2)
        self.assertIn("X.Y.Z", r.stderr)

    def test_R07_the_gate_uses_the_standard_library_and_names_no_host_or_person(self):
        text = GATE.read_text(encoding="utf-8")
        imports = {line.split()[1].split(".")[0] for line in text.splitlines()
                   if line.startswith(("import ", "from "))}
        self.assertLessEqual(imports, {"argparse", "os", "re", "shutil", "subprocess", "sys"})
        self.assertNotIn("http", text)
