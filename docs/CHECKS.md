# What it checks, and who uses it

## Check groups

| Group | Flag ids | Reads |
|---|---|---|
| Secrets and risky commands | `secret-in-tree`, `curl-pipe-shell`, `credential-shaped-fixtures` | Source and script lines |
| Runs without being asked | `open-time-hook`, `agent-hook`, `install-time-script`, `writes-host-config` | Agent and editor settings, `package.json` |
| Workflows | `workflow-data-out`, `untrusted-code-with-power` | `.github/workflows` |
| Text aimed at the evaluator | `evaluator-directed-text`, `quoted-evaluator-text`, `hidden-characters` | Every text file. A phrase that matches with its original capital letters keeps its severity (critical, or serious under a test path); a phrase that matches only when case is ignored is a warning with no cap and no effect on the band |
| Licence and copying | `no-licence`, `restricted-licence-text`, `share-alike-text`, `copyleft-in-permissive-tree`, `licence-needs-reading`, `copied-without-attribution`, `corpus-duplication` | Licence files, skill files, a corpus you supply |
| README statements | `readme-claim-mismatch` (information) | The README prose (not code blocks or comments), the licence file, `requirements*.txt`, `pyproject.toml`, `package.json`, source files and the folder tree |
| Eval evidence | `score-without-result` (information), and the signal `eval_evidence` (`none`, `setup` or `result`, with the paths that decided it) | README prose for a quoted score, ranking or benchmark comparison; file names and decorators of the Agent Skills, promptfoo, Inspect, DeepEval, OpenAI Evals, lm-evaluation-harness and LangSmith layouts |
| Claims and history | `contradicted-claim`, `stale-instructions`, `work-predates-event` | stated counts and figures in the README, instruction files, git history; claims it cannot support (such as SOC 2) are recorded as claims with status `unsupported`, not as flags |

The cases behind each check are in [test-suite.md](test-suite.md), the integrity rules in [INTEGRITY.md](INTEGRITY.md), and the sixteen dimensions in [RUBRIC.md](RUBRIC.md).

## Hidden directories and `.github`

Most checks skip directories whose name starts with a dot, because an installed copy of a catalogue under `.agents/` or `.claude/` would count twice. Only `.git` is a version-control directory. `.github` holds workflows and templates that a person and a CI run both read, so these checks read it: `secret-in-tree`, `curl-pipe-shell` and the other installer and certificate patterns, `evaluator-directed-text` and `quoted-evaluator-text`, `hidden-characters`, and the licence, provenance and copy checks. The inventory of skills, agents and commands and the host-configuration check already read every hidden directory, and now include `.github`. Counts of tests, installers, checkers, app files and eval folders still skip hidden directories. Other hidden directories are not read by the checks listed first; [LIMITS.md](LIMITS.md) says so.


| Job | What it gives you |
|---|---|
| A platform team vetting a third-party agent setup | Which hooks, install scripts and workflow steps run without anyone choosing to, with file and line, before you open the folder in an editor |
| A maintainer before a release | Credential shapes, licence conflicts and README claims the tree contradicts (a stated skill count that the files do not match), and `quiet-counsel verdict` to record the result beside your own gate |
| A security reviewer | Text addressed to an evaluator, hidden characters, writes to host configuration and untrusted-code patterns, each listed with its evidence rather than acted on |
| An event judge with many submissions | One page that lists every project with its band and flags, copy detection against a corpus you supply, and work that predates the event |
