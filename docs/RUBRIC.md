# The rubric

Sixteen dimensions in five groups, each scored 0 to 10 in integers or halves. Every published
score states its confidence (`measured`, `judged`, `unverified`) and carries at least one piece
of evidence. The dashboard refuses to render a score with nothing behind it.

A judged score can reasonably move by 1 in either direction. A score taken from screen signals
alone can move by 2 and stays marked `unverified` until a deep pass confirms it.

Means are unweighted, within a group and overall. A mean summarises this rubric and nothing
else, which is why the dashboard shows the whole profile beside it. Two projects with the same
mean are often nothing alike.

## Group A, methodology and agentic design

### A1, instruction-format conformance

At 10, every definition passes the format's own
validator, each description names what the thing does and the occasions that call for it, no undeclared extension keys
appear, and references resolve relative to the definition and one level deep. At 5 it conforms
loosely, with extension keys or absolute paths that only work in one checkout. At 0 it is not
recognisable as agent instructions. Measured with the official validator where one exists.

### A2, context economy

At 10 the always-loaded cost is measured, budgeted and enforced,
supporting material is read only when a task calls for it, and each path the always-loaded files name points at a file that exists. At 5
disclosure is a convention and nothing measures the cost. At 0 everything loads on every
session. Measured as always-loaded bytes and an estimated token count, counting one copy of each
distinct definition, and the paths in root instruction files that no longer exist.

A longer instruction file does not score higher. Two 2026 studies of `AGENTS.md` files disagree
on whether they help at all: one measured less runtime and fewer output tokens with the file
(Lulla et al., arXiv 2601.20404), the other found no gain in task success and more than 20%
higher cost, and recommends only minimal, necessary content (Gloaguen et al., arXiv 2602.11988).
Stale instructions have a name in the research, context debt (Chatlatanagulchai et al., arXiv
2511.12884).

### A3, capability boundaries

At 10 each agent or skill declares the tools it needs, reviewers
and verifiers cannot write, and a host can enforce the separation. At 5 the boundary exists only
in prose, as in "the reviewer never edits". At 0 every component runs with whatever the session
has. This dimension is never skipped: a system that gives an agent tools has a boundary
question, even when the answer is that it has none.

### A4, determinism and reproducibility

At 10 dependencies are pinned, external references are
pinned with a stop condition, and a run repeated at a stated revision produces the same artifact.
At 0 versions float and external content is unpinned.

## Group B, evidence and evaluation

### B1, evaluation rigour

At 10 behavioural and selection evals run in CI, results are
committed, failures block, and at least one comparison has a control. At 5 evals exist and are
run by hand. At 0 there are none.

### B2, claim accuracy

At 10 every number the project states about itself can be reproduced
from the repository, and anything that cannot is labelled an estimate. At 0 the claims
contradict what the repository contains. This is where an inflated project page gets caught, and
it is fully mechanical.

### B3, audit trail

At 10 what happened is recorded as it happened: run records, receipts
carrying command output, provenance for generated artifacts, a history that is not rewritten. At
5 there is a changelog and commit history. At 0 results are asserted in prose.

## Group C, safety and security

### C1, secret and credential hygiene

At 10 there are no secrets in the tree or its history,
credentials come from the environment or a store, and the repository scans for them itself. A
single live credential caps the whole group at 3 and raises a critical flag.

### C2, untrusted-content posture

At 10 outside text is explicitly treated as data, there is
guidance for injected instructions in tool output, and instruction text is scanned for hidden
characters. At 5 guidance exists in one place and nothing enforces it. At 0 there is nothing, in
a system that reads external content.

### C3, supply chain

At 10 CI actions are pinned by digest, lockfiles are committed, installers
do not pipe downloads into a shell, certificate verification is never disabled, and releases
carry provenance. At 0 nothing is pinned, or an installer executes remote content unchecked.

### C4, destructive-action gating

At 10 anything that deletes, overwrites, deploys or spends is
gated by a dry run, a confirmation, or a permission the host enforces. At 5 it is documented as
dangerous and left ungated. At 0 the destructive path is the default.
Measured in part from code that writes to a host's settings, hooks or standing-instruction
files, and whether that code asks first.

## Group D, legal and integrity
### D1, licence compliance

At 10 the project states its licence, every redistributed component
carries its own licence and attribution, and no copyleft component is redistributed under a
permissive or closed licence. At 0 it redistributes content whose licence forbids it, or strips
attribution. Flags here are critical by default, because a licence breach survives a rewrite.
Measured from the root licence, copyleft licence files and SPDX headers, and the licence every
third-party file declares or, with a corpus, came from.

### D2, originality and provenance

At 10 the work is the authors', with a history consistent
with the claimed effort, and borrowed material is credited at file level. At 5 there is
substantial borrowed material, credited loosely. At 0 copied work is presented as original.
Measured from file-level duplication against a corpus. History shape, authorship spread and
whether the first commit already contains the finished project are not measured in 0.1.2, which starts no git program. A copy credited nowhere caps
this dimension at 3.

## Group E, product and operability

### E1, coverage

Does it do a useful span of work, and is that span reusable beyond one team?
At 10 it is broad, deep and composable. At 0 it is a demo with one path.

### E2, portability

Does it run anywhere its format is supported, without absolute paths,
host-only keys or one vendor's assumptions?

### E3, maintainability and onboarding

Are indexes computed rather than hand-kept, do scripts
carry help and stable diagnostics, and can a newcomer install the thing and do one real task
without being told how?

## Applicability by archetype

"no" means the dimension is skipped and the scorecard records a reason.

| | A1 | A2 | A3 | A4 | B1 | B2 | B3 | C1 | C2 | C3 | C4 | D1 | D2 | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| catalogue | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| harness | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| orchestrator | no | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| tool | no | no | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| application | no | no | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## Caps that override the mean

Some findings are facts about the whole project rather than a low score on one dimension.

| Finding | Effect |
|---|---|
| A live credential in the tree or history | Group C capped at 3, critical flag |
| A copyleft component redistributed under an incompatible licence | D1 set to 0, critical flag, not recommendable until resolved |
| Instruction text aimed at the evaluator | Critical flag, project reported and left unscored until a person rules |
| A headline claim the repository contradicts | B2 at most 2, with the contradiction quoted |
| Share-alike text inside a tree under another licence | D1 set to 0, critical flag |
| Third-party text whose terms forbid reuse, or that has no licence | D1 at most 3, serious flag |
| A copied file credited nowhere | D2 at most 3, serious flag |
| Nothing in the repository runs | E1 at most 2, judged in the deep pass; the screen does not detect it |

A cap appears in the report with the evidence that triggered it. A cap without its evidence is
the same failure as a score without evidence.

## Where the anchors are weak

Only A1 rests on an external standard. The other fifteen dimensions are anchored judgement, and
a reader who disputes an anchor is disputing the evaluator rather than an industry body.

Coverage rewards size, which is a real bias against small, disciplined projects. Security is
scored from what the repository shows, so branch protection, organisation policy and runtime
sandboxing sit outside it. That is a gap in the instrument rather than a finding about the
project.
