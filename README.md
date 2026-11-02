# Quiet Counsel

Read an agent project's repository, work out what kind of project it is, flag what looks wrong,
and show the file and line, or the command, behind each number. The result is one HTML page you
can open, email or commit.

It runs locally on the Python standard library (3.11 or newer). It makes no network call and
calls no model.

> Status: v0.1.0 is built and tested. Accuracy is not measured and no benchmark exists yet.

```sh
pip install "git+https://github.com/sourav-patra/quiet-counsel@v0.1.0"
quiet-counsel classify ./project
quiet-counsel screen ./submissions/* --corpus ./corpus --out ./cards
quiet-counsel dashboard ./cards/*.json --out cohort.html
```

`quiet-counsel sample <dir>` writes a synthetic project with five planted problems, and
[examples/sample-dashboard.html](examples/sample-dashboard.html) is the page built from it.

To check the no-network claim, run cases G-03 (no module imports a network library) and G-09 (a
screen with every socket refused gives the same card byte for byte, with the clock fixed):

```sh
TZ=UTC PYTHONPATH=src:tests python3 -m unittest discover -s tests -t tests -k test_G03 -k test_G09
```

On Windows PowerShell, run the same two cases from the repository root with `$env:TZ='UTC'; $env:PYTHONPATH='src;tests'; py -3 -m unittest discover -s tests -t tests -k test_G03 -k test_G09`.

## What it cannot see

It reads files in one directory tree. It cannot see stolen accounts, package registries, extension
marketplaces, runtime behaviour or deployed versions. It does not run a project's tests, does not
guess whether a person or a model wrote the code, and lists licence text without ruling on it in
law. Copy detection matches identical content against the corpus you supply and misses a
rewritten copy.

[docs/NOTICES.md](docs/NOTICES.md) records eight 2026 incident patterns and what this tool does
and does not look at for each. Of the seven that are not the hackerbot-claw campaign, five (the
OpenAI and Hugging Face breach, the LiteLLM 1.107.0 release, the Cursor extension, the PHP flaw and
the Node.js flaw) are marked `invisible`: the affected material is not in a repository tree, or
depends on a version the tool does not compare against an advisory. For the other two, the keyv
worm and the fake audit workflow, the files appear with the compromise, so a screen of the affected repository had
nothing to find beforehand; the checks can list them afterwards, to help a person triage. No detection rate exists for
any of them.

## What is measured, and what is not

- Flags about a file cite its path and line. Flags about history or a missing file cite a command
  or a commit. `tools/check_evidence.py` confirms that each cited line exists and either holds the quoted
  text or is a line the scanner withholds (the excerpt reads `<line withheld>`: the line holds a
  credential shape or a word such as `token`, and you open it to read it). On this repository's
  own tree it reports 3 flags, all 3 citing a file and line (13 evidence items: 7 with the quoted
  text on the line, 6 withheld lines, 0 broken, 0 differing). Of the 24
  numeric signals on a card, 0 cite a file and line; the rest cite the command that
  produces them. Reproduce with `python3 tools/check_evidence.py . --list`.
- Accuracy is not measured and no benchmark exists. Case F-01 in
  [docs/test-suite.md](docs/test-suite.md) stays open until a person has read every flag from a
  real cohort.
- Field run: one run by the author on 2 November 2026, of 50 public agent repositories drawn from a personal catalogue of agent tools, ordered by a
  hash of each name, taking the top 50 of that order under 150 MB, screened with this version's checks. There
  were 0 screen errors and 5 warnings from the checks added for the incident notices (4 `install-time-script`,
  1 `open-time-hook`). In all, 4 critical, 31 serious, 36 warning and 34 information flags. The data-out
  and untrusted-code checks raised nothing, so the one place they have fired is test fixtures. The
  repository list is withheld so as not to name other people's projects, so a reader cannot reproduce this run; the
  aggregates are in [docs/field-run-2026-11-02.json](docs/field-run-2026-11-02.json). No person has read every flag.
- A project's own `.scanignore` can lower `secret-in-tree` and some other critical flags to
  information. They stay listed, `--no-ignore` restores them, and the `verdict` command still counts a flag lowered this way at its original severity.

Every flag is a finding for a person to rule on. The tool orders projects and cites evidence. It
disqualifies nobody, and a high score does not mean a project is safe or that an agent will do
better in it.

## Integrity checks

Text addressed to the evaluator is reported and never acted on. A line the tool judges to be quoted
or defensive, such as a security guide quoting the attack it defends against, does not stop
scoring, and every such line is listed as `quoted-evaluator-text` at information level so a reader
can check the judgement. A determined author can still write the surrounding words on purpose.
Hidden characters, licence text, copied files and README claims have their own checks. All of it is
in [docs/INTEGRITY.md](docs/INTEGRITY.md).

## Beside the Elephant-Goldfish Model

Google's [Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model) has fresh-context subagents review a design before code is written, and its drift report compares checked-in documents with source code; it runs inside a coding agent. This tool reads a repository with scripts alone and cites what it finds. We read its README and design notes on 2 November 2026 and have not run it, so no comparison of results exists.

## Using it from an agent

Three skills in `skills/` (`screen-cohort`, `triage-flags`, `review-project`) and three roles in
`agents/` (screener, reviewer, verifier, none of which can write to the project it reads).
[AGENTS.md](AGENTS.md) holds the instructions every host reads.

```sh
python3 install.py --dest <your host's skills directory> --agents-dest <its agents directory>
```

[docs/AGENT-INTERFACE.md](docs/AGENT-INTERFACE.md) lists the directories common hosts read. The
installer never deletes anything and never overwrites without `--force`. The tool screens itself
in its own test suite (case H-16) and must raise no critical or serious flag against its own tree.

## More

- [docs/RUBRIC.md](docs/RUBRIC.md): the 16 dimensions and what a 10 and a 0 look like.
- [docs/ARCHETYPES.md](docs/ARCHETYPES.md): how a project is classified from evidence, not its name.
- [docs/SCREEN-MODE.md](docs/SCREEN-MODE.md): the triage pass and the deep pass.
- [docs/cli.md](docs/cli.md): every command and flag.
- [docs/COMPARISON.md](docs/COMPARISON.md): what neighbouring tools need and cover.
- [docs/NOTICES.md](docs/NOTICES.md): dated pattern notices. One person maintains them and claims
  no standing over anyone. Corrections go to `https://github.com/sourav-patra/quiet-counsel/issues`.
- [docs/test-suite.md](docs/test-suite.md): every case with its ID. The suite follows the method
  at [why-bureau](https://github.com/sourav-patra/why-bureau) and fails if a case loses its test.
  `python3 tools/gate.py` runs it locally and in `.github/workflows/gate.yml`.
- [RELEASING.md](RELEASING.md): branches, tags and how to cut or install a release.

## Licence

MIT. See [LICENSE](LICENSE).
