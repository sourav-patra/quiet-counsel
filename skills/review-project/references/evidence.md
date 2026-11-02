# What counts as evidence

A command and its output, at a named commit, in a clean clone. Not a release note, a changelog
line, a status field, a plan, a pull-request title, or a project's own claim to be fixed.

Four rules settle the close calls, each written after it was needed.

A check that will not execute leaves its item open, and the report records why it would not run.

An advisory check that fails is a failure. A checker running in a non-blocking posture still
reports a real defect, even though the gate around it stayed green.

A check exercises the primary interface, not a convenience alias. A shorthand flag can pass
while the interface it wraps is broken.

A defect closes only when its check passes on the branch at the evaluation snapshot.

## Writing a check

Every finding carries one line with its expected output. If it cannot be written in one line,
the finding is too vague to act on, so rewrite it before filing.

A good check runs for a stranger, states a behaviour rather than an implementation, names what
the output should be, and fails today. If it passes on the current branch, there is no finding.

Good: add a file under `skills/` containing a zero-width character and run the check suite,
expecting a non-zero exit that names the file.

Bad: add a Unicode checker to the tools directory. That names a fix, and it can neither pass
nor fail.

## Withheld lines

A source line that holds a credential shape, or a word such as `secret`, `token`, `password` or
`api_key`, is not quoted by the scanner: the excerpt reads `<line withheld>` and the flag keeps its file and
line. Open the line to read it. Every other line is quoted as written. Do not copy a withheld
line into your own evidence, and do not paste a credential you find there into a report. A report
that leaks the secret it found has made the problem worse.
