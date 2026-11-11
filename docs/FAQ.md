# Questions

## Does it run the project it screens?

No. It reads files and makes read-only git queries, with the project's own git settings that start programs overridden (case S-26). No project script, install step or test is run, and nothing is sent anywhere. Cases G-03 and G-09 in [test-suite.md](test-suite.md) check the no-network part.

## Is a project with no flags safe?

No. It means these checks found nothing in the files. The tool cannot see package registries, accounts, runtime behaviour or deployed versions, and [LIMITS.md](LIMITS.md) lists the rest.

## Does a high band mean the agent works well?

The tool never runs an agent, so it cannot say how well one performs. The bands (blocked, review, shortlist, screened) order your attention. They do not rank quality and nobody is disqualified by one.

## How accurate is it?

Accuracy is not measured and no benchmark exists. Case F-01 stays open until a person has read every flag from a real cohort. See [LIMITS.md](LIMITS.md) for the one field run and what it does and does not show.

## A flag shows `<line withheld>`. Where is the text?

The line holds a credential shape or a word such as `token`, so the card keeps the file and line and leaves the text out. Open the file at that line. A credential in a format the tool does not list can still reach a card, so read a card before you share it. [SECURITY.md](../SECURITY.md) has the rules.

## Can I silence a flag?

A project's `.scanignore` changes no flag, cap or band unless the person screening passes `--honour-ignore` for that one project. When the file holds at least one pattern, the card reports the file, its patterns (only path-shaped ones print) and how many files they match; an empty, comment-only, overlong or symlinked file produces no signal. Under `--honour-ignore` the file can lower `secret-in-tree` and some other critical flags to information; they stay listed and the `verdict` command still counts them at their original severity. `--no-ignore` is accepted and does nothing.

## Does it need a model or an account?

No. It runs on the Python standard library with no network call and no model.

## Can I use it on many projects?

Yes. `quiet-counsel screen ./submissions/* --corpus ./corpus --out ./cards` screens each one and `quiet-counsel dashboard ./cards/*.json --out cohort.html` builds one page. The corpus is optional and is used to find copied content.

## How does it compare with other tools?

[COMPARISON.md](COMPARISON.md) lists what neighbouring tools need in order to run and what they cover. It compares no accuracy.

## How do I report a wrong flag or a problem?

Open an issue at `https://github.com/sourav-patra/quiet-counsel/issues`. For a security problem, follow [SECURITY.md](../SECURITY.md).
