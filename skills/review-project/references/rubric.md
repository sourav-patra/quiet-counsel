# The 16 dimensions at a glance

Full anchors are in `docs/RUBRIC.md` of the suite repository.

| | Dimension | Asks |
|---|---|---|
| A1 | Instruction-format conformance | Does it pass the format's own validator, and do descriptions say when to use the thing? |
| A2 | Context economy | Is the always-loaded cost measured and budgeted, and do the files name only paths that exist? |
| A3 | Capability boundaries | Can a host enforce what each component may do? |
| A4 | Determinism | Pinned dependencies, pinned external references, repeatable runs |
| B1 | Evaluation rigour | Do evals run in CI, with committed results and a control? |
| B2 | Claim accuracy | Can the project's own numbers be reproduced from the repository? |
| B3 | Audit trail | Is what happened recorded as it happened? |
| C1 | Secret hygiene | Anything credential-shaped in the tree or history? |
| C2 | Untrusted-content posture | Is outside text treated as data, and is that enforced? |
| C3 | Supply chain | Pinned CI, lockfiles, no piping downloads into a shell |
| C4 | Destructive-action gating | Dry run, confirmation, or a permission a host enforces, including before writing a host's settings or hooks |
| D1 | Licence compliance | Own licence declared, redistributed components compliant |
| D2 | Originality and provenance | Is the work the authors', and is borrowed material credited? |
| E1 | Coverage | A useful span of work, reusable beyond one team |
| E2 | Portability | Runs anywhere its format is supported |
| E3 | Maintainability and onboarding | Computed indexes, help text, a newcomer can start |

Scores are 0 to 10 in halves. A judged score can move by 1, a screen-derived one by 2. Means are
unweighted and summarise the rubric rather than usefulness. Some findings cap a group regardless
of the rest: a live credential, a licence breach, text aimed at the evaluator.
