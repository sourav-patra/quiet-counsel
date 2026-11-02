"""Traceability between docs/test-suite.md and the tests.

Every case the page marks PASS must be claimed by a test method named for it
(test_S04_...); a docstring mention does not count. Every such method must name a case the page
lists, so a test cannot quietly outlive the case it was written for. FIELD cases that need a real
cohort stay visible here as a skip rather than disappearing."""

import re
import unittest
from pathlib import Path

HERE = Path(__file__).parent
PAGE = HERE.parent / "docs" / "test-suite.md"
ROW = re.compile(r"^\| ([A-Z])-(\d{2}) \|.*\| (PASS|FIELD|ACCEPTED) \|\s*$", re.M)
FIELD = "FIELD: needs {what}; record the evidence in docs/test-suite.md when it runs."


def cases():
    return {f"{m.group(1)}{m.group(2)}": m.group(3) for m in ROW.finditer(PAGE.read_text(encoding="utf-8"))}


def claims():
    return "\n".join(p.read_text(encoding="utf-8") for p in HERE.glob("test_*.py")
                     if p.name != Path(__file__).name)


class Traceability(unittest.TestCase):
    def test_the_page_lists_cases(self):
        self.assertGreater(len(cases()), 70)

    def test_every_pass_case_has_a_test_named_for_it(self):
        text = claims()
        missing = [c for c, s in cases().items() if s == "PASS" and not re.search(rf"def test_{c}_", text)]
        self.assertEqual(missing, [], f"cases marked PASS with no test claiming them: {missing}")

    def test_every_case_test_names_a_listed_case(self):
        listed = set(cases())
        named = set(re.findall(r"def test_([A-Z]\d{2})_", claims()))
        self.assertEqual(sorted(named - listed), [], "tests claiming cases the page does not list")

    def test_no_skip_hides_outside_this_file(self):
        for p in HERE.glob("test_*.py"):
            if p.name != Path(__file__).name:
                self.assertNotIn("unittest.skip", p.read_text(encoding="utf-8"), p.name)


class Field(unittest.TestCase):
    """Cases that cannot be proved in CI. They stay visible rather than silently dropped."""

    @unittest.skip(FIELD.format(what="a real cohort of at least 50 submissions"))
    def test_F01_a_real_cohort_is_screened_and_every_flag_reviewed(self):
        # Given a real cohort; When it is screened and every flag is read by a person;
        # Then the false-positive rate per detector is recorded with the field run.
        ...
