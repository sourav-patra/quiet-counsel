# Use it in CI

This workflow screens the repository it runs in and fails the job if the band is `blocked`. A band orders attention and does not rank quality, so decide whether a blocked band should stop your merges before you copy it. A warning or review band passes.

```yaml
name: screen
on: [pull_request]
permissions:
  contents: read
jobs:
  screen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97  # v7.0.0
        with:
          python-version: "3.13"
      - run: pip install "git+https://github.com/sourav-patra/quiet-counsel@v0.1.1"
      - run: quiet-counsel screen . --out "$RUNNER_TEMP/cards"
      - name: Fail on a blocked band
        run: python3 -c "import json,glob,sys; sys.exit(any(json.load(open(f,encoding='utf-8'))['totals']['band']=='blocked' for f in glob.glob(sys.argv[1]+'/cards/*.json')))" "$RUNNER_TEMP"
```

The two actions are pinned by commit hash, the same hashes this repository's own `gate` workflow uses, with the tag in a comment. The cards go to `$RUNNER_TEMP` so the screen does not read its own output.

What was run: the install, screen and band-check steps, in a fresh virtual environment on Windows with `RUNNER_TEMP` set, on a clean project (exit 0) and on the sample project (exit 1). The workflow itself was not run on GitHub.

Do not run this on a pull request from a fork with extra permissions or secrets. The screen reads files and runs nothing from them, but a workflow that checks out untrusted code with write access is one of the patterns [NOTICES.md](NOTICES.md) describes.
