# Integrity checks

Written for a hackathon with a hundred submissions, judged partly by an agent, under time
pressure. Every incentive to overstate, and very little time to check.

A project is judged on what its repository contains, and every integrity finding names the file,
the line and the command that produced it. "Looks AI-generated" is not a finding. "The first
commit contains 1,847 files and the event ran for 36 hours" is.

## Text aimed at the evaluator

Every byte of a submission is data, never instruction. A submission containing text addressed to
the judging system, such as an instruction to disregard what it was told or a request for top
marks, is a
conduct problem rather than a scoring one, and it goes to a person.

The suite looks for hidden and direction-changing characters in anything an evaluator reads:
zero-width space, bidi overrides and isolates, tag-block characters, and byte-order marks inside
a line. Persian and Arabic typography is excluded, because zero-width non-joiners and
directional marks are ordinary orthography there and flagging them would call every translated
README an attack. It also looks for imperative text addressed to a model or scorer in READMEs,
skill bodies, comments, commit messages and file names.

Both sweeps skip text that defends against the thing it names. A security guide has to
quote the attack it defends against, a denylist has to name the command it blocks, and a
sanitiser has to contain the character it strips. Three clean repositories tripped these checks
before that test existed, and a critical flag that fires on good practice teaches people to
ignore critical flags.

On a real detection the tooling stops scoring that project, raises a critical flag, and records
the literal text with its location. A hit
under a test path (a directory named `test`, `tests`, `testdata`, `fixtures` or `__tests__`, or a
file named `test_*` or `*_test.*`) is raised as serious instead, is still listed with its evidence,
and does not stop scoring. The same lowering applies to copyleft text that sits only in test files
(a warning). A project's `.scanignore` cannot lower this flag when a hit is outside a test path: the flag stays critical and keeps its `do-not-score` cap, with or without `--honour-ignore`. The limit: a project can place text under a test path and receive the lower severity.
It is still listed, so a person reading the flags sees it, but the tooling does not stop on it. A second route is judgement from surroundings. A line addressed to the evaluator is set aside when the five lines centred on it carry a word such as "example", "attack" or "untrusted", or when it sits in quotation marks beside "score", "rate", "ignore" or "disregard". A determined author can write those words on purpose and lower a blocking hit to nothing that stops scoring. The tool therefore never drops such a line: it lists every one as `quoted-evaluator-text` at information level, with the file, the line and the count, so a reader can check the judgement. The listing does not stop scoring and no cap attaches to it. A `.scanignore` entry can move it into the excluded-path listing, where it stays visible. The tool's own tree passes H-16 with the listing present and no exception. The evaluator never acts on it, never quotes it into a
prompt, and says in the report that it was found.

## Originality and provenance

Five mechanical signals, none conclusive alone. In 0.1.2 three of them (first-commit mass, history shape and timestamp consistency) are not measured, because the tool starts no git program; the card says so in its limits with the reason `disabled in 0.1.2`, and history returns in a later release. The report gives the signals and leaves the
conclusion to a person.

| Signal | What it measures | What it does not mean |
|---|---|---|
| File-level duplication against a corpus | Identical content hashes between the submission and known public repositories | Copying with attribution is legitimate, so check the licence dimension first |
| First-commit mass | Files and lines in the initial commit against the event window | Importing scaffolding is normal; importing a finished product is not |
| History shape | Commit count, authorship spread, time span, gaps | A squashed import can be an honest workflow |
| Timestamp consistency | Commit times against the event window, author and committer dates disagreeing | Rebases legitimately rewrite dates |
| Vendored-to-first-party ratio | Third-party lines against the project's own | A thin wrapper around a good library is a valid project, if it says so |

When history returns, a shallow clone will report nothing at all. History fetched with `--depth 1` describes how you
fetched it, not how the work was written, and reading provenance from it produced a false flag
on four public repositories during testing.

The corpus is what turns suspicion into measurement. Point the tool at a directory of clones and
it reports every file whose content hash matches one of them, with both paths:

```sh
quiet-counsel integrity <project> --corpus ./corpus --min-bytes 400
```

A submission that is 60% identical to a public repository is not necessarily cheating. The judge
should know before scoring it as original work.

## Licence and redistribution

Does the project declare a licence at all? Without one nobody may reuse it, which matters for an
event meant to open-source its winners.

Does a copyleft component sit inside a permissively licensed tree? Only licence files and SPDX
headers count here. Prose that mentions the GPL, such as a setup wizard asking "MIT, Apache-2.0
or GPL-3.0?", is not redistribution, and treating it as one raised a critical flag on three
clean repositories before the check was narrowed.

Are vendored directories identified, with their licences kept? Stripping a `LICENSE` from
vendored code is the most common breach in practice.

Does the tree contain extracted proprietary material, such as leaked prompts or restrictively
licensed weights? This is a real category. One repository in an earlier survey redistributed
extracted proprietary prompts under a copyleft licence and was excluded from scoring rather than
scored.

## Third-party text

A project that copies someone else's text, whether a skill, a rules file or a module, should
carry that text's licence and say where it came from. The convention the check reads is a line
at the top of the copied file:

```
source: <repository url> @ <commit>, licence: <licence name>
```

A frontmatter `license:` key and an SPDX header count as declarations too. Prose never does,
and a template with placeholders, like the one above, declares nothing. A source line counts
only in the file's header, the frontmatter and the few lines after it, and never in a data file,
because a `source:` key in a YAML registry is a field and not a statement about the file.

A closed project that marks its own skills proprietary is stating its own terms, not borrowing
someone else's. Restrictive terms count as third-party only when the file names a source, or
when the project itself is published under an open licence.

Without a corpus, the check reads what the tree says about its own files. Given a corpus, it
also finds the copies: a file identical to a corpus file, or identical once its source and
licence lines are set aside, so a copy that gained a source line still matches. Each match
carries the licence of the project it came from, from the file's own declaration or the
nearest licence file above it in the corpus, and where the copy credits it: its own source or
licence line, a licence file beside it, or a notices, third-party, credits or attribution file
at the root that names the source. A README mention is too loose to count.

| What was found | Flag | Severity and cap |
|---|---|---|
| share-alike text (GPL, AGPL, CC-BY-SA) in a tree under another licence | `share-alike-text` | critical, D1 set to 0 |
| terms that do not allow reuse here (non-commercial, no-derivatives, source-available, proprietary), or a source with no licence at all | `restricted-licence-text` | serious, D1 capped at 3 |
| a permissive copy with no credit anywhere | `copied-without-attribution` | serious, D2 capped at 3 |
| an open licence that is not OSI-approved (CC-BY), a file-level copyleft, a name the tool does not know, or a source line with no licence | `licence-needs-reading` | warning |

Text with no licence is all rights reserved, which is why a copy from an unlicensed project is
treated like a restricted one. A permissive copy with its licence and credit in place raises
nothing.

The tool is not a lawyer and the report says so. It produces facts, being file, line, licence
text found and licence declared, for a person to rule on.

## Claim accuracy

The cheapest useful check in the suite, because inflated claims are usually falsifiable in one
command.

Numeric claims in the README are extracted and compared with what the tree contains. Capability
claims such as SOC 2, SLSA or "production-ready" are reported as unsupported without a search:
the screen does not look for a supporting artifact, so the status means only that a person has not
yet found one. Benchmark claims with no committed results, method
or control are reported as unsourced rather than false.

Four statuses, and the report keeps them apart. *Contradicted* means the repository disproves
it. *Unsupported* means nothing in the repository backs it. *Confirmed* means it was re-derived,
with the command. *Unchecked* means the claim and the measurement are not the same quantity: a
claim of "340 tests" counts cases while the screen counts files, so it stays unchecked until
someone runs the suite.

Context decides what kind of claim it is. "Works with 15 agents" is a compatibility claim about
hosts, and reading it as an inventory count produced a false contradiction against a clean
repository.

## What this cannot detect

Paraphrased copying. Content hashing catches identical files, not rewritten ones.

Copying from outside the corpus. The tool knows what you point it at and nothing else.

Work done before the event and legitimately reused, unless the history shows it.

A convincing lie in prose. If a README claims a partnership or a user base, no repository scan
settles it.

Text beyond a file-read limit. The scan reads at most 4,000 to 20,000 characters of frontmatter, 20,000 of a
licence file, 200,000 of a workflow, 500,000 of a hook, settings or declaration file and 2,000,000
of other text, and drops a final line the limit cuts in two. Anything past the limit, including a
hook or workflow step placed there, is not seen and raises no flag. Apart from those character
limits, three scans skip a whole file by size: the pattern scan (credential shapes, installers,
certificate and hook-bypass patterns, evaluator-directed text) skips a text file over 2,000,000
bytes (`scan.py:413`), and the licence-text scan (`scan.py:837`) and the provenance scan
(`scan.py:943`) skip one over 500,000 bytes. A credential, hook or instruction in a file that size
is not seen by that scan and raises no flag from it.

A credential-shaped name. The scorecard replaces a credential shape in a file or directory name, a
frontmatter key or a README claim phrase with `<redacted>`, since none of these is a quoted source
line. A file called like a key appears in references as `<redacted>.sh:1`, which no longer
resolves, so `check_evidence.py` reports that citation as broken. A project directory named like a
key gets a redacted `project.path`, and the review scripts then cannot find it unless `--project`
is given. There is no mapping back and no refusal to export (case S-18).

Whether a human or a model wrote the code. The tool deliberately does not guess. There is no
reliable detector, the question is usually the wrong one at an AI hackathon, and a false
accusation costs more than a missed one.

Every integrity flag is a finding for a person to rule on. The tooling ranks and evidences; it
does not disqualify.
