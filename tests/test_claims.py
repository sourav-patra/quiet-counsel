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


APACHE = "Apache License\nVersion 2.0, January 2004\n"
ARGS = "import argparse\np = argparse.ArgumentParser()\np.add_argument('--out')\n"


def mismatches(files):
    """(card, flag) for a repository named csvtool with a LICENSE of MIT unless the files say otherwise."""
    card = screen({**MINIMAL, **files}, name="csvtool")
    return card, flag(card, "readme-claim-mismatch")


def kinds_of(f):
    return {e["ref"].split(":")[0] for e in f["evidence"]}


class ReadmeClaimMismatch(unittest.TestCase):
    def test_C07_a_licence_claim_against_a_different_known_licence_is_flagged(self):
        card, f = mismatches({"README.md": "# T\n\nLicensed under Apache-2.0.\n"})
        self.assertEqual(f["severity"], "info")
        self.assertNotIn("caps", f)
        self.assertEqual(kinds_of(f), {"README.md", "LICENSE"})
        self.assertEqual(card["totals"]["caps_applied"], [])

    def test_C08_licence_near_misses_give_no_flag(self):
        for readme, extra in [
            ("Licensed under MIT.\n", {}),
            ("Licensed under MIT or Apache-2.0.\n", {}),
            ("Dual licensed: Apache-2.0 and MIT.\n", {}),
            ("Licensed under the Apache License.\n", {"LICENSE": "All rights reserved here.\n"}),
            ("```\nLicensed under Apache-2.0.\n```\n", {}),
            ("<!-- Licensed under Apache-2.0. -->\n", {}),
        ]:
            with self.subTest(readme=readme):
                _, f = mismatches({"README.md": "# T\n\n" + readme, **extra})
                self.assertIsNone(f)

    def test_C09_a_licence_badge_is_a_licence_claim(self):
        _, f = mismatches({"README.md": "# T\n\n![l](https://img.shields.io/badge/license-GPL--3.0-blue)\n"})
        self.assertIsNotNone(f)

    def test_C10_zero_dependencies_against_a_listed_package_is_flagged(self):
        for files in [{"requirements.txt": "# pins\nrequests==2.32\n"},
                      {"pyproject.toml": "[project]\nname='x'\ndependencies = ['requests']\n"},
                      {"package.json": '{"dependencies": {"left-pad": "1.0.0"}}'}]:
            with self.subTest(files=list(files)):
                _, f = mismatches({"README.md": "# T\n\nStandard library only.\n", **files})
                self.assertIn(list(files)[0], kinds_of(f))

    def test_C11_dependency_near_misses_give_no_flag(self):
        for readme, files in [
            ("Zero dependencies.\n", {"requirements.txt": "# none\n\n-r other.txt\n"}),
            ("Zero dependencies.\n", {"package.json": '{"devDependencies": {"jest": "1"}}'}),
            ("Zero dependencies.\n", {"pyproject.toml":
                "[project]\nname='x'\ndependencies = []\n[project.optional-dependencies]\ndev=['pytest']\n"}),
            ("No dependencies besides requests.\n", {"requirements.txt": "requests\n"}),
            ("Dependency-free at runtime.\n", {"requirements-dev.txt": "pytest\n"}),
            ("```\nzero dependencies\n```\n", {"requirements.txt": "requests\n"}),
        ]:
            with self.subTest(readme=readme, files=list(files)):
                _, f = mismatches({"README.md": "# T\n\n" + readme, **files})
                self.assertIsNone(f)

    def test_C12_a_flag_no_source_file_holds_is_flagged(self):
        _, f = mismatches({"README.md": "# T\n\n- `csvtool --json` prints JSON.\n", "t.py": ARGS})
        self.assertIn("README.md", kinds_of(f))
        self.assertIn("--json", f["evidence"][0]["excerpt"])

    def test_C13_flag_near_misses_give_no_flag(self):
        for readme, files in [
            ("`csvtool --out` writes the file.\n", {"t.py": ARGS}),
            ("`csvtool --json` prints JSON.\n", {"notes.md": "--json\n"}),                 # no parser anywhere
            ("`csvtool --json` prints JSON.\n", {"t.py": "print('hi')\n"}),                # no parser
            ("Run `pip install --upgrade t`.\n", {"t.py": ARGS}),
            ("Run `git log --json`.\n", {"t.py": ARGS}),
            ("`csvtool --help` shows usage.\n", {"t.py": ARGS}),
            ("`csvtool --json` prints JSON.\n", {"t.py": ARGS + "p.add_argument('--json')\n"}),
            ("`csvtool --json` prints JSON.\n", {"main.go": 'cmd.Flags().Bool("json", false, "")\n// cobra\n'}),
            ("`csvtool --json` prints JSON.\n", {"app.py": "import typer\ndef main(json: bool = False): ...\n"}),
            ("```\ncsvtool `--json`\n```\n", {"t.py": ARGS}),
        ]:
            with self.subTest(readme=readme, files=list(files)):
                _, f = mismatches({"README.md": "# T\n\n" + readme, **files})
                self.assertIsNone(f)

    def test_C14_a_path_the_readme_says_it_ships_but_is_missing_is_flagged(self):
        _, f = mismatches({"README.md": "# T\n\nIncludes a test suite in `tests/`.\n"})
        self.assertEqual(kinds_of(f), {"README.md", "test -e tests/"})

    def test_C15_path_near_misses_give_no_flag(self):
        for readme, extra in [
            ("Includes a suite in `tests/`.\n", {"tests/test_a.py": "x = 1\n"}),
            ("Writes results to `out/run.json`.\n", {}),                        # not an includes sentence
            ("Includes `./local/x`, `<dir>/x`, `~/x/y` and `out/a`.\n", {}),
            ("Ships cards in `cards/one.json`.\n", {}),
            ("Ships the demo in `demo/run`.\n", {".gitignore": "demo/\n"}),
            ("```\nIncludes `tests/`.\n```\n", {}),
        ]:
            with self.subTest(readme=readme):
                _, f = mismatches({"README.md": "# T\n\n" + readme, **extra})
                self.assertIsNone(f)

    def test_C16_four_of_six_planted_claims_in_a_small_tool_are_found(self):
        card, f = mismatches({
            "README.md": ("# csvtool\n\n- Standard library only, with no dependencies.\n"
                          "- Makes no network calls.\n- Retries a failed read three times.\n"
                          "- `csvtool --out PATH` writes the CSV to PATH.\n- `csvtool --json` prints JSON instead of CSV.\n"
                          "- Includes a test suite in `tests/`.\n- Licensed under MIT.\n"),
            "LICENSE": APACHE, "requirements.txt": "requests==2.32.0\n", "csvtool.py": ARGS})
        self.assertEqual(sorted(e["ref"].split(":")[0] for e in f["evidence"] if e["ref"].startswith("README")),
                         ["README.md"] * 4)
        self.assertEqual({"LICENSE", "requirements.txt", "test -e tests/"} <= kinds_of(f), True)
        self.assertEqual(f["detail"].count(";"), 3)


def evidence_state(files):
    card = screen({**MINIMAL, **files})
    return card, card["signals"]["eval_evidence"]["value"]


class EvalEvidence(unittest.TestCase):
    def test_C17_a_repository_with_no_eval_files_has_state_none(self):
        _, v = evidence_state({})
        self.assertEqual(v, {"state": "none", "paths": []})

    def test_C18_setup_files_give_state_setup_with_their_paths(self):
        for rel, text in [("skills/a/evals/evals.json", "{}"), ("promptfooconfig.yaml", "x: 1\n"),
                          ("evals/registry/evals/coqa.yaml", "x: 1\n"),
                          ("lm_eval/tasks/t/t.yaml", "x: 1\n"),
                          ("t/test_a.py", "import pytest\n@pytest.mark.langsmith\ndef test_a(): ...\n"),
                          ("e.py", "from inspect_ai import task\n@task\ndef t(): ...\n")]:
            with self.subTest(rel=rel):
                _, v = evidence_state({rel: text})
                self.assertEqual(v, {"state": "setup", "paths": [rel]})

    def test_C19_result_files_give_state_result_even_beside_setup(self):
        for rel in ["skill-workspace/iteration-1/benchmark.json", "w/iteration-1/x/grading.json",
                    "logs/2026-01-01_task_ab.eval", ".deepeval/.latest_test_run.json",
                    "test_run_20260101_000000.json", "evals/out/results.json"]:
            with self.subTest(rel=rel):
                _, v = evidence_state({rel: "{}", "promptfooconfig.yaml": "x: 1\n"})
                self.assertEqual(v, {"state": "result", "paths": [rel]})

    def test_C20_a_score_with_no_result_file_is_an_information_flag_that_never_says_false(self):
        card, v = evidence_state({"README.md": "# T\n\nScores 74% on the SWE-bench verified benchmark.\n"})
        f = flag(card, "score-without-result")
        self.assertEqual(f["severity"], "info")
        self.assertNotIn("caps", f)
        text = f["title"] + f["detail"]
        self.assertIn("no result file", text)
        self.assertIn("elsewhere", text)
        self.assertNotRegex(text, r"(?i)\bfalse\b|\bwrong\b|\blie")
        self.assertEqual(f["evidence"][0]["ref"], "README.md:3")

    def test_C21_with_setup_present_the_flag_says_so(self):
        card, _ = evidence_state({"README.md": "# T\n\n#6 ranking on the Agent Leaderboard, score 0.43.\n",
                                  "promptfooconfig.yaml": "x: 1\n"})
        f = flag(card, "score-without-result")
        self.assertIn("setup", f["detail"])
        self.assertIn("promptfooconfig.yaml", f["detail"])

    def test_C22_a_result_file_means_no_flag(self):
        card, _ = evidence_state({"README.md": "# T\n\nScores 74% on SWE-bench.\n",
                                  "w/iteration-1/benchmark.json": "{}"})
        self.assertIsNone(flag(card, "score-without-result"))

    def test_C23_the_listed_wordings_each_raise_the_flag(self):
        for line in ["Scores >74% on the SWE-bench verified benchmark.",
                     "mini-agent beats Claude Code on DeepSWE.",
                     "Achieved #6 ranking on the Deep Research Bench Leaderboard with 0.4344.",
                     "It uses 30% fewer steps.",
                     "State of the art on SWE-bench among open-source projects.",
                     "SoTA on HumanEval."]:
            with self.subTest(line=line):
                card, _ = evidence_state({"README.md": f"# T\n\n{line}\n"})
                self.assertIsNotNone(flag(card, "score-without-result"))

    def test_C24_loose_wordings_quotes_and_code_raise_nothing(self):
        for text in ["A state-of-the-art multi-agent team.\n",
                     "Reaches higher performance on difficult benchmarks.\n",
                     "Open model beats closed-source models.\n",
                     "Top 20 on OpenRouter.\n",
                     "Coverage is 85%.\n",
                     '> "Scores 90% on SWE-bench" says a user.\n',
                     'Users say "it scored 90% on the SWE-bench verified benchmark for us".\n',
                     "```\nScores 74% on SWE-bench.\n```\n",
                     "Run `scores 74% on SWE-bench`.\n",
                     "<!-- 74% on SWE-bench -->\n"]:
            with self.subTest(text=text):
                card, _ = evidence_state({"README.md": "# T\n\n" + text})
                self.assertIsNone(flag(card, "score-without-result"))

    def test_C25_screening_this_repository_raises_neither_new_flag(self):
        from helpers import REPO, scan
        card = scan.screen(str(REPO))
        self.assertIsNone(flag(card, "readme-claim-mismatch"))
        self.assertIsNone(flag(card, "score-without-result"))


class ClaimPrecision(unittest.TestCase):
    """Rule changes from the field adjudication of the first 50 repositories."""

    def test_C26_a_flag_held_in_a_command_file_a_skill_or_a_shebang_script_is_present(self):
        readme = "# T\n\n`csvtool --json` prints JSON.\n"
        for rel, text in [("commands/run.md", "Options: --json\n"), (".claude/commands/run.md", "--json\n"),
                          ("skills/a/SKILL.md", "Use --json\n"),
                          ("scripts/sync", "#!/bin/sh\n[ \"$1\" = --json ]\n")]:
            with self.subTest(rel=rel):
                _, f = mismatches({"README.md": readme, "t.py": ARGS, rel: text})
                self.assertIsNone(f)
        _, f = mismatches({"README.md": readme, "t.py": ARGS, "scripts/sync": "no shebang --json\n"})
        self.assertIsNotNone(f)

    def test_C27_only_a_flag_of_this_projects_own_command_counts(self):
        for readme in ["`--json` prints JSON.\n", "- [lean](https://x.example/l): `csvtool --json` here.\n",
                       "`lean-ctx init --json` sets up.\n", "`bun build --json x`.\n",
                       "Use `--json` with csvtool.\n"]:
            with self.subTest(readme=readme):
                _, f = mismatches({"README.md": "# T\n\n" + readme, "t.py": ARGS})
                self.assertIsNone(f)

    def test_C28_the_projects_own_names_come_from_its_manifests_or_its_folder(self):
        for files in [{"pyproject.toml": "[project]\nname='x'\n[project.scripts]\nct = 'x:main'\n"},
                      {"package.json": '{"bin": {"ct": "x.js"}}'}, {"package.json": '{"bin": "ct"}'}]:
            with self.subTest(files=list(files)):
                _, f = mismatches({"README.md": "# T\n\n`ct --json` prints JSON.\n", "t.py": ARGS, **files})
                self.assertIn("README.md", kinds_of(f))

    def test_C29_negated_reader_project_and_slug_shaped_paths_are_not_claims(self):
        for line in ["This repo does not ship a `.cursor/` folder; `.cursor/skills/` is yours.",
                     "Copy it into your project as `agent-skills/skills/`.",
                     "Put the file in `.github/copilot-instructions.md`.",
                     "Includes a plugin from `DietrichGebert/ponytail`.",
                     "Includes a model, `Xenova/all-MiniLM-L6-v2`, downloaded at first use."]:
            with self.subTest(line=line):
                _, f = mismatches({"README.md": "# T\n\n" + line + "\n"})
                self.assertIsNone(f)
        _, f = mismatches({"README.md": "# T\n\nIncludes guides in `docs/guide.md`.\n", "docs/other.md": "x\n"})
        self.assertIsNotNone(f)

    def test_C30_a_figure_found_in_a_result_file_elsewhere_in_the_tree_means_no_flag(self):
        readme = "# T\n\nLoCoMo retrieval 71.9% hit@1 on the SWE-bench style benchmark.\n"
        for rel, text in [("docs/benchmarks/locomo.json", '{"hit@1": 71.8970736629667}'),
                          ("results/r.csv", "metric,value\nhit,0.719\n"), ("benchmarks/n.md", "hit@1 = 71.9\n")]:
            with self.subTest(rel=rel):
                card, _ = evidence_state({"README.md": readme, rel: text})
                self.assertIsNone(flag(card, "score-without-result"))
        card, _ = evidence_state({"README.md": readme, "docs/benchmarks/x.json": '{"hit@1": 40.2}'})
        self.assertIsNotNone(flag(card, "score-without-result"))

    def test_C31_keep_must_and_script_scoped_dependency_wording_is_not_a_claim(self):
        for line in ["Keep scripts dependency-free.", "Helpers must stay dependency-free.",
                     "Scripts have zero dependencies."]:
            with self.subTest(line=line):
                _, f = mismatches({"README.md": "# T\n\n" + line + "\n", "requirements.txt": "requests\n"})
                self.assertIsNone(f)

    def test_C32_a_bare_flag_with_no_command_beside_it_is_not_checked(self):
        # A plain case this rule now misses (csvtool's "`--json` prints JSON"); the receipt records it.
        _, f = mismatches({"README.md": "# T\n\n- `--json` prints JSON.\n- Licensed under Apache-2.0.\n",
                           "t.py": ARGS})
        self.assertIsNotNone(f)
        self.assertNotIn("--json", f["detail"])


class ClaimChecksAreInformation(unittest.TestCase):
    """The fixed bar left every kind under 5 decided statements on the fresh sample, so both
    checks report at information and move no band."""

    def test_C33_both_claim_flags_are_information_with_no_cap_and_no_band_effect(self):
        files = {"README.md": "# T\n\nLicensed under Apache-2.0. Zero dependencies. `csvtool --json` prints JSON. "
                              "Includes `tests/`. Scores 74% on SWE-bench.\n",
                 "requirements.txt": "requests\n", "t.py": ARGS}
        card = screen({**MINIMAL, **files}, name="csvtool")
        clean = screen({**MINIMAL, "t.py": ARGS}, name="csvtool")
        for fid in ("readme-claim-mismatch", "score-without-result"):
            f = flag(card, fid)
            self.assertEqual(f["severity"], "info", fid)
            self.assertNotIn("caps", f, fid)
        self.assertEqual(card["totals"]["caps_applied"], [])
        self.assertEqual(card["totals"]["band"], clean["totals"]["band"])
