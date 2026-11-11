Author-built benchmark. The tool's author chose the checks and wrote the fixtures. Treat results as a description of this set.

# Benchmark

This page reports how ten checks of the screen behave on 400 small fixture projects. The fixtures are in `evals/benchmark/`. The page makes no claim about real repositories.

## Method

- Ten checks, each decidable from the files alone: `secret-in-tree`, `curl-pipe-shell`, `hidden-characters`, `evaluator-directed-text`, `copyleft-in-permissive-tree`, `contradicted-claim`, `open-time-hook`, `install-time-script`, `workflow-data-out`, `untrusted-code-with-power`.
- Each check has 20 positive and 20 near-miss negative fixtures, 400 in all. A label is a property of the files, such as "a workflow on `pull_request_target` checks out the head ref and runs it". No label says what the tool should do. Near misses were written from what `docs/INTEGRITY.md`, `docs/CHECKS.md` and `docs/test-suite.md` say each check decides, not from the tool's patterns.
- `evals/benchmark/fixtures.py` builds every fixture at run time into a temporary folder. Planted values are assembled from pieces, so the repository holds no credential shape and no attack phrase. Hosts are `example.invalid`, reserved documentation addresses, loopback or `api.github.com`. The screen reads the files and nothing in them runs.
- Split: in each group of 20, the 5 fixtures with the smallest `sha256(seed:id)` are the dev split and the other 15 are the test split (100 dev, 300 test). The seed is `qc-bench-2026-11-03`.
- The manifest `evals/benchmark/manifest.json` lists fixture id, check, label, split, property text and the sha256 of each fixture's content. Its hash was recorded before the test split was run. The dev split was run freely, and fixtures whose labels or placement contradicted their own property text were corrected from it. No rule of the tool was changed before the original test run.
- The test split was run once before the rule changes. The changes that followed are described under "After the rule fixes", with the held-out set that checks them.
- Metrics: for each check, the 2 by 2 count of the check's flag at any severity against the label (a warning counts as a flag, so recall for `evaluator-directed-text` includes hits that no longer stop scoring), with the Wilson 95% interval for recall and for the false positive rate. Baselines are flag-all and flag-none. There is no composite score, no rank and no comparison with other tools. The fixtures say nothing about how often these problems occur in real repositories.

Manifest hash (sha256 of `evals/benchmark/manifest.json`): `ad063792b1885549e57990c2a687464d4ccbfab2e78922c1e80f5dc9e6e75b94`

## Rerun

```
py -3 -I evals/benchmark/run.py run --split test --manifest-hash ad063792b1885549e57990c2a687464d4ccbfab2e78922c1e80f5dc9e6e75b94
```

The runner refuses to start if the generator no longer reproduces the manifest.

## Blind second labeller

A second labeller, blind to the author's labels and to the property text, labelled 80 fixtures (20% of the set, stratified: 4 positives and 4 near misses for each check). It was an AI model from a different vendor than the one that wrote the fixtures. It saw the files and the name of the check with its one-line definition. 72 of the 80 labels agree with the author's, and Cohen's kappa is 0.80. The script that computes it is private, so the method in words: kappa is (observed agreement minus chance agreement) divided by (1 minus chance agreement), where chance agreement comes from how often each labeller says positive.

The 8 disagreements, by check:

- `secret-in-tree` (4): four near misses that the second labeller called positive because the planted value still has the shape of a key (a Slack token shape, a hard-coded database password, and two AWS key shapes under a placeholder or example comment).
- `untrusted-code-with-power` (2): one positive the labeller was not certain about because the reusable workflow it calls is absent, and one near miss with a pull-request head built with write permissions.
- `contradicted-claim` (1): a near miss that states two skills while five are present.
- `workflow-data-out` (1): a near miss where a secret is sent as HTTP authentication.

The labels were not changed after the comparison, and the tables below use the author's labels. A disagreement is a sign that the near-miss boundary is arguable for those fixtures, most of all for the four `secret-in-tree` ones.

## Results

Original run on the test split, before any rule change. Run once: 300 fixtures, 15 positive and 15 negative for each check. Recall and false positive rate are given with Wilson 95% intervals. With 15 per group the intervals are wide: a perfect 15 of 15 still allows a true rate down to 0.80.

| check | TP | FN | FP | TN | recall (Wilson 95%) | false positive rate (Wilson 95%) |
|---|---|---|---|---|---|---|
| `secret-in-tree` | 14 | 1 | 0 | 15 | 14/15 = 0.93 (0.70 to 0.99) | 0/15 = 0.00 (0.00 to 0.20) |
| `curl-pipe-shell` | 11 | 4 | 2 | 13 | 11/15 = 0.73 (0.48 to 0.89) | 2/15 = 0.13 (0.04 to 0.38) |
| `hidden-characters` | 13 | 2 | 0 | 15 | 13/15 = 0.87 (0.62 to 0.96) | 0/15 = 0.00 (0.00 to 0.20) |
| `evaluator-directed-text` | 4 | 11 | 3 | 12 | 4/15 = 0.27 (0.11 to 0.52) | 3/15 = 0.20 (0.07 to 0.45) |
| `copyleft-in-permissive-tree` | 15 | 0 | 0 | 15 | 15/15 = 1.00 (0.80 to 1.00) | 0/15 = 0.00 (0.00 to 0.20) |
| `contradicted-claim` | 15 | 0 | 3 | 12 | 15/15 = 1.00 (0.80 to 1.00) | 3/15 = 0.20 (0.07 to 0.45) |
| `open-time-hook` | 15 | 0 | 0 | 15 | 15/15 = 1.00 (0.80 to 1.00) | 0/15 = 0.00 (0.00 to 0.20) |
| `install-time-script` | 15 | 0 | 0 | 15 | 15/15 = 1.00 (0.80 to 1.00) | 0/15 = 0.00 (0.00 to 0.20) |
| `workflow-data-out` | 15 | 0 | 0 | 15 | 15/15 = 1.00 (0.80 to 1.00) | 0/15 = 0.00 (0.00 to 0.20) |
| `untrusted-code-with-power` | 15 | 0 | 0 | 15 | 15/15 = 1.00 (0.80 to 1.00) | 0/15 = 0.00 (0.00 to 0.20) |

Baselines on the same fixtures, each check taken alone: flag-all has recall 150/150 = 1.00 (0.98 to 1.00) and false positive rate 150/150 = 1.00 (0.98 to 1.00); flag-none has recall 0/150 = 0.00 (0.00 to 0.02) and false positive rate 0/150 = 0.00 (0.00 to 0.02).

What the wrong calls were (26 of 300; the ids are listed below the table):

- `evaluator-directed-text` missed 11 of 15 positives. The phrase patterns are case sensitive, and 11 of the planted sentences start with a capital letter. Three near-miss negatives (a request to rate an app, a note to disregard earlier lint warnings, a security policy asking reporters not to report an issue publicly) were flagged.
- `curl-pipe-shell` missed 4 of 15 positives: three sit under `docs/`, which the check treats as a documentation location, and one is a workflow `run:` line that does not begin with the download command. It flagged 2 of 15 negatives: a download piped into a checksum program and into a shell linter, because the pattern accepts any word that begins with `sh` after the pipe.
- `hidden-characters` missed 2 of 15 positives: one under `docs/` and one in a `.rst` file, a file type the scan does not read.
- `secret-in-tree` missed 1 of 15 positives: a key on a line that also holds HTML tags.
- `contradicted-claim` flagged 3 of 15 negatives: a count of skill categories, a count of skill levels, and a future-tense plan, each read as a count of shipped skills.
- The other five checks had no wrong call on the test split.

No test-split fixture was judged wrong, so there is no second figure that excludes one. As a sensitivity check only, leaving out the five positives that sit under `docs/` (three for `curl-pipe-shell`, two for `hidden-characters`) gives `curl-pipe-shell` recall 11/12 and `hidden-characters` recall 13/13; the table above stays the figure of record.

Wrong calls on the test split:

```
FN secret-in-tree-pos15: The file web/index.html is outside any test, example, docs, sample, fixture or mock location and holds a Google API key on a line that has no placeholder wording.
  FN curl-pipe-shell-pos07: The file docs/GETTING-STARTED.md holds a command that downloads with curl or wget and pipes the output into a shell.
  FN curl-pipe-shell-pos12: The file docs/macos.md holds a command that downloads with curl or wget and pipes the output into a shell.
  FN curl-pipe-shell-pos17: The file .github/workflows/prepare.yml holds a command that downloads with curl or wget and pipes the output into a shell.
  FN curl-pipe-shell-pos19: The file docs/windows.md holds a command that downloads with curl or wget and pipes the output into a shell.
  FP curl-pipe-shell-neg03: A download is piped into a checksum program, not a shell.
  FP curl-pipe-shell-neg13: A download is piped into a shell linter, which reads but does not run it.
  FN hidden-characters-pos12: The file docs/usage.md contains the invisible character U+E0020 inside ordinary text outside any test, example or docs-sample location.
  FN hidden-characters-pos19: The file docs/guide.rst contains the invisible character U+200B inside ordinary text outside any test, example or docs-sample location.
  FN evaluator-directed-text-pos03: The file agents/reviewer.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos04: The file CONTRIBUTING.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos05: The file src/main.py holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos09: The file docs/about.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos11: The file config/meta.yml holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos12: The file README.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos13: The file skills/plan/SKILL.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos14: The file docs/FAQ.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos16: The file docs/SUBMISSION.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos17: The file README.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FN evaluator-directed-text-pos19: The file docs/LICENSE-NOTES.md holds a sentence addressed to whoever reviews or scores the repository, asking for a top score, a pass, or silence about problems.
  FP evaluator-directed-text-neg04: The store page asks app users to rate the app ten stars.
  FP evaluator-directed-text-neg07: A lint note says to set aside the older warnings after the upgrade (paraphrased here; the manifest holds the exact words).
  FP evaluator-directed-text-neg09: A security policy tells reporters not to report the issue in public.
  FP contradicted-claim-neg10: The README states 12 skill categories, not 12 skills; the tree holds 3 skills.
  FP contradicted-claim-neg11: The README states 3 skill levels, not 3 shipped skills; the tree holds 1.
  FP contradicted-claim-neg13: The README states a plan for 40 skills in the future tense; the tree holds 2.
```

Raw counts per check, as printed by the runner:

```
{"contradicted-claim": {"FN": 0, "FP": 3, "TN": 12, "TP": 15}, "copyleft-in-permissive-tree": {"FN": 0, "FP": 0, "TN": 15, "TP": 15}, "curl-pipe-shell": {"FN": 4, "FP": 2, "TN": 13, "TP": 11}, "evaluator-directed-text": {"FN": 11, "FP": 3, "TN": 12, "TP": 4}, "hidden-characters": {"FN": 2, "FP": 0, "TN": 15, "TP": 13}, "install-time-script": {"FN": 0, "FP": 0, "TN": 15, "TP": 15}, "open-time-hook": {"FN": 0, "FP": 0, "TN": 15, "TP": 15}, "secret-in-tree": {"FN": 1, "FP": 0, "TN": 15, "TP": 14}, "untrusted-code-with-power": {"FN": 0, "FP": 0, "TN": 15, "TP": 15}, "workflow-data-out": {"FN": 0, "FP": 0, "TN": 15, "TP": 15}}
```

## After the rule fixes

The wrong calls above led to three rule changes, made on the dev split and unit tests only (cases Y-01 to Y-05 in `docs/test-suite.md`): `evaluator-directed-text` phrases match whatever the letter case; `curl-pipe-shell` needs a whole-word shell after the pipe, and reads workflow files including `run:` lines; `contradicted-claim` takes no count from "skill categories", "skill levels" or a sentence about a plan. The `docs/` exemptions and the handling of `.rst` files were not changed.

### Held-out set

A second set, `evals/benchmark/manifest-2.json`, has 10 positive and 10 near-miss fixtures for each of these three checks. It was written from each check's documented definition, in forms the first set did not use, and committed before any rule change. Its sha256 is `1a5faabae7018d9df540540943cfe96d8d1229d6f95b78f5419acd8d797e85d3`. It was run once, after the rule changes, with `py -3 -I evals/benchmark/heldout.py run`. With 10 per group the intervals are very wide.

| check | TP | FN | FP | TN | recall (Wilson 95%) | false positive rate (Wilson 95%) |
|---|---|---|---|---|---|---|
| `evaluator-directed-text` | 7 | 3 | 1 | 9 | 7/10 = 0.70 (0.40 to 0.89) | 1/10 = 0.10 (0.02 to 0.40) |
| `curl-pipe-shell` | 6 | 4 | 0 | 10 | 6/10 = 0.60 (0.31 to 0.83) | 0/10 = 0.00 (0.00 to 0.28) |
| `contradicted-claim` | 9 | 1 | 2 | 8 | 9/10 = 0.90 (0.60 to 0.98) | 2/10 = 0.20 (0.06 to 0.51) |

Wrong calls: `evaluator-directed-text` missed 3 (a JSON description field, a module docstring, a shell `echo`) and flagged a prompt file for the project's own contest tool. `curl-pipe-shell` missed a Makefile, a Dockerfile, a `package.json` script and a Python string, files the check does not read or lines that do not begin with the download command. `contradicted-claim` missed "40+ skills" and flagged "6 skill tiers" and a sentence comparing with a rival's 90 skills.

### Original test split, rerun after the rule changes

This is not held out: the split found the bugs the rules were changed for. The other seven checks are unchanged.

| check | TP | FN | FP | TN | recall (Wilson 95%) | false positive rate (Wilson 95%) |
|---|---|---|---|---|---|---|
| `evaluator-directed-text` | 15 | 0 | 5 | 10 | 15/15 = 1.00 (0.80 to 1.00) | 5/15 = 0.33 (0.15 to 0.58) |
| `curl-pipe-shell` | 12 | 3 | 0 | 15 | 12/15 = 0.80 (0.55 to 0.93) | 0/15 = 0.00 (0.00 to 0.20) |
| `contradicted-claim` | 15 | 0 | 0 | 15 | 15/15 = 1.00 (0.80 to 1.00) | 0/15 = 0.00 (0.00 to 0.20) |

The fixes cleared the failures they targeted: the 11 missed `evaluator-directed-text` positives are caught, the checksum and linter pipes no longer match, and the three claim near misses are no longer flagged. The case-insensitive match also flags two near misses it did not before (a changelog line about a project verified on a Python release, and a migration note about setting older steps aside), so its false positives rose from 3 to 5 of 15. `curl-pipe-shell` still misses the three positives under `docs/`.

### After the review fixes

Later changes touched the scan: `.github` is read by more checks, the installer check filters quoted lines before its budget, and a hit that matches only with case ignored is a warning. The frozen 300 were rerun at the final commit (not held out) and every count in the second table is unchanged, because the table counts a flag at any severity. The held-out counts above were measured at commit 2af7e69 and were not rerun: the code has changed since, and a second look at a held-out set is no longer held out.

### Severity of case-only matches

All 4 `evaluator-directed-text` flags that the case-insensitive match raised at critical or serious, or raised in severity, on 100 field repositories were ruled false by one AI agent (a single reader, not a panel). A hit that matches only because case is ignored is therefore a warning, with no cap and no effect on the band. A hit that matches the original case-sensitive phrases keeps its severity. The counts in the tables above count a flag at any severity, so they do not change.

## What this does not measure

- Real repositories. Every fixture is small and written by the author.
- Whole-project quality or the band. Only whether a named flag is present.
- Checks outside the ten above.
- Agent behaviour. Nothing here shows that a higher or lower result changes what an agent does.
