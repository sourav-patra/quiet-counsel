# Install

Quiet Counsel needs Python 3.11 or newer and git. It has no other dependency. Every command below was run in a fresh environment on Windows 11 with Python 3.13 before it was written here.

## Install a release

Pick one.

```sh
# pip, into the Python you are using (a virtual environment is a good idea)
pip install "git+https://github.com/sourav-patra/quiet-counsel@v0.1.0"

# pipx, which keeps it in its own environment
pipx install "git+https://github.com/sourav-patra/quiet-counsel@v0.1.0"

# uv
uv tool install "git+https://github.com/sourav-patra/quiet-counsel@v0.1.0"
```

The `@v0.1.0` part is a git tag, so you get that release and not whatever is on the main branch today. uv prints a warning if its tool directory is not on your PATH; run `uv tool update-shell` or add the directory it names.

## Install from source

```sh
git clone https://github.com/sourav-patra/quiet-counsel
cd quiet-counsel
pip install .
```

Use `pip install -e .` if you intend to edit it. You can also run it without installing: from the clone, `PYTHONPATH=src python3 -m quiet_counsel --version`.

## Windows

- Use `py -3` where this page says `python3`.
- In PowerShell, set variables with `$env:NAME='value'`, not `NAME=value`. The test command further down is given in both forms.
- pip puts `quiet-counsel.exe` in the `Scripts` folder of the environment. If the shell cannot find it, run `py -3 -m quiet_counsel` instead, which is the same program.

## Check that it works

```sh
quiet-counsel --version
quiet-counsel sample ./sample
quiet-counsel screen ./sample --out ./cards
```

The version line reads `quiet-counsel 0.1.0`. The screen prints one line that starts with `blocked`, because the sample has problems planted in it.

## Check the no-network claim

Case G-03 checks that no module imports a network library, and case G-09 checks that a screen with every socket refused gives the same card byte for byte, with the clock fixed:

```sh
TZ=UTC PYTHONPATH=src:tests python3 -m unittest discover -s tests -t tests -k test_G03 -k test_G09
```

On Windows PowerShell, from the repository root: `$env:TZ='UTC'; $env:PYTHONPATH='src;tests'; py -3 -m unittest discover -s tests -t tests -k test_G03 -k test_G09`.

## Upgrade

Install the new tag over the old one. pipx and uv do not upgrade a package installed from a git address, so they need `--force`.

```sh
pip install --upgrade "git+https://github.com/sourav-patra/quiet-counsel@vNEW"
pipx install --force "git+https://github.com/sourav-patra/quiet-counsel@vNEW"
uv tool install --force "git+https://github.com/sourav-patra/quiet-counsel@vNEW"
```

Replace `vNEW` with a tag listed in [CHANGELOG.md](../CHANGELOG.md).

## Uninstall

```sh
pip uninstall quiet-counsel
pipx uninstall quiet-counsel
uv tool uninstall quiet-counsel
```

Scorecards and pages you wrote stay where you put them.

## Skills and agent roles

To install the three skills and three roles into an agent host:

```sh
python3 install.py --dest <your host's skills directory> --agents-dest <its agents directory>
```

The installer never deletes anything and never overwrites without `--force`. The skills' scripts need the `quiet_counsel` package, so run `pip install .` from the clone as well. [AGENT-INTERFACE.md](AGENT-INTERFACE.md) lists the directories common hosts read.
