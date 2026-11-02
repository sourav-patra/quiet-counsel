"""Suite C: what a project says about itself, against what the repository contains. Four
statuses, kept apart: confirmed, contradicted, unsupported, unchecked."""

import unittest

from helpers import MINIMAL, flag, screen

SKILL = "---\nname: {n}\ndescription: Does {n}. Use when needed.\n---\nBody.\n"


def skills(n):
    return {f"skills/s{i}/SKILL.md": SKILL.format(n=f"s{i}") for i in range(n)}


def claim(card, kind):
    return next(c for c in card["claims"] if c["kind"] == kind)


class Claims(unittest.TestCase):
    def test_C01_an_inflated_count_is_contradicted_and_caps_claim_accuracy(self):
        card = screen({**MINIMAL, "README.md": "# T\n\nShips 12 skills.\n", **skills(1)})
        self.assertEqual(claim(card, "skills")["status"], "contradicted")
        self.assertEqual(flag(card, "contradicted-claim")["caps"], "B2<=2")

    def test_C02_finding_more_than_claimed_is_never_a_contradiction(self):
        card = screen({**MINIMAL, "README.md": "# T\n\nIncludes 2 skills.\n", **skills(5)})
        self.assertNotEqual(claim(card, "skills")["status"], "contradicted")
        self.assertIsNone(flag(card, "contradicted-claim"))

    def test_C03_a_test_count_is_unchecked_because_cases_are_not_files(self):
        card = screen({**MINIMAL, "README.md": "# T\n\nCovered by 340 tests.\n",
                       "tests/test_a.py": "def test_a():\n    pass\n"})
        c = claim(card, "tests")
        self.assertEqual(c["status"], "unchecked")
        self.assertIn("cases not counted", c["measured"])

    def test_C04_works_with_n_agents_is_a_compatibility_claim(self):
        card = screen({**MINIMAL, "README.md": "# T\n\nWorks with 15 agents out of the box.\n"})
        c = claim(card, "agents")
        self.assertEqual(c["kind_of_claim"], "compatibility")
        self.assertNotEqual(c["status"], "contradicted")

    def test_C05_a_compliance_claim_with_nothing_behind_it_is_unsupported(self):
        card = screen({**MINIMAL, "README.md": "# T\n\nSOC 2 compliant and production-ready.\n"})
        self.assertEqual(claim(card, "soc2")["status"], "unsupported")
        self.assertEqual(claim(card, "production-ready")["status"], "unsupported")

    def test_C06_a_count_within_fifteen_percent_is_confirmed(self):
        card = screen({**MINIMAL, "README.md": "# T\n\nShips 20 skills.\n", **skills(19)})
        self.assertEqual(claim(card, "skills")["status"], "confirmed")
