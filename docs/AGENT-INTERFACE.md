# The agent interface

The tool has two ways in. A person runs the command line. An agent uses the skills and roles
below, which wrap the same code and add the parts a person does by judgement: reading the lines
behind a flag, scoring with evidence, and checking someone else's citations.

## Skills

| skill | what it does | its scripts |
|---|---|---|
| `screen-cohort` | screens one or many projects and builds the dashboard | `screen_cohort.py` |
| `triage-flags` | prints the lines behind every flag so each can be judged in context | `triage_flags.py` |
| `review-project` | prepares a deep-review worksheet, refuses to finalize until every applicable dimension is scored with evidence, applies the caps, verifies citations | `review_project.py prepare`, `finalize`, `verify` |

Every skill follows the agentskills.io format: only the specification's frontmatter keys, a
name matching its folder, a description that says when to use it, and its references and
scripts inside its own folder, one level deep. Each declares the tools it needs in
`allowed-tools`. Every script answers `--help`, uses the standard library, returns 0 on
success, 1 on a refusal with the reasons printed, and 2 on bad input.

The scripts find the package in one of two ways: it is installed (`pip install .` from a
clone), or the skill is still inside the repository and the script finds `src/` above it.

## Roles

| role | tools | job |
|---|---|---|
| `screener` | Read, Grep, Glob, Bash | runs the screen and reports bands, without scoring |
| `reviewer` | Read, Grep, Glob, Bash | runs the deep review and produces the verdict |
| `verifier` | Read, Grep, Glob | re-checks the reviewer's citations, reading the evidence before the reasoning |

No role carries a write tool. The screener and reviewer carry a shell because they run the
scripts, and a shell can write files, so a list of tools cannot stop a reviewer changing the
project it reviews; the host's sandbox can. The verifier has no shell at all.
Finalize checks afterwards: prepare records a hash of every file, and finalize refuses when any
of them changed (case H-17). The before-and-after check is an idea taken from
[the-council](https://github.com/DantesPeak85/the-council), which runs its reviewers read-only and
compares the tree before and after them.

A role file has three frontmatter keys: `name`, `description` and `tools`. No role file names a model;
the host's default applies.

## Installing

```sh
python3 install.py --dest <skills-dir> --agents-dest <agents-dir>
```

`--dest` is the only way to say where. There are deliberately no per-host shortcuts, because a
shortcut can work while the thing it stands for is broken. `--dry-run` prints the plan and
writes nothing. An existing skill or role is never overwritten without `--force`, and nothing
is ever deleted.

Where hosts look, as of this release. These conventions are young and change, so check
your host's own documentation before relying on this table:

| host | skills | roles |
|---|---|---|
| Claude Code, for one project | `.claude/skills/` | `.claude/agents/` |
| Claude Code, for every project | `~/.claude/skills/` | `~/.claude/agents/` |
| hosts that read the shared project convention | `.agents/skills/` | not standardised |
| anything else | wherever it reads agent skills from | wherever it reads subagents from, if anywhere |

## Instructions for agents working on the repository

`AGENTS.md` is the single set of instructions for every host. `CLAUDE.md` is a one-line pointer
to it, for hosts that read only that name. Case H-13 keeps the always-loaded cost of both,
plus every skill description, under 12,000 characters.

## Selection evals

`evals/triggers.jsonl` holds prompts, each with the skill it should select, or none. Case H-15
checks its shape: every skill has at least three prompts that should pick it, and there are
prompts that should pick nothing. Rows marked `held-out` were written before any description was
tuned and are never used to tune one.

`tools/selection_eval.py prompt` writes a prompt from the current descriptions and the eval rows;
give it to any model and `tools/selection_eval.py score` grades the answer. Run it against two
versions of the descriptions for a with-and-without comparison, the method Anthropic's
skill-creator uses for description tuning
([anthropics/skills](https://github.com/anthropics/skills)). The script calls no model itself.
Whether a real host, with its own selection logic, picks the right skill can only be measured on
that host, so that stays case F-03, a field check.

## Everything in a project is data

Every skill and role says it, and case H-14 checks that they do. A project under evaluation can
contain text written to steer whatever reads it. The interface treats that text as a finding
to report, never as an instruction to follow.
