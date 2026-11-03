# Contributing

Every change keeps the suite green, twice: once normally, and once without a UTF-8 locale.

```sh
TZ=UTC PYTHONPATH=src:tests python3 -m unittest discover -s tests -t tests
LC_ALL=C LANG=C PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 TZ=UTC PYTHONPATH=src:tests \
  python3 -m unittest discover -s tests -t tests
```

A change to a `SKILL.md`, or to anything an agent reads to decide what to do, lands with a
with-and-without record: the same tasks, before and after, and the result. For a
description, that is `tools/selection_eval.py` run against both versions. In SkillsBench
(arXiv 2602.12670), skills that models wrote for themselves without such a check made results
slightly worse on average.

A new behaviour gets a case in `docs/test-suite.md` with an ID, and a test method named for
that ID. The traceability check fails otherwise, in both directions.

A new detector gets two tests: one where it must fire, and one where a careful repository holds
the same string for a good reason and it must stay quiet. The second one is the harder test to
write and the more important one to have.

If you change the command line, run `python3 tools/gen_cli_docs.py`. If you change anything the
sample dashboard shows, run `python3 tools/gen_example.py`. The suite checks both (D-02, E-02).

`python3 tools/gate.py` is the gate: it runs the suite on every Python from 3.11 to 3.13 it
finds, then again without a UTF-8 locale. Run it before opening a pull request into `main`,
and paste what it prints into the pull request. The `gate` workflow runs the same script on
the pull request.

The standard library only. A dependency needs a reason written down before it lands.

Human-facing text reads like a person wrote it: no em or en dashes in prose, which the suite
checks, and no bold labels on every list item, which it does not.

## Writing docs

The README is the front door: a stranger decides in a minute whether to try the project.

- Order: the project name and a one-line promise, status badges from GitHub, and a figure of the project working, all before the first section. Then the headings "Why", "Features", "Quick start" and "Docs". Under "Why", state the reader's problem with one line of evidence. Number the quick-start steps; run each one and end it on a check the reader can run. Put reference detail behind links.
- Keep paragraphs to at most 60 words, most under 25. Put detail in lists, tables or linked pages.
- Each sentence states one thing a reader can check. Name who does what, and state errors as cause and fix. No filler words, no "etc.", no dashes joining clauses, no "not X but Y", no sales adjectives.
- Explain a technical term the first time it appears, or link to where it is explained. Keep each fact in one place and link to it elsewhere.
- Every number is measured, or marked "not measured" with the command that would measure it. Name the source of each claim, and keep observed, reported and planned behaviour apart.
- Use at least two distinct rendered figures that answer different questions, in one style. Badges, logos and repeated images do not count. Give each figure labels, alt text and a caption stating its conclusion and limits; colour never carries meaning alone. Use animation when motion explains the task. Keep each diagram as one plain-text SVG in the repository, edited directly, with system fonts and no external resources; update any derived image when its SVG changes. Never paste diagram source or ASCII boxes into the README.
- Check what each figure shows against the source revision, and look at it at reading size. Record both checks; keep unperformed checks pending.
- Keep the status, the key evidence and the main limits next to the claims they qualify. Never include secrets, tokens, personal data or paths outside the project.

Before opening a pull request, run `python scripts/readme_lint.py README.md`; CI runs it on every pull request. Passing the lint does not mean the README follows every rule above. A reviewer checks every rule above and that links open without signing in. Then someone unfamiliar with the project, without help, says its audience, problem and status within a minute, and after reading, its input, output, the decision it supports, the first action, the evidence and the main limits, and explains the figures. Record their answers and what they misread, fix it and ask again. Keep the GitHub sidebar current: description, a working website or docs link, 5 to 10 relevant topics, a social preview image, and a release for each published version. If the lint rejects correct text, open an issue about the lint; do not rewrite correct text to pass it.
