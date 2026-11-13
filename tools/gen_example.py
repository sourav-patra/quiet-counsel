"""Rebuild examples/ from the synthetic sample project, with a fixed clock so the output is
byte-identical run to run. Case E-02 regenerates it and fails if the committed copy differs."""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
os.environ["QUIET_COUNSEL_NOW"] = "2026-09-24T00:00:00Z"

from quiet_counsel import dashboard, sample, scan  # noqa: E402

OUT = os.path.join(HERE, "..", "examples")


def build():
    work = tempfile.mkdtemp()
    cwd = os.getcwd()
    try:
        sample.write(os.path.join(work, "sample-project"))
        os.chdir(work)
        card = scan.screen("sample-project")
    finally:
        os.chdir(cwd)
        shutil.rmtree(work, ignore_errors=True)
    page = dashboard.build([card], "Sample review: one synthetic project")
    # The card is withheld at its one output boundary (scan.withhold_all), so the sample's planted
    # instruction is already a notice here and no complete attack phrase is committed (AGENTS.md).
    return json.dumps(card, indent=2, ensure_ascii=False) + "\n", page


if __name__ == "__main__":
    card, page = build()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "sample-scorecard.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(card)
    with open(os.path.join(OUT, "sample-dashboard.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print("wrote examples/sample-scorecard.json and examples/sample-dashboard.html")
