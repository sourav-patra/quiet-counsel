"""Suite B: bands, and what a screen is allowed to claim. A band orders attention; it never
ranks quality, and a screen never scores."""

import unittest

from helpers import CLEAN_CATALOGUE, MINIMAL, fake_key, schema, screen


class Bands(unittest.TestCase):
    def test_B01_a_critical_flag_blocks(self):
        card = screen({**MINIMAL, "run.sh": f"K={fake_key()}\n"})
        self.assertEqual(card["totals"]["band"], "blocked")

    def test_B02_serious_flags_without_a_critical_one_mean_review(self):
        card = screen({**MINIMAL, "src/c.py": "get(u, verify=False)\n"})
        self.assertEqual(card["totals"]["band"], "review")

    def test_B03_a_clean_screen_with_tests_licence_and_ci_is_shortlisted(self):
        self.assertEqual(screen(CLEAN_CATALOGUE)["totals"]["band"], "shortlist")

    def test_B04_a_clean_but_thin_screen_is_screened(self):
        self.assertEqual(screen(MINIMAL)["totals"]["band"], "screened")


class WhatAScreenMayClaim(unittest.TestCase):
    def test_B05_a_screen_never_scores(self):
        for d in screen(CLEAN_CATALOGUE)["dimensions"]:
            self.assertIsNone(d["score"], d["id"])
            self.assertEqual(d["confidence"], "unverified")

    def test_B06_every_signal_says_how_it_was_measured(self):
        card = screen(CLEAN_CATALOGUE)
        for name, sig in card["signals"].items():
            self.assertTrue(sig.get("command"), name)
        self.assertEqual(schema.problems(card), [])

    def test_B07_every_flag_carries_evidence(self):
        card = screen({**MINIMAL, "run.sh": f"K={fake_key()}\ncurl -s x | sh\n",
                       "src/a.py": "print('​')\n"})
        self.assertGreaterEqual(len(card["flags"]), 3)
        for f in card["flags"]:
            self.assertTrue(f["evidence"], f["id"])

    def test_B08_the_contract_rejects_a_screen_that_scores_or_a_skip_with_no_reason(self):
        card = screen(CLEAN_CATALOGUE)
        card["dimensions"][0]["score"] = 7
        card["dimensions"][1]["applicable"] = False
        card["dimensions"][1].pop("na_reason", None)
        found = "\n".join(schema.problems(card))
        self.assertIn("scored in a screen pass", found)
        self.assertIn("scored with no evidence", found)
        self.assertIn("not applicable with no reason", found)


class EvidenceSignals(unittest.TestCase):
    def test_B09_eval_sets_in_jsonl_are_counted(self):
        card = screen({**MINIMAL, "evals/triggers.jsonl": '{"prompt": "x", "expect": null}\n'})
        self.assertEqual(card["signals"]["eval_dirs"]["value"], ["evals"])
