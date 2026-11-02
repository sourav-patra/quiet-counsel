# Classify before you score

A survey of fourteen catalogues found three repositories with "harness" or "skills" in the name
and no skill definitions in them at all. One was a test runner, one an orchestration engine, one
a showcase web app. In the same survey, none of the fourteen had a top-level `agents/` or
`commands/` directory, though several defined agent-like behaviour nested elsewhere.

A rubric keyed to file paths would have scored every one of them zero and called it a finding,
which is a defect in the rubric. So the suite classifies from evidence, scores only the dimensions that apply to that archetype,
and records in the report which dimensions were skipped and why.

## The five archetypes

| Archetype | What it is | Recognised by |
|---|---|---|
| catalogue | A collection of agent instructions meant to be installed into a host | Skill definitions anywhere in the tree, an install script, a plugin or marketplace manifest |
| harness | A catalogue plus the machinery that governs it | A catalogue, checks or hooks that run over it, and release or governance documents |
| orchestrator | Runs or coordinates agents: queues, permissions, sandboxes | Session and permission handling, run logs, little or no catalogue |
| tool | A single capability an agent calls | A published package, a narrow public interface, its own tests |
| application | A product built with agents, where the agent work is the means | Application entry points, a user interface or service, domain code |

A project can be two things. Score it as the one its README claims to be, and say in the report
that it also functions as the other. An orchestration engine with nine skills is an
orchestrator.

## How the classifier decides

`quiet-counsel classify <path>` scores each archetype from weighted evidence and prints the
evidence beside it. It never reads the repository name.

| Signal | Weighs toward |
|---|---|
| Skill definitions found anywhere, including hidden host directories | catalogue, harness |
| An install script that copies definitions into a host directory | catalogue |
| Checkers or lint suites that read the catalogue | harness, but only when a catalogue exists |
| Release notes, records, governance documents | harness, same condition |
| Session, queue, permission or sandbox handling in code | orchestrator |
| A package manifest with a versioned public interface | tool |
| Application entry points and web assets | application |

Two of those conditions were added after an early version called six ordinary applications
harnesses. Checkers and governance documents are common in any mature repository, so they only
count toward harness when the project also ships a catalogue for them to govern.

The classifier's output is a claim with evidence. An evaluator may override it, and the report
records the override and the grounds. Without the grounds written down, an override lets the
evaluator's preference pass for a measurement.

## Which dimensions apply

`docs/RUBRIC.md` carries the full matrix. Only the methodology group varies, because it asks
about instruction design, which an application mostly does not do. Everything else applies to
anything that ships.

A dimension marked not applicable carries a written reason in the scorecard, and the dashboard
renders it as `n/a` with that reason attached. It is never rendered as a zero and never dropped
silently from the mean, so a project cannot improve its score by doing less.
