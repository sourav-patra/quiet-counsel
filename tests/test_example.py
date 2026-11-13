"""Suite E: the example that ships in the repository. It is the first thing a reader opens, so
it must show every detector firing, stay current with the code, and carry no credential shape
that a forge's push protection would block."""

import importlib.util
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import REPO, flag_ids, sample, scan

# The same expression the release preflight runs over the tree. Its literal prefixes are split
# so this file does not match itself.
SECRET_SCAN = re.compile("(gh[pousr]_[A-Za-z0-9]{20,}|" + "github" + "_pat_|AK" + "IA[0-9A-Z]{16}|"
                         + "sk-" + "ant-|" + "ATA" + "TT|-----BEGIN [A-Z ]*PRIVATE KEY)")


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Example(unittest.TestCase):
    def test_E01_the_sample_project_raises_every_planted_flag(self):
        root = sample.write(str(Path(tempfile.mkdtemp()) / "sample-project"))
        found = flag_ids(scan.screen(root))
        for planted in sample.PLANTED + sample.ALSO_EXPECTED:
            self.assertIn(planted, found)

    def test_E02_the_committed_example_is_current(self):
        card, page = _tool("gen_example").build()
        self.assertEqual((REPO / "examples" / "sample-scorecard.json").read_text(encoding="utf-8"), card,
                         "examples/ is stale: run python3 tools/gen_example.py")
        self.assertEqual((REPO / "examples" / "sample-dashboard.html").read_text(encoding="utf-8"), page)

    def test_E03_no_complete_credential_shape_exists_anywhere_in_the_tree(self):
        hits = []
        for f in REPO.rglob("*"):
            if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts:
                for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if SECRET_SCAN.search(line):
                        hits.append(f"{f.relative_to(REPO)}:{n}")
        self.assertEqual(hits, [], "credential shapes in the tree: " + ", ".join(hits))

    def test_E04_evidence_order_does_not_depend_on_the_order_the_filesystem_lists(self):
        base = Path(tempfile.mkdtemp())
        sample.write(str(base / "sample-project"))
        real_walk, real_listdir = os.walk, os.listdir

        def reversed_walk(top, *args, **kwargs):
            for dirpath, dirnames, filenames in real_walk(top, *args, **kwargs):
                # In place, so the scanner's pruning of dirnames still steers the real walk.
                dirnames.reverse()
                filenames.reverse()
                yield dirpath, dirnames, filenames

        cwd = os.getcwd()
        try:
            os.chdir(base)
            forward = json.dumps(scan.screen("sample-project"), sort_keys=True)
            with mock.patch.object(os, "walk", reversed_walk), \
                 mock.patch.object(os, "listdir", lambda p=".": list(reversed(real_listdir(p)))):
                backward = json.dumps(scan.screen("sample-project"), sort_keys=True)
        finally:
            os.chdir(cwd)
        self.assertEqual(forward, backward)

    def test_E05_the_committed_example_withholds_the_planted_phrase_and_the_live_sample_still_blocks(self):
        phrase = sample._directed()
        for name in ("sample-scorecard.json", "sample-dashboard.html"):
            self.assertNotIn(phrase, (REPO / "examples" / name).read_text(encoding="utf-8"), name)
        card = scan.screen(sample.write(str(Path(tempfile.mkdtemp()) / "sample-project")))
        f = next(x for x in card["flags"] if x["id"] == "evaluator-directed-text")
        self.assertEqual((f["severity"], f["caps"]), ("critical", "do-not-score"))
        # the card holds a notice, not the phrase; the raw hit is still found inside the tool
        self.assertEqual(f["evidence"][0]["excerpt"], "<text withheld: text addressed to the evaluator>")
        root = sample.write(str(Path(tempfile.mkdtemp()) / "sample-project"))
        self.assertTrue(any(phrase in h[3] for h in scan.evaluator_directed_hits(root)))
