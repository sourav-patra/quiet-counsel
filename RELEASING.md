# Releasing Quiet Counsel

## Versions

Semantic versioning. Before 1.0, the minor number may carry breaking changes to the scorecard format or the rubric; every breaking change is called out under "Breaking" in CHANGELOG.md, with the migration.

| version | means | gate |
|---|---|---|
| 0.1.0 | first public release: built and tested, not field-proven | `python3 tools/gate.py --release X.Y.Z` passes: the suite on Python 3.11, 3.12 and 3.13, again without a UTF-8 locale, with generated files current, no credential shape in the tree, and the tool's screen of itself clean |
| 0.2.0 | M1: field-proven | F-01 in docs/test-suite.md: a real cohort of at least 50 submissions screened, every flag read by a person, the false-positive rate per detector recorded with the field run |
| 0.3.0 | M2: corpus at scale | F-02: a known fork detected against a corpus of at least 30 public repositories |
| 0.4.0 | M3: deep pass | judged scoring with evidence capture, and `dashboard --strict` in the release gate for every published verdict |
| 1.0.0 | stable | scorecard format frozen, and a quarter of use with no unresolved false critical flag |

From 0.2.0, patch releases (0.x.Y) carry fixes only: no new scorecard fields, no change a published scorecard would notice. Before that, a 0.1.x release is an unproven build and may add features and fields, each one listed in CHANGELOG.md.

## CI

The CI lane is the GitHub workflow `.github/workflows/gate.yml`. It runs `tools/gate.py` on every push and pull request, and on a `vX.Y.Z` tag it adds the release checks for that version. Every workflow must run the gate (cases R-04 and R-05). Run the gate by hand on the release branch too, and paste its output into the pull request.

## Branches

- `main`: what was released. Protected: pull requests only, no force-push, no deletion. A pull request into `main` carries the gate's output and the `gate` check must pass.
- `dev`: integration. Feature branches (`feat/<topic>`, `fix/<topic>`) open pull requests into `dev`.
- `release/X.Y.Z`: cut from `dev` when a release is ready. Only fixes, the version bump and the changelog land here.
- `hotfix/X.Y.Z`: cut from `main` for an urgent fix to a released version.

The repository starts with only `main`, so `dev` and the `release/` and `hotfix/` branches above do not exist yet; they are created when the first change after 0.1.0 needs them.

## Cutting a release

1. From `dev`, create `release/X.Y.Z`.
2. In one commit: bump `version` in pyproject.toml and `__version__` in the package, rename "Unreleased" in CHANGELOG.md to `## X.Y.Z (YYYY-MM-DD)`, and change the version in the README's status line and install line, then run `python3 tools/gen_example.py`, because the example records the version that built it.
3. `python3 tools/gate.py --release X.Y.Z --require-all` passes on the release branch, with a clean working tree. Paste its output into the pull request. If a Python version is not installed, run without `--require-all` and say in the pull request which version did not run.
4. Optional: a release candidate. Tag `vX.Y.Z-rc.N` on the release branch and publish it as a GitHub pre-release.
5. Open a pull request `release/X.Y.Z → main`, review it, and merge it with a merge commit (not squash), so the tag's commit is on `main`.
6. On `main`: `git tag -a vX.Y.Z -m "Quiet Counsel X.Y.Z"`, push the tag, and `gh release create vX.Y.Z --verify-tag --notes-file <that CHANGELOG section>`.
7. Merge `main` back into `dev`.

A hotfix follows the same path from `hotfix/X.Y.Z` into `main`, then back into `dev`.

## Tags

- Annotated tags only, named `vX.Y.Z` (or `vX.Y.Z-rc.N`), always on a commit the gate passed.
- A published tag is never moved or deleted. If a release is wrong, release the next patch, and say in its notes what it supersedes.
- Tags and releases are pushed only from the account that owns the repository, checked with `gh api user --jq .login` right before the push.

## Install a release

```sh
pip install "git+https://github.com/sourav-patra/quiet-counsel@vX.Y.Z"
quiet-counsel --version
```
