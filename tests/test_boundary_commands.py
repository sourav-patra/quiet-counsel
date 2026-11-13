"""Suite H, cases H-40 to H-52: the output boundary at every command, and the readers beside it.

Round 5 left commands that print what they LOAD (a scorecard or worksheet read from a file), two tools
that printed project text, a skills reader that followed links out of its root, card file names that
could collide, a verify that called a correct withheld citation a mismatch, and an evidence check that
accepted either notice for either reason. Every case here builds the offending input and checks the
output for the credential shape, the credential assignment and the phrase aimed at the evaluator."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest

from helpers import MINIMAL, REPO, project, run_cli, scan, schema
from test_agentic import script
from test_output_boundary import KEY, PHRASE, VALUE, absent, tmp


def _tool(name, *args):
    return subprocess.run([sys.executable, str(REPO / "tools" / name), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _write(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


class CommandBoundary(unittest.TestCase):
    """H-40: a command that emits cards it loaded, rather than cards it just made, filters them first."""

    def _tainted(self):
        card = scan.screen(project(MINIMAL))
        card["project"]["name"] = f"proj {PHRASE}"
        card["project"]["tag"] = f"v-{KEY}"
        card["project"]["commit"] = f"token={VALUE}"
        card["dimensions"][0]["rationale"] = f"the author wrote {PHRASE} and {KEY}"
        card["flags"].append({"id": f"flag-{KEY}", "severity": "warning", "title": f"{PHRASE} {KEY}",
                              "evidence": [{"kind": "file", "ref": f"src/{KEY}.py:1", "excerpt": f"token={VALUE}"},
                                           {"kind": "note", "ref": f"src/{PHRASE}.py:2", "excerpt": PHRASE}]})
        return card

    def test_H40_dashboard_and_verdict_filter_a_card_they_load(self):
        d = tmp()
        card = _write(os.path.join(d, "c.json"), self._tainted())
        page = os.path.join(d, "p.html")
        r = run_cli("dashboard", card, "--out", page)
        self.assertEqual(r.returncode, 0, r.stderr)
        absent(self, r.stdout + r.stderr, "dashboard stdout")
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        absent(self, html, "the dashboard built from a loaded card")
        self.assertIn("withheld", html)
        out = os.path.join(d, "v.json")
        r = run_cli("verdict", card, "--out", out, "--gate-status", "passed")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as fh:
            text = fh.read()
        absent(self, text + r.stdout + r.stderr, "the verdict")
        self.assertIn("withheld", text)
        result = json.loads(text)
        self.assertEqual(result["verdict"], "PATCH")  # a warning  # still computed from the flags
        with open(card, "rb") as fh:
            self.assertEqual(result["scorecard_sha256"], hashlib.sha256(fh.read()).hexdigest())
        # a strict dashboard that refuses names the offending project, and the name is withheld
        bad = self._tainted()
        bad["mode"] = "deep"
        bad["dimensions"][0]["score"] = 5
        bad["dimensions"][0]["evidence"] = []
        r = run_cli("dashboard", _write(os.path.join(d, "u.json"), bad), "--out", page, "--strict")
        self.assertEqual(r.returncode, 1)
        absent(self, r.stdout + r.stderr, "the strict refusal")
        self.assertIn("refusing to build", r.stderr)

    def test_H40_check_prints_a_path_and_a_rule_and_never_a_value_from_the_card(self):
        card = self._tainted()
        card["schema"] = f"scorecard/{KEY}"
        card["mode"] = PHRASE
        card["flags"][-1]["severity"] = f"token={VALUE}"
        card["flags"][-1]["evidence"] = []
        card["claims"] = [{"claim": PHRASE, "status": KEY}]
        card["dimensions"][1]["id"] = f"X-{KEY}"
        card["dimensions"][2]["group"] = VALUE
        card["dimensions"][3]["confidence"] = PHRASE
        card["signals"][f"token={VALUE}"] = {}
        card["totals"] = {"band": KEY}
        card["project"].pop("name")
        r = run_cli("check", _write(os.path.join(tmp(), "c.json"), card))
        self.assertEqual(r.returncode, 1)
        absent(self, r.stdout + r.stderr, "check output")
        for want in ("$.schema: is not scorecard/1", "$.mode:", "$.project.name: missing",
                     ".severity: is not one of", "carries no evidence", "$.claims[0].status:",
                     "$.totals.band:"):
            self.assertIn(want, r.stdout)
        self.assertIn("<problem withheld", r.stdout)  # the signal key held a credential assignment
        for line in r.stdout.splitlines()[1:]:  # every message starts with a path
            self.assertRegex(line.strip(), r"^(\$[.\[\]\w#]*|<problem withheld[^>]*>)")
        self.assertEqual(schema.problems(scan.screen(project(MINIMAL))), [])


class ToolBoundary(unittest.TestCase):
    """H-41: tools/check_evidence.py and tools/selection_eval.py print through the filter."""

    def test_H41_check_evidence_prints_no_credential_or_aimed_text_from_the_path_or_the_card(self):
        root = project({**MINIMAL, "README.md": f"# T\n\nShips 3 skills. {PHRASE}\n"}, name=f"token={VALUE}")
        r = _tool("check_evidence.py", root)
        self.assertIn(r.returncode, (0, 1), r.stderr)
        absent(self, r.stdout + r.stderr, "check_evidence stdout")
        self.assertIn("<line withheld: credential>", r.stdout)  # the first line names the project path
        self.assertIn("flags:", r.stdout)  # the rest of the report is the tool's own
        self.assertNotIn("<line withheld", _tool("check_evidence.py", project(MINIMAL)).stdout)

    def _skills(self, skills):
        base = tmp()
        for name, desc in skills.items():
            _text(os.path.join(base, name, "SKILL.md"), f"---\nname: {name}\ndescription: {desc}\n---\nBody.\n")
        return base

    def test_H41_selection_eval_withholds_a_skill_name_and_description_from_a_supplied_directory(self):
        base = self._skills({"good": "Does good. Use when good is needed.", KEY: "Does y. Use when y.",
                             "evil": f"Use when needed. {PHRASE} and {PHRASE}.", "keyed": f"Use when token={VALUE}"})
        r = _tool("selection_eval.py", "prompt", "--skills", base)
        self.assertEqual(r.returncode, 0, r.stderr)
        absent(self, r.stdout + r.stderr, "the selection prompt")
        self.assertIn("- good: Does good. Use when good is needed.", r.stdout)  # an ordinary skill prints as before
        self.assertIn("<skill name withheld: credential>", r.stdout)
        self.assertIn("<description withheld: text addressed to the evaluator>", r.stdout)
        self.assertIn("<description withheld: credential>", r.stdout)
        # an answer that holds a credential is not echoed back by score
        answer = _write(os.path.join(tmp(), "a.json"), {"1": KEY})
        r = _tool("selection_eval.py", "score", answer)
        self.assertEqual(r.returncode, 1)
        absent(self, r.stdout + r.stderr, "score output")
        self.assertIn("1. expected", r.stdout)


class SkillsRootContainment(unittest.TestCase):
    """H-42: selection_eval never enters a directory or opens a SKILL.md that resolves outside --skills."""

    def _link(self, target, where, directory):
        try:
            os.symlink(target, where, target_is_directory=directory)
        except (OSError, NotImplementedError, AttributeError) as exc:
            if directory and os.name == "nt" and subprocess.run(
                    ["cmd", "/c", "mklink", "/J", where, target], capture_output=True).returncode == 0:
                return
            self.skipTest(f"this system refused to create a link: {exc}")

    def test_H42_a_linked_skill_directory_or_skill_file_outside_the_skills_root_is_skipped_and_named(self):
        base = tmp()
        outside = os.path.join(base, "outside")
        _text(os.path.join(outside, "stolen", "SKILL.md"), "---\nname: stolen\ndescription: OUTSIDE-DESCRIPTION-ONE\n---\n")
        _text(os.path.join(outside, "file.md"), "---\nname: filelinked\ndescription: OUTSIDE-DESCRIPTION-TWO\n---\n")
        skills = os.path.join(base, "skills")
        _text(os.path.join(skills, "inside", "SKILL.md"), "---\nname: inside\ndescription: Does inside. Use when inside.\n---\n")
        self._link(os.path.join(outside, "stolen"), os.path.join(skills, "linkeddir"), True)
        os.makedirs(os.path.join(skills, "linkedfile"))
        try:
            os.symlink(os.path.join(outside, "file.md"), os.path.join(skills, "linkedfile", "SKILL.md"))
            file_link = True
        except (OSError, NotImplementedError, AttributeError):
            file_link = False  # Windows needs a privilege to link a file; the directory link above still ran
        r = _tool("selection_eval.py", "prompt", "--skills", skills)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("OUTSIDE-DESCRIPTION", r.stdout + r.stderr)
        self.assertNotIn("stolen", r.stdout)
        self.assertIn("- inside: Does inside. Use when inside.", r.stdout)
        self.assertIn("skipped, resolves outside the skills directory: directory linkeddir", r.stderr)
        if file_link:
            self.assertIn("skipped, resolves outside the skills directory: file linkedfile/SKILL.md", r.stderr)
            self.assertNotIn("filelinked", r.stdout)
        # a link that stays inside the root is still read
        self._link(os.path.join(skills, "inside"), os.path.join(skills, "alias"), True)
        r = _tool("selection_eval.py", "prompt", "--skills", skills)
        self.assertEqual(r.stdout.count("Does inside."), 2, r.stdout)

    def test_H42_the_repository_prompt_is_unchanged_by_the_containment_check(self):
        r = _tool("selection_eval.py", "prompt")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        for name in ("screen-cohort", "triage-flags", "review-project"):
            self.assertIn(f"- {name}: ", r.stdout)


class CohortFileNames(unittest.TestCase):
    """H-43: one file per project across the whole cohort, never an overwrite."""

    def test_H43_names_are_unique_over_the_whole_list_whatever_their_order_or_letter_case(self):
        names = scan.card_file_names(["<name withheld: credential>", "project-1", "a", "a", "A", "b.", "B", "nul"])
        self.assertEqual(len(names), 8)
        self.assertEqual(len({n.casefold().rstrip(". ") for n in names}), 8, names)
        self.assertEqual(names[1], "project-1.json")  # a project really called project-1 keeps its name
        self.assertNotEqual(names[0], "project-1.json")  # and the withheld one moves
        self.assertEqual(names[2], "a.json")
        self.assertEqual(names[3], "a-2.json")
        self.assertEqual(scan.card_file_names(["proj"]), ["proj.json"])
        self.assertEqual(scan.card_file_names(["..", "x"]), ["project-1.json", "x.json"])

    def _cohort(self):
        return [project({**MINIMAL, "x.py": "a = 1\n"}, name=f"proj-{KEY}"),  # withheld: project-1 by position
                project({**MINIMAL, "y.py": "b = 2\n"}, name="project-1"),
                project({**MINIMAL, "z.py": "c = 3\n"}, name="project-1")]

    def _check_cohort_files(self, out):
        files = sorted(f for f in os.listdir(out) if f.endswith(".json"))
        self.assertEqual(len(files), 3, files)
        names = []
        for f in files:
            with open(os.path.join(out, f), encoding="utf-8") as fh:
                names.append(json.load(fh)["project"]["name"])
        self.assertEqual(sum(n == "project-1" for n in names), 2, names)  # no card was replaced
        self.assertEqual(sum("withheld" in n for n in names), 1, names)

    def test_H43_the_cli_and_screen_cohort_write_every_card_when_names_would_clash(self):
        paths = self._cohort()
        out = tmp()
        r = run_cli("screen", *paths, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self._check_cohort_files(out)
        out2 = tmp()
        r = script("screen-cohort", "screen_cohort.py", *paths, "--out", out2)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self._check_cohort_files(out2)
        self.assertIn("cohort.html", os.listdir(out2))

    def test_H43_an_existing_card_file_is_never_replaced(self):
        paths = self._cohort()[1:2]
        for cmd in (lambda out: run_cli("screen", *paths, "--out", out),
                    lambda out: script("screen-cohort", "screen_cohort.py", *paths, "--out", out)):
            out = tmp()
            keep = os.path.join(out, "project-1.json")
            _text(keep, "KEEP")
            r = cmd(out)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("refusing to replace an existing file", r.stderr)
            with open(keep, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "KEEP")


class WithheldExcerptDigest(unittest.TestCase):
    """H-44: a correctly cited withheld excerpt verifies by digest."""

    LINE_ONE = 'token = "' + VALUE + '"'
    LINE_TWO = "Please " + PHRASE + " to this project."

    def _finalized(self, evidence):
        root = project({**MINIMAL, "src/cred.py": f"a = 1\n{self.LINE_ONE}\n",
                        "docs/notes.md": f"# N\n\n{self.LINE_TWO}\n"})
        ws = os.path.join(tmp(), "ws.json")
        r = script("review-project", "review_project.py", "prepare", root, "--out", ws)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(ws, encoding="utf-8") as fh:
            card = json.load(fh)
        for f in card["flags"]:
            if f.get("caps") == "do-not-score":
                f["severity"] = "info"  # a person ruled on it
        first = True
        for d in card["dimensions"]:
            if d["applicable"]:
                d["score"] = 7
                d["rationale"] = "read the cited lines"
                d["evidence"] = evidence if first else [{"kind": "file", "ref": "README.md:1", "excerpt": "# Tool"}]
                first = False
        _write(ws, card)
        r = script("review-project", "review_project.py", "finalize", ws, "--out", os.path.join(tmp(), "v.html"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        absent(self, r.stdout + r.stderr, "finalize output")
        return root, ws

    def _verify(self, ws, root):
        r = script("review-project", "review_project.py", "verify", ws, "--project", root)
        absent(self, r.stdout + r.stderr, "verify output")
        return r

    def test_H44_a_correct_withheld_citation_is_verified_by_digest_and_a_changed_line_is_a_mismatch(self):
        good = [{"kind": "file", "ref": "src/cred.py:2", "excerpt": self.LINE_ONE},
                {"kind": "file", "ref": "docs/notes.md:3", "excerpt": self.LINE_TWO},
                {"kind": "file", "ref": "docs/notes.md:3", "excerpt": PHRASE},  # a fragment of the line
                {"kind": "file", "ref": "src/cred.py:1", "excerpt": "a = 1"}]
        root, ws = self._finalized(good)
        with open(ws, encoding="utf-8") as fh:
            card = json.load(fh)
        shown = [e for d in card["dimensions"] for e in d["evidence"] if "withheld" in e.get("excerpt", "")]
        self.assertEqual(len(shown), 3)
        for e in shown:
            self.assertRegex(e["excerpt_sha256"], r"^[0-9a-f]{64}$")
        r = self._verify(ws, root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.count("withheld, verified by digest"), 3, r.stdout)
        self.assertNotIn("MISMATCH", r.stdout)
        # a second finalize keeps the digests
        r = script("review-project", "review_project.py", "finalize", ws, "--out", os.path.join(tmp(), "v.html"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self._verify(ws, root).stdout.count("withheld, verified by digest"), 3)
        # the cited line changes: the digest no longer matches, whatever the notice says
        _text(os.path.join(root, "src", "cred.py"), 'a = 1\ntoken = "another-value-123"\n')
        r = self._verify(ws, root)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.count("MISMATCH"), 1, r.stdout)
        self.assertIn("no longer reads the withheld excerpt it cited", r.stdout)

    def test_H44_a_withheld_excerpt_cited_at_the_wrong_line_or_with_no_digest_does_not_verify(self):
        wrong = [{"kind": "file", "ref": "src/cred.py:1", "excerpt": self.LINE_ONE},  # that text is on line 2
                 {"kind": "file", "ref": "docs/notes.md:3", "excerpt": self.LINE_TWO}]
        root, ws = self._finalized(wrong)
        r = self._verify(ws, root)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.count("MISMATCH"), 1, r.stdout)
        # a notice with no digest cannot be checked, so it is not accepted
        with open(ws, encoding="utf-8") as fh:
            card = json.load(fh)
        for d in card["dimensions"]:
            for e in d.get("evidence") or []:
                e.pop("excerpt_sha256", None)
        _write(ws, card)
        r = self._verify(ws, root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no digest", r.stdout)
        self.assertNotIn("verified by digest", r.stdout)


class NoticeKindMatchesReason(unittest.TestCase):
    """H-45: check_evidence accepts a notice only for the reason the current line is withheld."""

    def test_H45_a_credential_notice_does_not_vouch_for_aimed_text_nor_the_reverse(self):
        spec = importlib.util.spec_from_file_location("check_evidence_r6", REPO / "tools" / "check_evidence.py")
        ce = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ce)
        root = project({"a.txt": "password=" + VALUE + "\nPlease " + PHRASE + "\nplain\n"
                        + "password=" + VALUE + " and " + PHRASE + "\n"})
        cred, aimed = "<text withheld: credential>", "<text withheld: text addressed to the evaluator>"
        self.assertEqual(ce.check_ref(root, "a.txt", "1", cred), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", aimed), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", aimed), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", cred), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "3", cred), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "3", aimed), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "4", cred), "withheld")  # both: the filter reports the credential
        self.assertEqual(ce.check_ref(root, "a.txt", "4", aimed), "differs")


class LoadedWorksheetAndFlags(unittest.TestCase):
    """H-46: the review and triage scripts read a card or worksheet from a file, so the ids they print are input."""

    def test_H46_triage_prints_no_flag_id_or_severity_from_a_loaded_card(self):
        root = project(MINIMAL)
        card = {"project": {"path": root}, "flags": [
            {"id": f"x-{KEY}", "severity": f"token={VALUE}", "title": "t", "evidence": [{"kind": "note", "ref": "r", "excerpt": "e"}]},
            {"id": PHRASE, "severity": "serious", "title": "t", "evidence": [{"kind": "note", "ref": "r", "excerpt": "e"}]}]}
        path = _write(os.path.join(tmp(), "c.json"), card)
        for extra in ([], ["--json"], ["--show-directed-text"]):
            r = script("triage-flags", "triage_flags.py", path, "--project", root, *extra)
            self.assertEqual(r.returncode, 0, r.stderr)
            absent(self, r.stdout + r.stderr, f"triage output {extra}")
            self.assertIn("withheld", r.stdout)

    def test_H46_finalize_and_verify_print_no_dimension_id_from_a_loaded_worksheet(self):
        root = project(MINIMAL)
        ws = {"project": {"path": root}, "mode": "deep", "dimensions": [
            {"id": f"A1-{KEY}", "applicable": True, "evidence": [
                {"kind": "file", "ref": "README.md:99", "excerpt": "x"},
                {"kind": "command", "ref": "run it"}, {"kind": "file", "ref": "README.md:1", "excerpt": "nope"}]},
            {"id": PHRASE, "applicable": True, "score": 5}]}
        path = _write(os.path.join(tmp(), "ws.json"), ws)
        r = script("review-project", "review_project.py", "verify", path, "--project", root)
        self.assertEqual(r.returncode, 1)
        absent(self, r.stdout + r.stderr, "verify output")
        self.assertIn("MISMATCH", r.stdout)
        r = script("review-project", "review_project.py", "finalize", path, "--out", os.path.join(tmp(), "v.html"))
        self.assertEqual(r.returncode, 1)
        absent(self, r.stdout + r.stderr, "finalize refusal")
        self.assertIn("refused:", r.stdout)


def _review_module():
    spec = importlib.util.spec_from_file_location(
        "review_project_r7", REPO / "skills" / "review-project" / "scripts" / "review_project.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _scored(files, evidence=None):
    """Prepare a worksheet for a project, score every applicable dimension 7 with one ordinary citation
    (or `evidence` on the first), and return (root, worksheet path, card)."""
    root = project({**MINIMAL, **files})
    ws = os.path.join(tmp(), "ws.json")
    r = script("review-project", "review_project.py", "prepare", root, "--out", ws)
    assert r.returncode == 0, r.stdout + r.stderr
    with open(ws, encoding="utf-8") as fh:
        card = json.load(fh)
    for f in card["flags"]:
        if f.get("caps") == "do-not-score":
            f["severity"] = "info"
    first = True
    for d in card["dimensions"]:
        if d["applicable"]:
            d["score"] = 7
            d["rationale"] = "read the cited lines"
            d["evidence"] = evidence if (first and evidence) else [
                {"kind": "file", "ref": "README.md:1", "excerpt": "# Tool"}]
            first = False
    _write(ws, card)
    return root, ws, card


def _finalize(ws):
    return script("review-project", "review_project.py", "finalize", ws, "--out", os.path.join(tmp(), "v.html"))


class LoadedCapsAndAnswers(unittest.TestCase):
    """H-47: the cap strings finalize prints and the answers selection_eval scores are input."""

    def test_H47_finalize_prints_the_filtered_cap_strings_not_the_raw_ones(self):
        root, ws, card = _scored({})
        card["flags"].append({"id": "cap-flag", "severity": "warning", "title": "t", "caps": f"token={VALUE}",
                              "evidence": [{"kind": "note", "ref": "r", "excerpt": "e"}]})
        _write(ws, card)
        r = _finalize(ws)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        absent(self, r.stdout + r.stderr, "finalize output")
        self.assertIn("withheld", r.stdout)
        self.assertIn("verdict written", r.stdout)

    def test_H47_selection_eval_reports_a_non_string_answer_by_its_key_and_never_echoes_it(self):
        answers = {"1": {"token": VALUE}, "2": [KEY], "3": 12345, "4": True, "5": {"a": PHRASE}}
        r = _tool("selection_eval.py", "score", _write(os.path.join(tmp(), "a.json"), answers))
        self.assertEqual(r.returncode, 1)
        absent(self, r.stdout + r.stderr, "score output")
        self.assertNotIn("12345", r.stdout)
        for n in range(1, 6):
            self.assertRegex(r.stdout, rf"(?m)^  {n}\. expected .*invalid answer")
        # null is an answer: row 13 expects it, so an answer of null is a hit and is not reported
        ok = _tool("selection_eval.py", "score", _write(os.path.join(tmp(), "b.json"), {"13": None}))
        self.assertFalse([l for l in ok.stdout.splitlines() if l.startswith("  13.")], ok.stdout)


class NoticeNeedsItsDigest(unittest.TestCase):
    """H-48: verify recognises a withholding notice before any text match."""

    NOTICE = "<excerpt withheld: credential>"

    def test_H48_a_line_holding_the_literal_notice_does_not_vouch_for_a_notice_without_a_matching_digest(self):
        mod = _review_module()
        secret = "token = " + '"' + VALUE + '"'
        hostile = f'NOTE = "{self.NOTICE}"  # {secret}'
        root = project({**MINIMAL, "src/hostile.py": hostile + "\n"})
        wrong = mod.excerpt_sha("something the line never held")
        evidence = [
            {"kind": "file", "ref": "src/hostile.py:1", "excerpt": self.NOTICE},                                    # no digest
            {"kind": "file", "ref": "src/hostile.py:1", "excerpt": self.NOTICE, "excerpt_sha256": wrong},           # wrong digest
            {"kind": "file", "ref": "src/hostile.py:1", "excerpt": self.NOTICE, "excerpt_sha256": "0" * 64},        # wrong digest
            {"kind": "file", "ref": "src/hostile.py:1", "excerpt": self.NOTICE,
             "excerpt_sha256": mod.excerpt_sha(self.NOTICE)},                                                       # digest of the notice
            {"kind": "file", "ref": "src/hostile.py:1", "excerpt": "NOTE ="},                                       # control: plain text
            {"kind": "file", "ref": "src/hostile.py:1", "excerpt": self.NOTICE,
             "excerpt_sha256": mod.excerpt_sha(secret)},                                                            # control: right digest
        ]
        ws = _write(os.path.join(tmp(), "ws.json"), {"project": {"path": root}, "mode": "deep", "dimensions": [
            {"id": "A1", "applicable": True, "evidence": evidence}]})
        r = script("review-project", "review_project.py", "verify", ws, "--project", root)
        absent(self, r.stdout + r.stderr, "verify output")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.count("MISMATCH"), 4, r.stdout)
        self.assertIn("2 citation(s) match", r.stdout)
        self.assertEqual(r.stdout.count("verified by digest"), 1, r.stdout)
        self.assertIn("no digest", r.stdout)


class OneExcerptLimit(unittest.TestCase):
    """H-49: finalize and verify share one line limit and one fragment limit."""

    def _secret(self, n):
        return ("password=" + "q" * n)[:n]

    def test_H49_a_withheld_fragment_over_the_limit_is_refused_by_finalize_and_one_at_the_limit_verifies(self):
        mod = _review_module()
        self.assertEqual(mod.FRAGMENT_LIMIT, 400)
        over, edge = self._secret(mod.FRAGMENT_LIMIT + 1), self._secret(mod.FRAGMENT_LIMIT)
        line = "x = 1  # " + over + " trailing text"
        root, ws, card = _scored({"src/long.py": line + "\n"},
                                 [{"kind": "file", "ref": "src/long.py:1", "excerpt": over}])
        r = _finalize(ws)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("too long to withhold and verify", r.stdout)
        self.assertNotIn("q" * 30, r.stdout + r.stderr)
        # the same line, cited at the limit: accepted, withheld and verified by digest
        with open(ws, encoding="utf-8") as fh:
            card = json.load(fh)
        card["dimensions"][[d["applicable"] for d in card["dimensions"]].index(True)]["evidence"] = [
            {"kind": "file", "ref": "src/long.py:1", "excerpt": edge}]
        _write(ws, card)
        r = _finalize(ws)
        self.assertEqual(r.returncode, 0, r.stdout)
        v = script("review-project", "review_project.py", "verify", ws, "--project", root)
        self.assertEqual(v.returncode, 0, v.stdout)
        self.assertIn("withheld, verified by digest", v.stdout)
        self.assertNotIn("q" * 30, v.stdout + v.stderr)
        # verify itself holds the same limits
        self.assertTrue(mod.holds_excerpt(line, mod.excerpt_sha(edge)))
        self.assertFalse(mod.holds_excerpt(line, mod.excerpt_sha(over)))

    def test_H49_a_withheld_fragment_past_the_line_limit_is_refused_by_finalize(self):
        mod = _review_module()
        frag = self._secret(40)
        line = "y" * (mod.LINE_LIMIT + 100) + " " + frag
        root, ws, card = _scored({"src/wide.py": line + "\n", "src/near.py": "z = 0  # " + frag + "\n"},
                                 [{"kind": "file", "ref": "src/wide.py:1", "excerpt": frag}])
        r = _finalize(ws)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("too long to withhold and verify", r.stdout)
        self.assertFalse(mod.holds_excerpt(line, mod.excerpt_sha(frag)))
        # the same fragment near the start of its line is accepted
        with open(ws, encoding="utf-8") as fh:
            card = json.load(fh)
        card["dimensions"][[d["applicable"] for d in card["dimensions"]].index(True)]["evidence"] = [
            {"kind": "file", "ref": "src/near.py:1", "excerpt": frag}]
        _write(ws, card)
        self.assertEqual(_finalize(ws).returncode, 0)


class DerivedCapsAreRecomputed(unittest.TestCase):
    """H-50: finalize clears what it derived last time before it derives it again."""

    def test_H50_ruling_a_capped_flag_informational_removes_the_cap_from_totals_and_the_page(self):
        root, ws, card = _scored({})
        card["flags"].append({"id": "cap-flag", "severity": "warning", "title": "t", "caps": "C1<=3",
                              "evidence": [{"kind": "note", "ref": "r", "excerpt": "e"}]})
        _write(ws, card)
        out = os.path.join(tmp(), "v.html")
        r = script("review-project", "review_project.py", "finalize", ws, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(ws, encoding="utf-8") as fh:
            first = json.load(fh)
        capped = [d for d in first["dimensions"] if d.get("capped_to") is not None]
        self.assertEqual([d["id"] for d in capped], ["C1"])
        self.assertEqual(first["totals"]["caps_applied"], ["C1<=3"])
        with open(out, encoding="utf-8") as fh:
            self.assertIn("capped to 3", fh.read())
        # a person rules the flag informational; finalize again
        for f in first["flags"]:
            if f["id"] == "cap-flag":
                f["severity"] = "info"
        _write(ws, first)
        r = script("review-project", "review_project.py", "finalize", ws, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(ws, encoding="utf-8") as fh:
            second = json.load(fh)
        self.assertFalse(any("capped_to" in d for d in second["dimensions"]))
        self.assertEqual(second["totals"]["caps_applied"], [])
        self.assertEqual(second["totals"]["mean"], 7)
        self.assertGreater(second["totals"]["mean"], first["totals"]["mean"])
        with open(out, encoding="utf-8") as fh:
            self.assertNotIn("capped to", fh.read())


class ReadersOpenOnlyRegularFiles(unittest.TestCase):
    """H-51, H-52: two readers that opened a scanned or named path with a bare open()."""

    def test_H51_triage_reports_a_missing_file_without_opening_the_path_and_skips_a_named_pipe(self):
        from unittest import mock
        spec = importlib.util.spec_from_file_location(
            "triage_flags_h51", REPO / "skills" / "triage-flags" / "scripts" / "triage_flags.py")
        tf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tf)
        root = project({**MINIMAL})
        real_open, seen = open, []

        def watching(file, *args, **kwargs):
            seen.append(str(file))
            return real_open(file, *args, **kwargs)

        with mock.patch("builtins.open", watching):
            lines, error = tf.read_lines(root, "gone.txt")
        self.assertIsNone(lines)
        self.assertIn("No such file", error)
        self.assertFalse([f for f in seen if f.endswith("gone.txt")], seen)
        if not hasattr(os, "mkfifo"):
            self.skipTest("this system has no named pipes (os.mkfifo)")
        os.mkfifo(os.path.join(root, "pipe.txt"))
        script_path = str(REPO / "skills" / "triage-flags" / "scripts" / "triage_flags.py")
        code = ("import importlib.util\n"
                f"s = importlib.util.spec_from_file_location('tf', {script_path!r})\n"
                "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                f"print(m.read_lines({root!r}, 'pipe.txt')[1])\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env={**os.environ, "PYTHONPATH": str(REPO / "src")}, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertEqual(r.stdout.strip(), "not a regular file, so it was not read")

    def test_H52_selection_eval_reads_a_skill_file_with_invalid_bytes_and_skips_a_named_pipe(self):
        skills = os.path.join(tmp(), "skills")
        os.makedirs(os.path.join(skills, "odd"))
        with open(os.path.join(skills, "odd", "SKILL.md"), "wb") as fh:
            fh.write(b"---\nname: odd\ndescription: Handles caf\xe9 text. Use when odd.\n---\n")
        _text(os.path.join(skills, "fine", "SKILL.md"),
              "---\nname: fine\ndescription: Does fine. Use when fine.\n---\n")
        cmd = [sys.executable, str(REPO / "tools" / "selection_eval.py"), "prompt", "--skills", skills]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertIn("- odd: Handles caf� text. Use when odd.", r.stdout)
        self.assertIn("- fine: Does fine. Use when fine.", r.stdout)
        if not hasattr(os, "mkfifo"):
            self.skipTest("this system has no named pipes (os.mkfifo)")
        os.makedirs(os.path.join(skills, "piped"))
        os.mkfifo(os.path.join(skills, "piped", "SKILL.md"))
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertNotIn("piped", r.stdout)
        self.assertIn("- fine: Does fine. Use when fine.", r.stdout)

if __name__ == "__main__":
    unittest.main()
