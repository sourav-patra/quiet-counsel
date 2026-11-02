# Screen mode

Deep evaluation of one project takes hours. A hackathon has a hundred submissions and a fixed
window. Scoring all hundred deeply is impossible, and scoring them shallowly while calling it a
verdict is worse.

So there are two passes with a hard boundary between them.

## Pass one, the screen

```sh
quiet-counsel screen ./submissions/* --corpus ./corpus --out ./cards/
quiet-counsel dashboard ./cards/*.json --out cohort.html
```

No model, no network, seconds per project. It produces an archetype with its evidence, around
thirty measured signals, integrity flags, and a band.

| Band | Meaning | What follows |
|---|---|---|
| blocked | A critical flag: a live credential, a licence breach, or text aimed at the evaluator | A person rules before anything else happens |
| review | Serious flags, or a claim the repository contradicts | Goes to the deep pass regardless of how it looks |
| shortlist | Clean screen, strong signals: tests, pinned CI, a declared licence, real history | Goes to the deep pass |
| screened | Clean screen, thin signals | Deep pass if the cohort is small or a judge asks |

A band orders attention. It does not rank quality, and nothing is eliminated by it. Every
project appears on the dashboard either way, because a tool that silently drops submissions is
not a judging aid.

### What the screen measures

Methodology: how many distinct instruction definitions (skills, agents, commands) there are,
the always-loaded description characters and a token estimate, descriptions that do not say
when to use them, definitions that declare tools, non-standard frontmatter keys, the bytes of
root instruction files, and paths those files name that no longer exist. It does not run a
format validator or count bodies over a budget.

Evidence: test files and eval directories, workflow files and how many actions are pinned by
digest, and the claims extracted from the README for comparison. It does not check whether CI
runs the tests, and does not look for committed results or run records.

Safety: credential shapes with path and line, split by confidence, hidden-character scan,
untrusted-content guidance, installers that pipe downloads into a shell, code that writes a host's settings, hooks or
instruction files and whether it asks first, disabled certificate verification, CI actions pinned by digest, lockfiles.

Integrity: licence file and its guessed identity, copyleft markers inside a permissive tree,
the licence every third-party file declares, corpus duplication with the
source licence and credit of each copy, first-commit mass, history span and authorship.

Product: the size of the README and absolute paths that bind the project to one machine. Entry
points, the install path and the documentation surface are not measured.

Every signal carries the command that produced it. A number a reader cannot re-derive does not
go in.

### What a screen cannot claim

Screen output is `unverified` by construction. Its signals may suggest a score and they never
set one. The dashboard draws a screened dimension as an open outline rather than a filled cell,
so a reader can tell an unverified dimension from a scored one at a glance.

## Pass two, the deep evaluation

For each project that reaches it: run the archetype's applicable dimensions, attach evidence to
every score, resolve every flag the screen raised, and re-derive any claim the screen marked
unsupported.

Three rules carried from practice. A check that will not run is never a pass, and the report
says why it would not run. An advisory check that fails is still a failure, even when the gate
around it stays green. A claim closes only when it is re-derived at the evaluated commit,
never from a badge or a release note.

Budget roughly 30 to 60 minutes of careful attention per project, most of it reading. A cohort
of 100 with a shortlist of 15 is about a day, which is the argument for the screen and the
reason its limits travel with its output.

## Judging a cohort fairly

Fix the rubric before you see the cohort. A rubric edited afterwards can always be edited toward
a favourite.

Score each project as its archetype. An orchestrator is not penalised for shipping no catalogue;
the dimension is marked not applicable with a reason.

Do not let one dimension carry the verdict. The dashboard shows the profile precisely so that a
strong build with a weak README is not confused with a strong README.

Publish the cohort's own weaknesses. If 70 of 100 projects have no licence, the event's
guidance is the likelier cause, and the report should say so.

Where two profiles sit within the rubric's own margin of 1, say it is a tie and let a person
break it on something the rubric does not measure.
