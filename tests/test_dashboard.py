"""Suite V: the dashboard. It is the only thing most readers will see, so it is tested for what
it must never do as well as what it shows."""

import copy
import os
import re
import tempfile
import unittest

from quiet_counsel import sample
from helpers import CLEAN_CATALOGUE, MINIMAL, dashboard, fake_key, project, scan, screen


def deep_card():
    """A screened card turned into a deep one, with one scored dimension and its evidence."""
    card = screen(CLEAN_CATALOGUE)
    card["mode"] = "deep"
    card["dimensions"][0].update(score=8, confidence="judged",
                                 evidence=[{"kind": "command", "ref": "skills-ref validate", "excerpt": "0 errors"}])
    return card


class Renders(unittest.TestCase):
    def test_V11_a_capped_dimension_shows_its_effective_score_and_the_cap(self):
        card = deep_card()
        card["dimensions"][0].update(score=10, capped_to=3)
        page = dashboard.build([card], "t")
        self.assertIn('<span class="score">3</span>', page)
        self.assertIn("scored 10, capped to 3", page)
        self.assertNotIn('<span class="score">10</span>', page)

    def test_V01_every_project_appears_and_blocked_ones_come_first(self):
        clean = screen(CLEAN_CATALOGUE, name="clean-one")
        bad = screen({**MINIMAL, "run.sh": f"K={fake_key()}\n"}, name="bad-one")
        page = dashboard.build([clean, bad], "cohort")
        self.assertEqual(page.count('class="project"'), 2)
        self.assertLess(page.index(">bad-one<"), page.index(">clean-one<"))

    def test_V02_a_score_with_no_evidence_raises_a_visible_warning(self):
        card = deep_card()
        card["dimensions"][1].update(score=6, confidence="judged", evidence=[])
        page = dashboard.build([card], "t")
        self.assertIn('<div class="warnbar">', page)
        self.assertIn("SCORED WITHOUT EVIDENCE", page)

    def test_V03_strict_mode_refuses_to_build_that_page(self):
        card = deep_card()
        card["dimensions"][1].update(score=6, confidence="judged", evidence=[])
        with self.assertRaises(dashboard.Unevidenced):
            dashboard.build([card], "t", strict=True)
        dashboard.build([deep_card()], "t", strict=True)  # fully evidenced: builds

    def test_V04_the_page_loads_nothing_from_anywhere(self):
        page = dashboard.build([screen(CLEAN_CATALOGUE)], "t")
        self.assertIsNone(re.search(r'<(script|link|img|iframe)[^>]+(src|href)="https?:', page))
        self.assertNotIn("@import", page)
        self.assertNotIn("<script src", page)

    def test_V05_hostile_text_in_a_submission_is_escaped_not_rendered(self):
        payload = "<script>alert(1)</script>"
        card = screen({**MINIMAL, "README.md": f"# T\n\nShips 9 skills {payload}\n"})
        card["project"]["name"] = payload
        card["flags"].append({"id": "x", "severity": "warning", "title": payload,
                              "evidence": [{"kind": "note", "ref": payload, "excerpt": payload}]})
        page = dashboard.build([card], "t")
        self.assertNotIn(payload, page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_V06_every_status_is_carried_by_a_word_not_only_a_colour(self):
        card = screen({**MINIMAL, "run.sh": f"K={fake_key()}\n", "src/c.py": "get(u, verify=False)\n"})
        page = dashboard.build([card], "t")
        for word in ("critical", "serious", "blocked"):
            self.assertRegex(page, rf'class="pill[^"]*"[^>]*>(\d+ )?{word}<')

    def test_V07_dark_mode_follows_the_system_and_the_explicit_toggle(self):
        page = dashboard.build([screen(MINIMAL)], "t")
        self.assertIn("@media (prefers-color-scheme: dark)", page)
        self.assertIn(':root[data-theme="dark"]', page)
        self.assertIn(':root:not([data-theme="light"])', page)

    def test_V08_a_skipped_dimension_shows_its_reason_never_a_zero(self):
        card = screen({**MINIMAL, "src/App.tsx": "x\n", "src/Page.tsx": "x\n", "src/index.html": "<html></html>\n"})
        page = dashboard.build([card], "t")
        self.assertIn('class="dim na"', page)
        self.assertIn("no instruction catalogue", page)

    def test_V09_what_the_run_did_not_establish_is_always_on_the_page(self):
        page = dashboard.build([screen(MINIMAL)], "t")
        self.assertIn("What this page does not show", page)
        self.assertIn("What this run did not establish", page)

    def test_V10_the_page_claims_evidence_for_every_flag_and_the_sample_card_holds_it(self):
        with tempfile.TemporaryDirectory() as work:
            sample.write(os.path.join(work, "p"))
            card = scan.screen(os.path.join(work, "p"))
        for f in card["flags"]:
            self.assertTrue(f["evidence"] and all(e.get("ref") for e in f["evidence"]), f["id"])
        page = dashboard.build([card], "t")
        self.assertIn("names its evidence (a file and line, or a command or commit)", page)
        self.assertNotIn("names the file and line it came from", page)
