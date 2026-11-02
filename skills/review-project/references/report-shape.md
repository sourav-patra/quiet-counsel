# What a verdict contains

One dashboard and one scorecard per project. Both are generated, so neither can drift from the
other.

The scorecard holds the project and the commit, the archetype with its evidence, the measured
signals each with its command, the flags each with file and line, the dimensions with score,
confidence, rationale and evidence, the claims with their status, the totals and band, and the
limits.

The dashboard renders all of it: a cohort table ordered by band, a card per project with the
dimension grid, the flags open by default when serious, the claims beside what measurement
found, every signal with its command, and a closing section on what the run did not establish.

Three things a verdict always states. Which commit it measured. What it could not check and why.
Where the previous verdict was wrong, if there was one.

A verdict with no errata after several runs more likely means nobody checked it than that it was
right every time.
