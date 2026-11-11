"""Suite P: third-party text. A project that copies someone else's text should carry that text's
licence and a line saying where it came from. Copied share-alike text, text under terms that do
not allow reuse, and text from a source with no licence are findings; a permissive copy with its
credit in place is not.

The declarations are assembled at run time, like the credential shapes elsewhere, so this file
declares nothing about itself when the tool screens its own tree."""

import importlib.util
import json
import os
import tempfile
import unittest

from helpers import CLEAN_CATALOGUE, MINIMAL, REPO, flag, flag_ids, project, scan
from test_agentic import fill, script, worksheet

SOURCE = "sour" + "ce: "
SPDX = "SPDX-License-" + "Identifier: "
FOUR = {"share-alike-text", "restricted-licence-text", "copied-without-attribution",
        "licence-needs-reading"}
BODY = "def helper(value):\n" + "".join(f"    step_{i} = value + {i}\n" for i in range(30)) + \
       "    return value\n"
MIT = "MIT License\n\nCopyright (c) 2026 Upstream Authors\n"
APACHE = "Apache License\nVersion 2.0, January 2004\n"
CC_BY_SA = "Creative Commons Attribution-ShareAlike 4.0 International\n"


def skill(licence=None, extra=""):
    lic = f"license: {licence}\n" if licence else ""
    return f"---\nname: borrowed\ndescription: Borrowed. Use when borrowing.\n{lic}---\n{extra}Body.\n"


def screen(files, corpus=None):
    return scan.screen(project(files), corpus)


class Declared(unittest.TestCase):
    def test_P01_a_skill_declaring_a_share_alike_licence_in_an_mit_tree_is_critical(self):
        card = screen({**MINIMAL, "skills/borrowed/SKILL.md": skill("CC-BY-SA-4.0")})
        f = flag(card, "share-alike-text")
        self.assertEqual(f["severity"], "critical")
        self.assertEqual(f["caps"], "D1=0")
        self.assertEqual(f["evidence"][0]["ref"], "skills/borrowed/SKILL.md:4")

    def test_P02_terms_a_person_should_read_are_a_warning_and_a_bare_source_line_is_one(self):
        card = screen({**MINIMAL, "docs/rules.md":
                       f"{SOURCE}https://github.com/example/rules @ abc123, licence: CC-BY-4.0\n\nText.\n",
                       "docs/other.md": f"{SOURCE}https://github.com/example/other\n\nText.\n"})
        f = flag(card, "licence-needs-reading")
        self.assertEqual(f["severity"], "warning")
        refs = {e["ref"]: e["excerpt"] for e in f["evidence"]}
        self.assertIn("[CC-BY-4.0]", refs["docs/rules.md:1"])
        self.assertIn("no licence stated", refs["docs/other.md:1"])
        self.assertNotIn("share-alike-text", flag_ids(card))

    def test_P03_restricted_or_proprietary_terms_are_serious_and_cap_licence_compliance(self):
        card = screen({**MINIMAL, "skills/borrowed/SKILL.md": skill("PolyForm Noncommercial 1.0.0"),
                       "src/lib.js": f"// {SPDX}BUSL-1.1\nexport const x = 1;\n"})
        f = flag(card, "restricted-licence-text")
        self.assertEqual(f["severity"], "serious")
        self.assertEqual(f["caps"], "D1<=3")
        self.assertEqual({e["ref"] for e in f["evidence"]}, {"skills/borrowed/SKILL.md:4", "src/lib.js:1"})

    def test_P04_a_permissive_skill_carrying_its_licence_and_source_is_quiet(self):
        card = screen({"README.md": "# Tool\n", "LICENSE": APACHE, "skills/borrowed/SKILL.md":
                       skill("MIT", f"{SOURCE}https://github.com/example/skills @ 1a2b3c, licence: MIT\n")})
        self.assertFalse(FOUR & flag_ids(card))
        self.assertEqual(card["signals"]["third_party_declarations"]["value"], 2)

    def test_P05_a_template_with_placeholders_in_a_guide_declares_nothing(self):
        card = screen({**MINIMAL, "docs/copying.md":
                       f"Put this at the top:\n\n{SOURCE}<repo url> @ <commit>, licence: <name>\n",
                       "docs/front.md": "---\ntitle: guide\nlicense: <name>\n---\nText.\n"})
        self.assertEqual(card["signals"]["third_party_declarations"]["value"], 0)
        self.assertFalse(FOUR & flag_ids(card))

    def test_P06_a_file_under_the_projects_own_share_alike_licence_is_not_a_finding(self):
        card = screen({"README.md": "# Tool\n", "LICENSE": "GNU GENERAL PUBLIC LICENSE\nVersion 3\n",
                       "skills/borrowed/SKILL.md": skill("GPL-3.0-or-later")})
        self.assertNotIn("share-alike-text", flag_ids(card))


class Copied(unittest.TestCase):
    def corpus(self, licence_text=None, name="upstream"):
        files = {f"{name}/lib/helper.py": BODY}
        if licence_text:
            files[f"{name}/LICENSE"] = licence_text
        return project(files)

    def test_P07_a_permissive_file_copied_with_no_credit_is_serious_and_caps_provenance(self):
        card = screen({**MINIMAL, "src/helper.py": BODY}, self.corpus(MIT))
        f = flag(card, "copied-without-attribution")
        self.assertEqual(f["severity"], "serious")
        self.assertEqual(f["caps"], "D2<=3")
        self.assertIn("source licence MIT", f["evidence"][0]["excerpt"])
        self.assertEqual(card["signals"]["copies_credited"]["value"], "0 of 1")

    def test_P08_a_copy_that_gained_a_source_line_still_matches_and_is_credited(self):
        credited = f"# {SOURCE}https://github.com/example/upstream @ 9f8e7d, licence: MIT\n" + BODY
        card = screen({**MINIMAL, "src/helper.py": credited}, self.corpus(MIT))
        self.assertFalse(FOUR & flag_ids(card))
        self.assertEqual(card["signals"]["copies_credited"]["value"], "1 of 1")
        self.assertIn("corpus-duplication", flag_ids(card))

    def test_P09_a_licence_beside_the_copy_or_a_notice_naming_the_source_is_credit(self):
        beside = screen({**MINIMAL, "vendor/upstream/helper.py": BODY, "vendor/upstream/LICENSE": MIT},
                        self.corpus(MIT))
        notice = screen({**MINIMAL, "src/helper.py": BODY,
                         "THIRD_PARTY_NOTICES.md": "src/helper.py comes from upstream, MIT.\n"},
                        self.corpus(MIT))
        self.assertNotIn("copied-without-attribution", flag_ids(beside))
        self.assertNotIn("copied-without-attribution", flag_ids(notice))

    def test_P10_a_copy_from_a_source_with_no_licence_is_restricted(self):
        card = screen({**MINIMAL, "src/helper.py": BODY}, self.corpus(None))
        f = flag(card, "restricted-licence-text")
        self.assertIn("no licence file in the source project", f["evidence"][0]["excerpt"])

    def test_P11_a_copy_from_a_share_alike_source_is_critical(self):
        card = screen({**MINIMAL, "src/helper.py": BODY}, self.corpus(CC_BY_SA))
        f = flag(card, "share-alike-text")
        self.assertEqual(f["severity"], "critical")
        self.assertIn("CC-BY-SA-4.0", f["evidence"][0]["excerpt"])


class Classes(unittest.TestCase):
    def test_P12_licence_names_sort_into_the_classes_the_check_acts_on(self):
        expected = {
            "MIT": "permissive", "Apache-2.0": "permissive", "BSD-3-Clause": "permissive",
            "ISC": "permissive", "CC0-1.0": "permissive", "BSL-1.0": "permissive",
            "GPL-3.0-only": "share-alike", "AGPL-3.0": "share-alike", "CC-BY-SA-4.0": "share-alike",
            "LGPL-2.1": "weak-copyleft", "MPL-2.0": "weak-copyleft",
            "CC-BY-4.0": "not-osi",
            "CC-BY-NC-SA-4.0": "restricted", "BUSL-1.1": "restricted", "UNLICENSED": "restricted",
            "PolyForm Noncommercial 1.0.0": "restricted", "Proprietary": "restricted",
            "": "none", None: "none", "Made-Up-1.0": "unknown",
        }
        self.assertEqual({k: scan.licence_class(k) for k in expected}, expected)


class Caps(unittest.TestCase):
    def test_P13_finalize_applies_the_licence_and_provenance_caps(self):
        _, ws = worksheet({**CLEAN_CATALOGUE, "skills/borrowed/SKILL.md": skill("BUSL-1.1")})
        fill(ws, score=9)
        out = os.path.join(tempfile.mkdtemp(), "v.html")
        r = script("review-project", "review_project.py", "finalize", ws, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(ws, encoding="utf-8") as fh:
            card = json.load(fh)
        d1 = next(d for d in card["dimensions"] if d["id"] == "D1")
        self.assertEqual(d1["capped_to"], 3.0)
        self.assertIn("D1<=3", card["totals"]["caps_applied"])
        spec = importlib.util.spec_from_file_location(
            "review_project", REPO / "skills" / "review-project" / "scripts" / "review_project.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod._ceiling("D2<=3", "D2"), 3.0)
        self.assertIsNone(mod._ceiling("D2<=3", "D1"))
        self.assertEqual(mod._ceiling("safety<=3", "C2"), 3.0)


class Quiet(unittest.TestCase):
    """Found by screening real catalogues: both used to raise a flag on clean repositories."""

    def test_P14_a_closed_project_marking_its_own_skills_proprietary_is_quiet(self):
        card = screen({"README.md": "# Internal\n", "skills/own/SKILL.md": skill("Proprietary")})
        self.assertFalse(FOUR & flag_ids(card))
        card = screen({**MINIMAL, "skills/own/SKILL.md": skill("Proprietary")})
        self.assertIn("restricted-licence-text", flag_ids(card))

    def test_P15_a_source_field_in_data_or_deep_in_a_document_is_not_a_declaration(self):
        deep = "# Design notes\n\n" + "Some text.\n" * 20 + f"{SOURCE}https://example.com/board\n"
        card = screen({**MINIMAL, "registry.yaml": f"servers:\n  - name: x\n    {SOURCE}https://example.com/x\n",
                       "docs/notes.md": deep})
        self.assertEqual(card["signals"]["third_party_declarations"]["value"], 0)
        self.assertFalse(FOUR & flag_ids(card))

    def test_P16_share_alike_text_in_a_fixture_named_file_is_critical_unless_the_project_excludes_it(self):
        files = {**MINIMAL, "skills/x/evals/files/a/SKILL.fixture.md":
                 f"{SOURCE}https://github.com/example/borrowed @ abc123, licence: CC-BY-SA-4.0\n\nBody.\n"}
        card = screen(files)
        f = flag(card, "share-alike-text")
        self.assertEqual(f["severity"], "critical")
        self.assertEqual(card["totals"]["band"], "blocked")
        card = scan.screen(project({**files, ".scanignore": "skills/*/evals/files/*\n"}), honour_ignore=True)
        f = flag(card, "share-alike-text")
        self.assertEqual(f["severity"], "info")
        self.assertTrue(f["excluded"])
        self.assertEqual(f["original_severity"], "critical")
        self.assertNotEqual(card["totals"]["band"], "blocked")
