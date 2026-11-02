"""Suite Q: what a project does to the agent host it installs into, and whether the instruction
files every session loads still describe the tree.

Hooks, settings and standing-instruction files change every later session, so writing them
without asking is a safety finding. An instruction file that names paths which no longer exist
is stale guidance loaded on every run, which the research on agent context files calls context
debt (Chatlatanagulchai et al., arXiv 2511.12884)."""

import unittest

from helpers import MINIMAL, flag, flag_ids, screen

SETTINGS = "~/.claude/" + "settings.json"


class HostConfig(unittest.TestCase):
    def test_Q01_an_installer_that_writes_hooks_without_asking_is_serious(self):
        card = screen({**MINIMAL, "install.sh":
                       f"#!/bin/sh\nmkdir -p ~/.claude\ncat > {SETTINGS} <<EOF\n{{\"hooks\": {{}}}}\nEOF\n"})
        f = flag(card, "writes-host-config")
        self.assertEqual(f["severity"], "serious")
        self.assertEqual(f["evidence"][0]["ref"], "install.sh:3")
        self.assertEqual(card["signals"]["host_config_writes"]["value"], 1)

    def test_Q02_the_same_write_behind_a_confirmation_is_a_warning(self):
        card = screen({**MINIMAL, "install.sh":
                       "#!/bin/sh\nread -p 'Add the hooks to your settings? [y/N] ' ok\n"
                       f"[ \"$ok\" = y ] && cat > {SETTINGS} <<EOF\n{{}}\nEOF\n"})
        self.assertEqual(flag(card, "writes-host-config")["severity"], "warning")

    def test_Q03_a_script_appending_to_the_projects_standing_instructions_is_caught(self):
        card = screen({**MINIMAL, "scripts/learn.py":
                       "def learn(rule):\n    with open('AGENTS.md', 'a') as fh:\n        fh.write(rule)\n"})
        self.assertIn("writes-host-config", flag_ids(card))

    def test_Q04_reading_naming_or_documenting_those_files_is_quiet(self):
        card = screen({**MINIMAL,
                       "tools/show.sh": "#!/bin/sh\ncat CLAUDE.md\n",
                       "src/pin.ts": "/**\n * The host puts AGENTS.md in the system prompt `<system-reminder>`\n */\n"
                                     "export const pin = (s: string) => s;\n",
                       "docs/setup.md": f"Add the hook to `{SETTINGS}` yourself:\n\n    echo '{{}}' > {SETTINGS}\n",
                       "tests/test_install.py": f"def test_it():\n    open('{SETTINGS}', 'w')\n"})
        self.assertNotIn("writes-host-config", flag_ids(card))


class StaleInstructions(unittest.TestCase):
    def test_Q05_an_instruction_file_naming_a_missing_path_is_a_warning(self):
        card = screen({**MINIMAL, "scripts/build.sh": "echo build\n", "AGENTS.md":
                       "# Agents\n\nBuild with `scripts/build.sh`, then run `scripts/release.sh`.\n"})
        f = flag(card, "stale-instructions")
        self.assertEqual(f["severity"], "warning")
        self.assertEqual([e["excerpt"] for e in f["evidence"]], ["scripts/release.sh"])
        self.assertEqual(f["evidence"][0]["ref"], "AGENTS.md:3")

    def test_Q06_repository_names_placeholders_urls_and_code_blocks_are_not_paths(self):
        card = screen({**MINIMAL, "src/app.py": "x = 1\n", "skills/x/SKILL.md": "---\nname: x\n---\n",
                       "CLAUDE.md":
                       "Read `src/app.py`. Style from `someone/humanizer`. Install into `<skills-dir>`.\n"
                       "Every skill has a `SKILL.md`.\n"
                       "See `https://example.invalid/docs/`. Tests match `src/*.py`.\n\n"
                       "```sh\npython3 tools/missing.py\n```\n"})
        self.assertNotIn("stale-instructions", flag_ids(card))
        self.assertEqual(card["signals"]["rulebook_missing_paths"]["value"], 0)

    def test_Q07_a_renamed_file_that_kept_its_extension_is_still_caught(self):
        card = screen({**MINIMAL, "CLAUDE.md": "Start in `docs/OVERVIEW.md`, then `RUNBOOK.md`.\n"})
        self.assertEqual([e["excerpt"] for e in flag(card, "stale-instructions")["evidence"]],
                         ["docs/OVERVIEW.md", "RUNBOOK.md"])


class FoundInReview(unittest.TestCase):
    """Cases an independent review of the first version found, each now held."""

    def test_Q08_reading_a_host_file_is_not_writing_it(self):
        card = screen({**MINIMAL, "tools/check.py":
                       "import json, os, sys\nif os.path.getsize('CLAUDE.md') > 4000:\n    pass\n"
                       f"print(json.dumps(json.load(open('{SETTINGS}'))))\n"
                       "sys.stdout.write(open('AGENTS.md').read())\n",
                       "tools/copy.sh": "#!/bin/sh\ncat CLAUDE.md > /tmp/copy.txt\n"})
        self.assertNotIn("writes-host-config", flag_ids(card))

    def test_Q09_a_write_through_a_variable_is_caught_in_node_python_and_shell(self):
        node = ("const path = require('path'), fs = require('fs'), os = require('os');\n"
                "const p = path.join(os.homedir(), '.claude', 'settings.json');\n"
                "const cfg = JSON.parse(fs.readFileSync(p));\ncfg.hooks = {};\n"
                "fs.writeFileSync(p, JSON.stringify(cfg));\n")
        py = ("from pathlib import Path\nSETTINGS = Path.home() / '.claude' / 'settings.json'\n"
              "data = SETTINGS.read_text()\nSETTINGS.write_text(data + '{}')\n")
        sh = f"#!/bin/sh\nTARGET={SETTINGS}\necho start\necho '{{}}' > \"$TARGET\"\n"
        for name, text in (("setup.js", node), ("setup.py", py), ("setup.sh", sh)):
            card = screen({**MINIMAL, name: text})
            self.assertIn("writes-host-config", flag_ids(card), name)

    def test_Q10_an_option_that_skips_the_prompt_is_not_a_gate(self):
        card = screen({**MINIMAL, "install.sh":
                       "#!/bin/sh\n# confirm python is present\napt-get install --yes jq\n"
                       "cp hooks/pre.sh ~/.claude/hooks/pre.sh\necho '{}' > .mcp.json\n"})
        f = flag(card, "writes-host-config")
        self.assertEqual(f["severity"], "serious")
        self.assertEqual(len(f["evidence"]), 2)

    def test_Q11_products_recursive_globs_tilde_fences_ignored_outputs_and_hidden_files_are_quiet(self):
        card = screen({**MINIMAL, ".gitignore": "dist/\n", "src/pkg/mod.py": "x = 1\n",
                       ".claude/settings.local.json": "{}\n", "AGENTS.md":
                       "Built with `Next.js`. Tests are `src/**/*.py`. The build writes `dist/index.js`.\n"
                       "Local overrides go in `settings.local.json`.\n\n~~~\nrun `tools/gone.py`\n~~~\n"})
        self.assertNotIn("stale-instructions", flag_ids(card))

    def test_Q12_a_workflow_named_bare_that_exists_under_dot_github_is_not_missing(self):
        card = screen({**MINIMAL, ".github/workflows/deploy.yml": "name: review\non: push\n",
                       "AGENTS.md": "The `deploy.yml` workflow publishes the site.\n"})
        self.assertNotIn("stale-instructions", flag_ids(card))
        self.assertEqual(card["signals"]["rulebook_missing_paths"]["value"], 0)

    def test_Q13_a_workflow_named_bare_that_exists_nowhere_is_still_a_warning(self):
        card = screen({**MINIMAL, ".github/workflows/gate.yml": "name: gate\non: push\n",
                       "AGENTS.md": "Run `gate.yml`, then `deploy.yml`.\n"})
        self.assertEqual([e["excerpt"] for e in flag(card, "stale-instructions")["evidence"]],
                         ["deploy.yml"])
