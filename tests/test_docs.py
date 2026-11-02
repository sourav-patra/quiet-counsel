"""Suite D: the documentation says only what is true of the code, and reads as prose a person
wrote. Written-down conventions drift; checked ones do not."""

import importlib.util
import re
import unittest
from pathlib import Path

from helpers import REPO, schema
from quiet_counsel import cli

HUMAN_FACING = [REPO / "README.md", REPO / "AGENTS.md", REPO / "CLAUDE.md", REPO / "CHANGELOG.md",
                REPO / "CONTRIBUTING.md", REPO / "SECURITY.md", REPO / "RELEASING.md",
                *sorted((REPO / "docs").glob("*.md")), *sorted((REPO / "skills").rglob("*.md")),
                *sorted((REPO / "agents").glob("*.md"))]
SPEC_KEYS = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}


def prose(text):
    """Text with fenced code blocks and inline code removed."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


class Docs(unittest.TestCase):
    def test_D01_docs_name_only_subcommands_that_exist(self):
        # Only text that is shaped like a command counts: inline code and fenced blocks. Prose
        # such as "the package installed" names the project, not a subcommand.
        prog = cli.build_parser().prog
        subs = {"classify", "screen", "integrity", "dashboard", "check", "verdict", "sample"}
        for f in HUMAN_FACING:
            text = f.read_text(encoding="utf-8")
            code = re.findall(r"```.*?```", text, flags=re.S) + re.findall(r"`[^`\n]+`", text)
            for block in code:
                for m in re.finditer(rf"(?<![\w/-]){re.escape(prog)} ([a-z]+)\b", block):
                    self.assertIn(m.group(1), subs, f"{f.name} names `{prog} {m.group(1)}`")

    def test_D02_the_command_reference_is_current(self):
        spec = importlib.util.spec_from_file_location("g", REPO / "tools" / "gen_cli_docs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual((REPO / "docs" / "cli.md").read_text(encoding="utf-8"), mod.render(),
                         "docs/cli.md is stale: run python3 tools/gen_cli_docs.py")

    def test_D03_the_rubric_and_the_code_name_the_same_sixteen_dimensions(self):
        text = (REPO / "docs" / "RUBRIC.md").read_text(encoding="utf-8")
        in_doc = set(re.findall(r"(?m)^### ([A-E][1-4]),", text))
        self.assertEqual(in_doc, set(schema.DIMENSIONS))

    def test_D04_human_facing_prose_carries_no_em_or_en_dashes(self):
        hits = []
        for f in HUMAN_FACING:
            for n, line in enumerate(prose(f.read_text(encoding="utf-8")).splitlines(), 1):
                if "—" in line or "–" in line:
                    hits.append(f"{f.relative_to(REPO)}:{n}: {line.strip()[:70]}")
        self.assertEqual(hits, [], "dashes in prose:\n" + "\n".join(hits))

    def test_D05_the_shipped_skill_uses_only_specification_keys_and_its_own_name(self):
        for skill_md in (REPO / "skills").glob("*/SKILL.md"):
            head = skill_md.read_text(encoding="utf-8").split("---")[1]
            keys = set(re.findall(r"^([a-z][a-z-]*):", head, re.M))
            self.assertLessEqual(keys, SPEC_KEYS, f"non-spec keys: {keys - SPEC_KEYS}")
            name = re.search(r"^name:\s*(\S+)", head, re.M).group(1)
            self.assertEqual(name, skill_md.parent.name)
