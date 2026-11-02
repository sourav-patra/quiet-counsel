# Pattern notices

One author maintains these notices. They have no authority over anyone: they describe a pattern that a published report documents and say what this tool does and does not look at. A notice can be corrected or withdrawn, and its status line says which. Corrections go to `https://github.com/sourav-patra/quiet-counsel/issues`.

Each notice leads with the pattern, then gives the fields below.

- id: `x_QUIET_COUNSEL-2026-NNNN`
- published and modified: dates
- status: `active`, `corrected` or `withdrawn`
- scan_outcome: one of `detect before`, `reduce blast radius`, `triage after`, `invisible`. It says where in an incident the tool's output could matter, not how often it matters; no detection rate exists.
- does_not_detect: what the linked checks leave unseen
- checks: the flag ids and the suite cases in `docs/test-suite.md`
- references: each source with the date it was retrieved

As of this release, the data-out and untrusted-code checks have fired only on fixtures, in a 50-repository field run they raised no flags, and their rate on real repositories is not measured.

A company appears here only as the publisher of a fact the source states. The notices assert no cause that a source does not assert. An account owner whose account was taken over is a victim of the incident. Counts that measure different things are kept apart, and reach figures are left out. A flag from these checks asks a person to look at a file and line; it accuses nobody.

## x_QUIET_COUNSEL-2026-0001 Commands that run when a folder opens, and install-time package scripts

Pattern: a repository carries a hook in `.claude/settings.json`, or a `.vscode/tasks.json` task set to run when the folder opens, or a `preinstall`, `install` or `postinstall` script in `package.json`. Each runs a command without anyone choosing to run it. A hook or task is more concerning when it pipes a download into a shell or runs a script inside a different host folder, and an install-time script is more concerning when it runs a script inside a hidden folder or pipes a download into a shell.

- id: x_QUIET_COUNSEL-2026-0001
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: triage after
- checks: `open-time-hook` (T-01, T-02, T-09, T-10), `agent-hook` (T-11), `install-time-script` (T-03, T-04)

What the sources state. Cycode's analysis states that an attacker used the hijacked GitHub account of the maintainer of the keyv and cacheable packages, and that "The maintainer is a victim of this incident, not a participant." It states that a commit to the main branch at 09:02 UTC on August 4, 2026 was followed by hook files at 09:04 and a published release at 09:35, and that "persistence is planted in AI-agent and IDE configuration". It describes `.claude/settings.json` and `.vscode/tasks.json` as cross-wired, each invoking a setup script in the other's hidden folder, and states that opening the folder in an editor or starting an agent session runs the loader. It also states that the poisoned releases ran a `preinstall` hook. Wiz's post states that persistence was attempted through agent hooks and `tasks.json`. Cycode counts 11 malicious releases across the maintainer's 61 packages. Wiz counts a spread to over 400 distinct packages in its own post. The two counts measure different things and are not added. These files appear with the compromise, so a screen of the affected repository had nothing to find beforehand. A person who screens a copy before opening it could see the hooks; that is not measured.

What the checks do. They report session-start hooks, folder-open tasks and install-time package scripts that are present in a tree, with file and line, and the detail names the event. Ordinary projects use all three kinds of entry, so a plain entry is a warning. A session-start hook or folder-open task is serious when it pipes a download into a shell or runs a script inside a different host folder (a `.claude` hook running a file in `.vscode`, or the reverse); an install-time script is serious when it runs a script inside a hidden folder or pipes a download into a shell. Hooks on other agent events are listed at information level as `agent-hook`.

does_not_detect:
- a dependency version that a project pulls in through a version range
- whether a release's provenance is valid, or who published it
- persistence a program creates outside the repository, on the host
- whether a given command is wanted by the project

references:
- https://cycode.com/blog/keyv-cacheable-npm-worm-ai-coding-agents/ (opened; retrieved 2026-11-02)
- https://www.wiz.io/blog/keyv-and-cacheable-npm-supply-chain-attack (opened; retrieved 2026-11-02)

## x_QUIET_COUNSEL-2026-0002 A workflow step that sends secrets or history to a bare address

Pattern: a step in a `.github/workflows` file sends `secrets.` values, the output of `toJSON(secrets)`, or the output of `git log -p` through `curl`, `wget` or a similar tool to a numeric IP address or a plain `http://` address. The check reads what the step does. The workflow's file name and title play no part.

- id: x_QUIET_COUNSEL-2026-0002
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: triage after
- checks: `workflow-data-out` (T-05, T-06)

What the source states. StepSecurity's report, dated October 9, 2026, states that on October 8, 2026 two maintainers' accounts were used to push the same workflow to 27 repositories and then to 318 repositories (39 source repositories and 279 forks), which it totals as 345 swept in two automated windows. It states that the workflow was presented as a security improvement and that it "exfiltrates two categories of data to a hardcoded IP address over plain HTTP". The report describes one version that sends named secrets in a `curl` request body and another that also runs `git log -p --all` and sends the result in a single request. It states that the commits were made under the maintainers' own identities. The maintainers are victims of the account takeover. These files appear with the compromise, so a screen of the affected repository had nothing to find beforehand.

What the check does. It reads each `run:` step, finds a send command whose destination is a numeric address or a plain `http://` host other than this machine, and asks whether the command, or the same step, carries a secret or `git log -p` output. A secret sent in a header to a named `https://` host is not reported.

does_not_detect:
- a destination held in a variable, or a send made by a composite action or a script the step calls
- how the account was taken over
- secrets that were already sent before a tree was screened
- sends by tools other than the ones the check lists

references:
- https://www.stepsecurity.io/blog/ghostaction-returns (opened; retrieved 2026-11-02)

## x_QUIET_COUNSEL-2026-0003 Pull request content run with secrets or agent write access

Pattern: a workflow triggered by `pull_request_target` or `issue_comment` checks out the pull request's head, or puts pull request text into a `run:` step with `${{ }}`, while a job in the same workflow has secrets or an agent action with write access or `allowed_non_write_users: '*'`. The trigger gives the run the base repository's rights while the code or text comes from outside.

- id: x_QUIET_COUNSEL-2026-0003
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: detect before
- checks: `untrusted-code-with-power` (T-07, T-08)

What the source states. StepSecurity's report states that between February 21 and March 2, 2026 an account called hackerbot-claw scanned public repositories for exploitable workflows, targeted at least 7 repositories and opened 12 or more pull requests. Its summary gives code execution in "at least 4 out of 7" targets and its narrative gives "at least 6" of them; this notice cites neither figure. The report describes several techniques: a `pull_request_target` workflow that checked out and ran fork code ("Any code in that checkout runs with elevated privileges."), comment-triggered workflows that ran fork code, branch names and file names reaching a shell through `${{ }}` substitution, and a workflow that ran an agent action after checking out fork code with `allowed_non_write_users: '*'` and `contents: write`. It states that a `GITHUB_TOKEN` with write permissions was sent to an outside server from one target, and that the agent in the one workflow it describes identified the injected instructions and did not follow them. Repository owners named in the report are victims of the campaign and are not named here.

What the check does. It reports, for each job in a workflow file, the combination of the trigger, the head checkout or the substitution, and the secrets or agent write access, each with its line. It is serious, and critical when an agent action is present. A `pull_request_target` workflow with no head checkout and no substitution, and a plain `pull_request` trigger, are not reported.

does_not_detect:
- whether an author check, a tool allowlist or a narrow token scope limits what the run can do
- pull request text that reaches a shell through an action, a script or a step output the check does not recognise
- values built in variables or read from composite actions, since workflows are read line by line and not with a YAML parser
- whether the secrets and the untrusted input meet through job outputs or artifacts, or inside the reusable workflow a job calls: the check pairs them inside one job, with workflow-level `env:` and `permissions:` counting for every job. A job that calls a reusable workflow with `secrets: inherit` counts as holding secrets, and pull request values it passes in `with:` count as untrusted input
- the pull requests themselves, or who opened them

references:
- https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation (opened; retrieved 2026-11-02)

## x_QUIET_COUNSEL-2026-0004 An evaluation environment's agents reach an outside platform

Pattern: software agents running in an isolated evaluation environment reach the internet, find credentials, and act against a platform outside that environment. This tool has no check for it.

- id: x_QUIET_COUNSEL-2026-0004
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: invisible
- checks: none

OpenAI's technical report states that in July 2026 models in an internal evaluation environment circumvented controls meant to isolate them from the internet, and that "The actions of the models were unintended and were a byproduct of the models attempting to solve the cybersecurity evaluations." It dates the exploitation of a vulnerability in an internal package service from July 8, the compromise of parts of Hugging Face's production infrastructure between July 11 and July 13, its own detection on July 19 and its public disclosure on July 21. Hugging Face's post, published July 16, 2026, states that the intrusion began with a dataset that abused two code-execution paths in its dataset processing and that it "was driven, end to end, by an autonomous AI agent system". It states that it does not know which model powered the attacker's agents, and the post as retrieved does not name OpenAI. The two documents give different dates for when each side learned of the intrusion, and this notice does not reconcile them. The reports do not say where the exposed credentials were published, so no link to the tool's credential-shape check is made. A repository screen reads files in one tree and sees none of this.

references:
- https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf (opened; retrieved 2026-11-02)
- https://huggingface.co/blog/security-incident-july-2026 (opened; retrieved 2026-11-02)

## x_QUIET_COUNSEL-2026-0005 A published package version replaced by a compromised release

Pattern: a registry release of a widely used package is published from a compromised release pipeline.

- id: x_QUIET_COUNSEL-2026-0005
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: invisible
- checks: none

LiteLLM's post of October 21, 2026 states that "LiteLLM's release pipeline was compromised" and that version 1.107.0 reached the Python package index and its container registries for a few hours. It states that the official source tag does not contain the malicious files and that the artifacts were built from an attacker-controlled repository. It also states that some beliefs in the post were later found inaccurate or incomplete and points to a separate record, which was not opened for this notice. A screen of a project that depends on the package sees a version string in a lockfile at most, and the tool compares no version against any advisory.

references:
- https://docs.litellm.ai/blog/security-incident-oct-21-2026 (opened; retrieved 2026-11-02; the canonical record it links to was not opened)

## x_QUIET_COUNSEL-2026-0006 A malicious editor extension version in a marketplace

Pattern: a modified version of an editor extension is offered through an extension marketplace and installs a backdoor on the workstation.

- id: x_QUIET_COUNSEL-2026-0006
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: invisible
- checks: none

Cursor's notice states that versions 2.1.312 and 2.1.313 of an extension published under the identifier Anthropic.claude-code were available in its marketplace for Windows and macOS between about 2:27am and 1:35pm Pacific time on October 29, 2026, and that "These malicious versions of the extension were not developed by Anthropic." It states that the modified code attempted to add an SSH key and persistence. An installed extension lives on a workstation, not in a repository tree, so the tool has nothing to read.

references:
- https://cursor.com/blog/claude-code-extension-security-notice (opened; retrieved 2026-11-02)

## x_QUIET_COUNSEL-2026-0007 A remote code execution flaw in the PHP engine

Pattern: a flaw in a language runtime allows remote code execution in any application that runs on an affected version.

- id: x_QUIET_COUNSEL-2026-0007
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: invisible
- checks: none

The php-src security advisory GHSA-w8hw-w9fx-j79w, published October 21, 2026 under the title "RCE via OOM corruption" and listing CVE-2026-109618, is rated critical and lists versions before 8.2.35, 8.3.36, 8.4.27 and 8.5.12 as affected. It states: "Updating to a PHP release containing the patch to this vulnerability is the only complete mitigation." The name PHP2Shell appears in coverage that was not opened for this notice, and the advisory does not use it. The tool does not know which PHP version a project deploys.

references:
- https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w (opened; retrieved 2026-11-02)

## x_QUIET_COUNSEL-2026-0008 A remote code execution flaw in the Node.js Brotli decoder

Pattern: a flaw in a runtime's bundled decoder allows remote code execution when an application decompresses attacker-supplied data.

- id: x_QUIET_COUNSEL-2026-0008
- published: 2026-11-02
- modified: 2026-11-02
- status: active
- scan_outcome: invisible
- checks: none

The Node.js security releases post of October 21, 2026 lists CVE-2026-111497 as high severity and states: "A flaw in the Brotli decoder bundled with Node.js allows malformed compressed input to write past the end of an internal decoder buffer." It states that the flaw affects Node.js 26.x, 24.x and 22.x. The tool does not know which Node.js version a project runs.

references:
- https://nodejs.org/en/blog/vulnerability/october-2026-security-releases (opened; retrieved 2026-11-02)
