# Changelog

## 0.1.0 (2026-11-02)

- First public release. Quiet Counsel reads an agent project's repository, works out its archetype
  (catalogue, harness, orchestrator, tool or application) from evidence, and writes a scorecard
  with the file and line behind each flag.
- Commands: `classify`, `screen`, `integrity`, `dashboard`, `check`, `verdict` and `sample`. The
  command reference is in `docs/cli.md`.
- Screening measures the rubric's dimensions as unverified. A deep pass, run by an agent with the
  `review-project` skill, scores them with evidence, applies the caps and renders the verdict.
- Agent interface: three skills (`screen-cohort`, `triage-flags`, `review-project`) and three
  roles (`screener`, `reviewer`, `verifier`), installed with `install.py`.
- Standard library only. It does not call a language model or any network service.
- Fixed a flag where a `"main"` string in any manifest counted as a package.json entry.
- Four checks written from public incident reports: `open-time-hook` (commands set to run when a
  folder or agent session opens), `install-time-script`, `workflow-data-out` and
  `untrusted-code-with-power`. Workflows are read line by line, not with a YAML parser; the limits
  are in `docs/test-suite.md`, Suite T.
- `open-time-hook` fires on session-start hooks and folder-open tasks only, and is serious only for a
  download piped to a shell or a script in a different host folder. Other hook events raise an
  information-level `agent-hook`. Evaluator-directed text and copyleft text found only under test
  paths are lowered (serious and warning) and still listed.
- A project's `.scanignore` cannot lower the critical `evaluator-directed-text` flag. The listing limit for
  that flag applies after the defensive-text and test-path tests. A settings file or manifest nested too
  deeply to read raises `unreadable-configuration`. `runOn` is read from parsed tasks, not from comments.
- Evaluator-directed lines judged to be quoted or defensive are listed as `quoted-evaluator-text` at
  information level, with file, line and count, instead of being dropped. `untrusted-code-with-power`
  treats `secrets: inherit` on a reusable-workflow call as holding secrets.
- `tools/check_evidence.py` counts how many flags and numeric signals cite a file and line that
  exist.
- The dashboard and the screen's limits note said every flag names a file and line. Flags about history or a
  missing file cite a command or commit, so both now say every flag names its evidence. `stale-instructions`
  no longer raises on a bare workflow name that exists under `.github/workflows/` (cases Q-12, Q-13, V-10).
- A source line that holds a credential shape, or a word such as `secret`, `token` or `password`,
  is no longer partly quoted with its value masked. The card quotes none of it: the excerpt reads
  `<line withheld>` and the flag keeps its file and line. Every other line is quoted as written.
  This guards against accidents; a repository written to defeat it can still get text onto a card.
  `tools/check_evidence.py` counts these lines as `withheld`. `quiet-counsel integrity` no longer
  prints a whole line it would withhold from a card, and flags are listed in a fixed order
  (cases S-25, M-04, M-07, M-08). A `.scanignore` pattern shown in a card, a hook event name in
  the `agent-hook` detail and a stale path beside a fenced span follow the same rule (case S-25).
- A release-review workflow is not in 0.1. The `verdict` command stays.
- Not yet proven on a real cohort. The field checks are listed in `docs/test-suite.md`.
