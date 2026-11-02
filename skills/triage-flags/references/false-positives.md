# False positives, and how the detectors already handle them

Each class below was found on a real, clean repository during testing. The detectors screen
out the first group already. The second group still gets through, and needs a person.

## Already screened out

| detector | what used to match | how it is excluded now |
|---|---|---|
| text aimed at the evaluator | security guidance quoting the attack it defends against | lines in a defensive context, or quoting the phrase, are skipped |
| installer pipes to a shell | a denylist entry naming the command it blocks; a test string | only lines that would execute count, outside test and example paths |
| hidden characters | Persian and Arabic zero-width non-joiners; a byte-order mark; a sanitiser inserting the character on purpose | the typographic set is excluded; a leading byte-order mark is stripped; defensive context is skipped |
| credentials | test fixtures and documented placeholders | reported as information, never as critical |
| copyleft in a permissive tree | prose naming the GPL, such as a setup wizard's question | only licence files and SPDX headers count |
| third-party text | a guide showing the source-line template | a URL or licence with placeholders declares nothing; prose is never read |
| third-party text | a closed project marking its own skills proprietary; a `source:` field in a YAML registry | restrictive terms count only with a named source or under an open root licence; source lines count only in a file's header, never in data files |
| writes to host configuration | a doc comment or guide naming `AGENTS.md` or a settings file; a script that only reads `CLAUDE.md` | only code lines that write count, never comments, docs or test paths; a confirmation, dry run or opt-in flag in the same file lowers it to a warning |
| stale instructions | an owner/repo name such as `someone/tool`, a placeholder, a URL, a command inside a code block | a slash counts as a path only when its first segment is in the tree; a bare file name counts only when no file of that name exists anywhere; placeholders, URLs and fenced code are skipped |
| provenance | a shallow clone looking like a squashed import | history is not measured on a shallow clone |
| inventory claims | "works with 15 agents", a compatibility claim | read as compatibility, never as a count |

## Still gets through, and needs a person

- A credential-shaped string outside test paths that is in fact a documented example. The
  path decides the severity, so a real example in `src/` still reads as critical.
- Evaluator-directed text in an unusual discussion context the markers do not recognise.
- A licence file for a component that is not actually redistributed, such as a vendored file
  that is only used in tests.
- Files identical to a corpus file because both copied the same third-party original. The
  source licence then belongs to that original, not to the corpus project.
- Credit kept somewhere the check does not read, such as a credits section in the README.
- A write to a host file behind a confirmation in another file, which reads as ungated.
- An instruction file naming a path the project generates at build time.

## Telling fixture from finding

A fixture sits in a test or example path, is named as a fixture nearby, or is assembled from
fragments. A finding sits in code or configuration that ships, or in text an agent would read
as instruction. When the two look the same, the path and the neighbouring lines decide.
