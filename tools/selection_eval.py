"""Skill selection eval: does a model pick the right skill from the descriptions alone?

The script never calls a model. It writes the prompt, you give that prompt to whatever model
or host you want to measure, and it scores the JSON answer that comes back. Running the same
prompts against two versions of the descriptions is the with-and-without comparison.

    python3 tools/selection_eval.py prompt [--skills DIR] > prompt.txt
    python3 tools/selection_eval.py score answer.json [answer2.json ...]

`--skills` points at another checkout's skills/ directory, for the "without" side. Answers are
JSON objects mapping the prompt number (as a string) to a skill name or null; a number
with no answer counts as a miss. Scoring prints
the hits per set (tuning and held-out) and every miss. Exit 0 always for `prompt`; for
`score`, 0 when every answer is perfect, 1 otherwise, 2 on bad input.
"""

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EVALS = os.path.join(REPO, "evals", "triggers.jsonl")


def descriptions(skills_dir):
    out = []
    for path in sorted(glob.glob(os.path.join(skills_dir, "*", "SKILL.md"))):
        with open(path, encoding="utf-8") as fh:
            head = fh.read().split("---")[1]
        name = re.search(r"(?m)^name:\s*(.+)$", head).group(1).strip()
        block = re.search(r"(?m)^description:\s*>?\s*\n((?:  .+\n?)+)", head)
        text = " ".join(line.strip() for line in block.group(1).splitlines()) if block else \
            re.search(r"(?m)^description:\s*(.+)$", head).group(1).strip()
        out.append((name, text))
    return out


def rows():
    with open(EVALS, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build_prompt(skills_dir):
    lines = ["Skills available:"]
    lines += [f"- {name}: {text}" for name, text in descriptions(skills_dir)]
    lines += ["", "For each user request below, say which ONE skill you would load to handle it, or "
              "null if none of these skills fits the request. Reply with only a JSON object mapping "
              "the request number (as a string) to a skill name or null. No other text.", ""]
    lines += [f"{i}. {r['prompt']}" for i, r in enumerate(rows(), 1)]
    return "\n".join(lines) + "\n"


def score(paths):
    data, worst = rows(), 0
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            print(f"{path}: no JSON object found", file=sys.stderr)
            return 2
        answer = json.loads(m.group(0))
        by_set, misses = {}, []
        for i, r in enumerate(data, 1):
            got = answer.get(str(i), "<missing>")
            hit = got == r["expect"]
            s = by_set.setdefault(r.get("set", "tuning"), [0, 0])
            s[0] += hit
            s[1] += 1
            if not hit:
                misses.append(f"  {i}. expected {r['expect']}, got {got}: {r['prompt']}")
        summary = ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by_set.items()))
        print(f"{path}: {summary}")
        print("\n".join(misses) if misses else "  no misses")
        worst = max(worst, 1 if misses else 0)
    return worst


def main(argv=None):
    ap = argparse.ArgumentParser(prog="selection_eval", description="Skill selection eval.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prompt", help="print the prompt to give a model")
    p.add_argument("--skills", default=os.path.join(REPO, "skills"),
                   help="skills directory whose descriptions to use (default: this repository's)")
    s = sub.add_parser("score", help="score one or more JSON answers")
    s.add_argument("answers", nargs="+", help="files holding a model's JSON answer")
    a = ap.parse_args(argv)
    if a.cmd == "prompt":
        sys.stdout.write(build_prompt(a.skills))
        return 0
    return score(a.answers)


if __name__ == "__main__":
    sys.exit(main())
