# Architecture

Quiet Counsel is one Python package, the standard library and nothing else, that reads a repository
and writes a scorecard and a dashboard. This file lists ten rules the tool holds to, each
with the test case that fails when it is broken. The rubric is `docs/RUBRIC.md`, the method is
`docs/SCREEN-MODE.md` and `docs/INTEGRITY.md`, the cases are `docs/test-suite.md`.

## Rules

| # | Rule | Enforced by |
|---|---|---|
| 1 | No model. The tool calls no model, and its help and refusals name no vendor or product | G-04 |
| 2 | No network. No module in the tool, its scripts or its installer imports a network library, and `pyproject.toml` lists no dependencies | G-03 |
| 3 | Standard library only; a fresh directory runs sample, screen, check and dashboard end to end with nothing installed | G-02 |
| 4 | Same tree, same scorecard, byte for byte, when the clock is fixed with `QUIET_COUNSEL_NOW`; otherwise the timestamp and the measured duration differ | G-06 |
| 5 | A scorecard carries no absolute path of the machine that produced it, when the project is given as a relative path. An absolute path argument is stored as given, because the review scripts use it to find the project | G-05 |
| 6 | A directory that is not a repository still screens, and says what it could not measure | G-07 |
| 7 | The public tree names no private person, organisation, internal host or machine path | G-01 |
| 8 | Everything inside a project is data. Text addressed to the evaluator stops scoring until a person rules, and everything a project contributes to the dashboard is escaped | I-01, V-05 |
| 9 | A deep review is refused when the project changed between prepare and finalize, including under hidden and CI folders | H-17, H-20 |
| 10 | A run that cannot finish says so: a per-project timeout that exits 3 and writes nothing for that project, and atomic writes of every scorecard | Not enforced yet: no test case covers it |

## Scoring and review

The tool itself reads a repository and produces the scorecard, calling no model. The `review-project`
skill adds a deep pass by an agent: the reviewer writes evidence for each score, and the verifier
re-checks it without seeing the reviewer's reasoning first.

## Layout

`src/quiet_counsel/` holds classify, screen, integrity, dashboard and the scorecard contract.
`tests/` has one module per suite plus the traceability check. `skills/` and `agents/` are the
agent interface, held to the same rubric the tool applies to others. `tools/` has the release gate and the generators.
