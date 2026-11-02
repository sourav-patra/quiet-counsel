# How it compares

Read on 2 November 2026, from each project's raw README or licence file on `raw.githubusercontent.com` (at the tag named in the row, where one is given), and from Factory's documentation page as served (HTTP 200 on that date, with the nine pillars, five levels and 80% gate in its text). These projects change often, so follow the links and check the page before repeating anything here. Rows for projects that were not opened on that date were removed.

This tool reads one repository, or a hundred, without running anything, and reports what the files contain and the file and line, command or commit behind each number. The projects below answer nearby questions, and what each one needs in order to run is the place to start comparing.

## What each one needs

| Project | What it does | What it needs, as its page states it |
|---|---|---|
| This tool | Reads a repository and reports what it contains, with evidence for each number | Python 3.11 or newer and the standard library. No network call and no model (cases G-03 and G-09 in [test-suite.md](test-suite.md)) |
| [SkillOpt](https://github.com/microsoft/SkillOpt) | Improves one skill document for a frozen agent: an optimiser model turns scored rollouts into edits | Live model runs for training, and a score for each rollout. A candidate edit is accepted only when it strictly improves a held-out validation score. MIT |
| [SkillSpector](https://github.com/NVIDIA/SkillSpector/blob/v2.13.2/README.md) (tag v2.13.2) | Scans an agent skill for security problems | Its README says LLM analysis is the default and file contents are then sent to the configured provider; `--no-llm` keeps contents local. The dependency check sends dependency names and versions to OSV.dev "even with `--no-llm`", and needs outbound HTTPS to `api.osv.dev` for live vulnerability data; when that is unreachable it uses a small built-in fallback list |

SkillOpt starts from a skill whose output you can score. This tool starts from a repository and needs no model run.

## Repository scorers closest in purpose

These score how ready a repository is for coding agents. This tool asks what an agent project contains and what looks wrong in it, so the questions differ even where the inputs match. The table gives requirements and coverage as each page states them. It compares no accuracy and gives no ranking.

| Project | What it covers | What it needs |
|---|---|---|
| [AgentReady](https://github.com/ambient-code/agentready) | Scores a git repository across 13 categories (documentation, testing and CI, dependency management, security and others) out of 100, with a Platinum, Gold, Silver or Bronze level | Python and pip. The page gives no runtime network or model requirement. MIT |
| [Ready Agent 1](https://github.com/tjboudreaux/ready-agent-1/blob/main/README.md) | Levels across 9 pillars, each gate clears when 80% of its applicable checks pass and every gate below it is cleared. Its README says every check cites the file, commit or GitHub setting behind it | Python 3.11 or newer, no runtime dependencies, Linux and macOS. Offline by default; GitHub checks and command execution are opt-in; an agent layer is advisory. MIT |
| [Factory Agent Readiness](https://docs.factory.com/web/agent-readiness/overview) | Five levels across 9 pillars, each level unlocked by passing 80% of the previous level's criteria | Run through the Factory app, the Droid CLI or an API. The page does not say whether an account is required |
| [AgentRC](https://github.com/microsoft/agentrc/blob/main/README.md) | Scores AI readiness across 9 pillars and 5 levels, and generates and maintains instruction files | Node.js 22 or newer. GitHub sign-in or a token, and the Copilot CLI for generation. Marked experimental. MIT |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard/blob/main/README.md) | Checks of supply-chain practice, each scored 0 to 10 and combined into a weighted average. None of the checks the page lists is specific to agents | A GitHub or GitLab token for higher rate limits; Go for the standalone CLI, or a Docker image |

Google's [Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model) has fresh-context subagents review a design before code is written, and its drift report compares checked-in documents with source code; it runs inside a coding agent. This tool reads a repository with scripts alone and cites what it finds. We read its README and design notes on 2 November 2026 and have not run it, so no comparison of results exists.

## Dated notices

None of the tools we examined publishes dated notices tied to named repository checks. We read READMEs and selected source, and four tools remain unknown on this: agent-readiness (harry), AgentRC, Factory and OpenHands' `agent-readiness-report`. Corrections are welcome at `https://github.com/sourav-patra/quiet-counsel/issues`.

The nearest neighbours publish records of a different kind. [skill-advisories](https://github.com/Akshay7273/skill-advisories) is an open advisory database for agent skills, plugins and MCP servers, in an OSV-style format. The [Orca AI Incident Archive](https://github.com/Continuum-AI-Corp/Orca-AI-Incident-Archive) is an open database of real-world AI agent incidents. The CISA [Known Exploited Vulnerabilities catalog](https://www.cisa.gov/known-exploited-vulnerabilities) lists vulnerabilities exploited in the wild. [MITRE ATLAS](https://github.com/mitre-atlas/atlas-data) is a knowledge base of adversary techniques against AI systems. This tool's notices are in [NOTICES.md](NOTICES.md).

## Where to use something else

For the security of a single skill or agent configuration, use a dedicated scanner. The safety sweep here is a coarse pass across many projects and goes nowhere near that depth.

For supply-chain practice in general, use OpenSSF Scorecard.

To find out whether a project's code works, run its tests. Nothing here runs them.

## Where this one is weak

Accuracy is not measured and no benchmark exists yet. Case F-01 in [test-suite.md](test-suite.md) is the field check that would measure the false-positive rate per detector. Copy detection matches identical content, so a rewritten copy passes unseen. The rubric's anchors are one evaluator's judgement except where [RUBRIC.md](RUBRIC.md) names an outside standard. One person maintains it.

Not checked: no tool was installed or run; the Factory page was read as served HTML with its text extracted by a script; the four tools named above as unknown were checked only at the pages the table links; rows for projects not opened on the date above were removed, not re-checked.
