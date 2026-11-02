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
