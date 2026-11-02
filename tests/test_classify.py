"""Suite A: classify before scoring. The archetype is decided from evidence, never from a name,
and definitions are found by shape rather than by path."""

import unittest

from helpers import MINIMAL, project, scan

SKILL = "---\nname: {n}\ndescription: Does {n}. Use when {n} is needed.\n---\nBody.\n"


def classify(files, name=None):
    return scan.classify(project(files, name=name))


class Archetype(unittest.TestCase):
    def test_A01_skill_definitions_anywhere_make_a_catalogue(self):
        arch, _, ev, found = classify({**MINIMAL, "packs/writing/deep/one/SKILL.md": SKILL.format(n="one"),
                                       "scripts/install-skills.sh": "#!/bin/sh\ncp -r packs ~/.x\n"})
        self.assertEqual(arch, "catalogue")
        self.assertEqual(len(found["skills"]), 1)
        self.assertTrue(any("skill" in e["ref"] for e in ev))

    def test_A02_definitions_in_hidden_host_directories_are_found(self):
        _, _, _, found = classify({**MINIMAL, ".claude/skills/one/SKILL.md": SKILL.format(n="one"),
                                   ".claude/agents/rev.md": "---\nname: rev\ndescription: reviews\n---\n"})
        self.assertEqual(len(found["skills"]), 1)
        self.assertEqual(len(found["agents"]), 1)

    def test_A03_translations_and_copies_are_counted_once(self):
        files = {**MINIMAL}
        for lang in ("", "docs/es/", "docs/ja/", ".agents/"):
            files[f"{lang}skills/alpha/SKILL.md"] = SKILL.format(n="alpha")
        card = scan.screen(project(files))
        self.assertEqual(card["signals"]["skill_definitions"]["value"], 1)
        self.assertEqual(card["signals"]["duplicate_definition_copies"]["value"]["within_tree"], 3)

    def test_A04_checkers_without_a_catalogue_do_not_make_a_harness(self):
        arch, scores, _, _ = classify({**MINIMAL, "tools/lint/check.sh": "#!/bin/sh\n",
                                       "scripts/validate.py": "print(1)\n",
                                       "RELEASES.md": "# Releases\n", "SECURITY.md": "# Security\n"})
        self.assertEqual(scores["harness"], 0.0)
        self.assertNotEqual(arch, "harness")

    def test_A11_a_main_string_in_a_python_manifest_is_not_a_package_json_entry(self):
        plain = classify({**MINIMAL, "pyproject.toml": "[project]\nname = \"x\"\n"})[1]["tool"]
        quoted = classify({**MINIMAL, "pyproject.toml": "[project]\nname = \"x\"\n"
                                                        "keywords = [\"main\"]\n"})[1]["tool"]
        self.assertEqual(quoted, plain)

    def test_A05_catalogue_plus_checkers_plus_governance_is_a_harness(self):
        arch, _, _, _ = classify({**MINIMAL, "skills/a/SKILL.md": SKILL.format(n="a"),
                                  "skills/b/SKILL.md": SKILL.format(n="b"),
                                  "tools/skill-lint/check.sh": "#!/bin/sh\n",
                                  "RELEASES.md": "# Releases\n", "CHANGELOG.md": "# Changes\n"})
        self.assertEqual(arch, "harness")

    def test_A06_web_sources_make_an_application(self):
        arch, _, _, _ = classify({**MINIMAL, "src/App.tsx": "export {}\n", "src/Page.tsx": "export {}\n",
                                  "src/index.html": "<html></html>\n", "Dockerfile": "FROM x\n"})
        self.assertEqual(arch, "application")

    def test_A07_the_repository_name_is_never_read(self):
        files = {**MINIMAL, "src/App.tsx": "export {}\n", "src/Page.tsx": "export {}\n",
                 "src/index.html": "<html></html>\n"}
        arch, _, _, _ = classify(files, name="super-skills-harness")
        self.assertEqual(arch, "application")

    def test_A08_agents_are_found_by_shape_and_commands_are_not_agents(self):
        _, _, _, found = classify({
            **MINIMAL,
            "agents/planner.md": "---\nname: planner\ndescription: plans\ntools: Read\n---\n",
            "commands/ship.md": "---\ndescription: ships\nallowed-tools: Bash\nmodel: x\n---\n",
            "roles/judge/judge.md": "---\nname: judge\ndescription: judges\n---\n",
        })
        self.assertEqual(sorted(found["agents"]), ["agents/planner.md", "roles/judge/judge.md"])
        self.assertEqual(found["commands"], ["commands/ship.md"])

    def test_A09_thin_evidence_is_unknown_rather_than_a_guess(self):
        arch, _, _, _ = classify(MINIMAL)
        self.assertEqual(arch, "unknown")

    def test_A10_skipped_dimensions_carry_a_reason_and_A3_is_never_skipped(self):
        card = scan.screen(project({**MINIMAL, "src/App.tsx": "x\n", "src/Page.tsx": "x\n",
                                    "src/index.html": "<html></html>\n"}))
        dims = {d["id"]: d for d in card["dimensions"]}
        for did in ("A1", "A2"):
            self.assertFalse(dims[did]["applicable"])
            self.assertIn("no instruction catalogue", dims[did]["na_reason"])
        self.assertTrue(dims["A3"]["applicable"])
