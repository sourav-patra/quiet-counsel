# Changelog

## 0.1.1 (2026-11-04)

- Security: 0.1.0 read history by running `git` with the scanned project's own `.git/config`, so a project that set `log.showSignature=true` and `gpg.program` to a script, and held a commit with a signature header, ran that script during `screen`. Every git call now puts overrides for the settings that start a program (signature checkers, pager, hooks path, file-system monitor, external diff) before the subcommand, and the script no longer runs (case S-26).
- Security: 0.1.0 did not read `.github` for the credential, evaluator-text, hidden-character, installer, licence or copy checks, because every directory whose name starts with `.git` was skipped. Only `.git` is skipped now, and those checks read `.github` (cases Z-10 and Z-11); other hidden directories are still skipped by them. The installer check filters quoted and defensive lines before it applies its budget of 60 hits, so 20 defensive comments no longer hide a real command, and a reached budget is reported (cases Z-13 and Z-14).
- Security: in 0.1.0 a repository's own `.scanignore` could lower its band, because findings in the paths it listed became information by default. A `.scanignore` now changes no flag, cap or band unless the person screening passes `--honour-ignore` for that one project; the card reports the file, its patterns and how many files they match. `--no-ignore` is still accepted and does nothing. A project with a `.scanignore` can move to a stricter band; none of the 50 repositories in the 2 November field run ships one.
- A check that stops at its hit, copy or file budget now says so: the card lists the check and the budget in its limits. For a check that decides a band, the card also carries a `scan-limit-reached` warning and the band is at least `review` (case I-32). For a check that only informs (the README flag check, eval evidence reads, result figure reads, and the listing of evaluator phrases that match only with case ignored) the card carries the limits entry and no flag, and the band does not change (cases Z-08, Z-09, Z-18). This reports a limit and does not close it; text past a budget is still not read. The character budgets count what was read before long lines are cut, so files of very long single lines use them up (cases Z-19 and Z-20). The root `.scanignore` is no longer read by any check, so it cannot use a budget (case I-26). A pattern prints in the signal only when it is path-shaped, patterns are deduplicated and capped at 50 (case I-33), and the licence stop no longer recounts its hits (case I-34).
- Four rule fixes found by the benchmark (`docs/BENCHMARK.md`): `evaluator-directed-text` phrases match whatever the letter case; `curl-pipe-shell` needs a whole-word shell after the pipe (`| sha256sum` and `| shellcheck` no longer match, `zsh` and `dash` do) and now reads `.github/workflows/*.yml`, including `run:` lines; `contradicted-claim` takes no count from "skill categories", "skill levels" or a sentence about a plan ("plan to", "will add", "roadmap"). Cases Y-01 to Y-05. Original-case matches are kept apart from case-only matches, so 25 case-only lines cannot hide a later original-case hit (case Z-17).
- A SPDX line now gets only the label its identifier names (`GPL-3.0` is GPL, `AGPL-3.0` is AGPL, `LGPL-2.1` is LGPL), in source files and in licence files (cases I-23 and I-28). In 0.1.0 one such line was listed once under each label. A licence file naming `AGPL-3.0` is now identified as AGPL, not GPL.
- The test helpers remove their temporary folders when the test process exits (case G-10).
- The test helpers retry `git add` up to four times when git reports `Permission denied` on a path in `.git/objects` with exit 128 (case G-11).
- Both README checks now report at information. After tightening, a run on 50 fresh repositories gave 2 flags (1 true, 1 false; the score flag covers 2 README lines, the mismatch flag 1), under the 5 needed to state a rate, so `readme-claim-mismatch` is no longer a warning. `docs/field-run-2026-11-03.json` holds the aggregates for the tuning and fresh samples.
- Tightened `readme-claim-mismatch` and `score-without-result` after the field adjudication (19 of 21 statements from the first 50 repositories were false). A flag is checked only when it follows the project's own command; command files, `SKILL.md` and shebang scripts count as files that can hold a flag; negated and reader-project paths and owner/repo or model-id tokens are skipped; a figure held by a result file under `docs/`, `benchmarks/` or `results/` clears `score-without-result`; "keep", "must" and script-scoped dependency wording is not a claim.
- New signal `eval_evidence` (`none`, `setup` or `result`, with the paths) and flag `score-without-result` (information, no cap): the README quotes a score, ranking or benchmark comparison and the repository holds no eval result file. A setup file alone is reported as setup. The flag says the result may be kept elsewhere and never says a claim is false. No measured false positive rate yet.
- New flag `readme-claim-mismatch` (information, no cap): the README names a licence, "no dependencies", a `--flag` or a path that the files contradict. Each flag cites the README line and the file or its absence. A field run on 50 fresh repositories gave 2 flags, too few for a rate.
- A `package.json` or `pyproject.toml` of the wrong types no longer ends the screen: the card names the metadata it left unchecked (cases Z-03 to Z-06).
- Elephant-Goldfish wording corrected.

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
