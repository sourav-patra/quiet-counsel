"""Suite K: the command line, driven as a user would drive it."""

import json
import os
import tempfile
import unittest

from helpers import CLEAN_CATALOGUE, MINIMAL, project, run_cli
from quiet_counsel import __version__


class CommandLine(unittest.TestCase):
    def test_K01_version_prints_the_name_and_version(self):
        r = run_cli("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn(__version__, r.stdout)

    def test_K02_classify_json_names_the_archetype_and_its_evidence(self):
        r = run_cli("classify", project(CLEAN_CATALOGUE), "--json")
        out = json.loads(r.stdout)
        self.assertEqual(out["archetype"], "catalogue")
        self.assertTrue(out["evidence"])

    def test_K03_screen_writes_one_card_per_project_and_a_line_each(self):
        a, b = project(CLEAN_CATALOGUE, name="one"), project(MINIMAL, name="two")
        out = tempfile.mkdtemp()
        r = run_cli("screen", a, b, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(os.listdir(out)), ["one.json", "two.json"])
        self.assertIn("one", r.stdout)
        self.assertIn("two", r.stdout)

    def test_K04_a_path_that_is_not_a_directory_is_skipped_and_all_bad_is_exit_2(self):
        good = project(MINIMAL)
        r = run_cli("screen", good, "/no/such/dir")
        self.assertEqual(r.returncode, 0)
        self.assertIn("skipped, not a directory", r.stderr)
        self.assertEqual(run_cli("screen", "/no/such/dir").returncode, 2)

    def test_K05_integrity_prints_history_licence_and_claims(self):
        out = json.loads(run_cli("integrity", project(MINIMAL)).stdout)
        for key in ("history", "licence", "claims", "hidden_characters", "evaluator_directed"):
            self.assertIn(key, out)

    def test_K06_check_exits_1_on_a_broken_card_and_0_on_a_good_one(self):
        out = tempfile.mkdtemp()
        run_cli("screen", project(MINIMAL, name="p"), "--out", out)
        good = os.path.join(out, "p.json")
        self.assertEqual(run_cli("check", good).returncode, 0)
        with open(good, encoding="utf-8") as fh:
            card = json.load(fh)
        card["flags"].append({"id": "x", "severity": "loud", "title": "x", "evidence": []})
        bad = os.path.join(out, "bad.json")
        with open(bad, "w", encoding="utf-8") as fh:
            json.dump(card, fh)
        r = run_cli("check", bad)
        self.assertEqual(r.returncode, 1)
        self.assertIn("carries no evidence", r.stdout)
