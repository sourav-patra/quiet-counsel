"""README statements checked against the files, with no model and no network. Four kinds: the
licence, "no dependencies", a command-line flag, and a path the README says the repository holds.

Each check fires only when the repository plainly says otherwise. When the README is scoped,
the files are unclear or nothing can be compared, it says nothing. No project code is run.
Only README prose is read: fenced code and HTML comments are skipped.
"""

import bisect
import fnmatch
import json
import os
import re

try:
    import tomllib
except ImportError:  # shortcut: Python 3.10 and older skip pyproject.toml, upgrade with requires-python
    tomllib = None

from . import scan as _s

DOC_EXT = {".md", ".txt", ".html", ".css", ".rst"}
PARSER_RE = re.compile(r"\b(argparse|click|typer|commander|clap|cobra)\b")
OTHER_COMMAND_RE = re.compile(r"\b(pip3?|git|npm|npx|docker|uv|pipx|curl)\b")
INCLUDES_RE = re.compile(r"(?i)\b(includes?|ships?|shipped|holds?|contains?|comes with|bundles?)\b")
SCOPE_RE = re.compile(r"(?i)\b(besides|except|other than|apart from|aside from|beyond|at runtime|"
                      r"for development|dev|keep|must|should|scripts?)\b")
DEPENDENCY_CLAIM_RE = re.compile(r"(?i)zero[- ]dependenc|\bno dependenc|dependency[- ]free|"
                                 r"standard library only|stdlib only")
NEGATED_RE = re.compile(r"(?i)\b(does not|doesn't|do not|don't|not|never|without|no longer)\b")
READER_RE = re.compile(r"(?i)\byour\b|\b(put|place|copy|copied|drop|add|install(ed)?)\b[^.]{0,40}\b(in|into|to|under)\b")
GENERATED_TOPS = {"out", "output", "build", "dist", "cards", "node_modules", "target", "tmp", "coverage"}


def prose_lines(text):
    """[(line number, text)] with fenced code and HTML comments blanked, numbers kept."""
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    out, fence = [], None
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*(```+|~~~+)", line)
        if m:
            fence = None if fence and m.group(1)[0] == fence else (fence or m.group(1)[0])
            continue
        if not fence:
            out.append((n, line))
    return out


def _readme(root):
    for name in sorted(os.listdir(root)):
        if re.match(r"(?i)^readme(\.|$)", name) and not _s.leaves_root(root, os.path.join(root, name)):
            return name, prose_lines(_s.read_text(os.path.join(root, name), 200000, root))
    return None, []


def _spans(line):
    return re.findall(r"`([^`\n]+)`", line)


# ---------------------------------------------------------------------------- licence

LICENCE_CLAIM_RES = [
    re.compile(r"(?i)licen[cs]ed\s+(?:under|with)\s+(?:the\s+)?([^.,;\n)\]]+)"),
    re.compile(r"(?i)\b(MIT|Apache[- ]?(?:2(?:\.0)?)?|BSD(?:[- ]\d[- ]Clause)?|ISC|A?L?GPL\S*|MPL\S*)\s+licen[cs]e\b"),
    re.compile(r"(?i)badge/licen[cs]e[-_]([A-Za-z0-9.+_-]+)"),
]
FAMILIES = [("AGPL", "GPL"), ("LGPL", "GPL"), ("GPL", "GPL"), ("MIT", "MIT"), ("APACHE", "Apache-2.0"),
            ("BSD", "BSD"), ("ISC", "ISC"), ("MPL", "MPL-2.0"), ("MOZILLA", "MPL-2.0")]


def _family(name):
    n = (name or "").upper()
    return next((fam for key, fam in FAMILIES if re.search(rf"(?<![A-Z]){key}(?![A-Z])", n)), None)


def licence_mismatch(root, prose, declared, declared_file):
    want = _family(declared)
    if not want:
        return None
    claims = []
    for n, line in prose:
        if re.search(r"(?i)\bor\b|\bdual\b|\band\b", line):
            continue
        for rx in LICENCE_CLAIM_RES:
            for m in rx.finditer(line):
                fam = _family(m.group(1))
                if fam:
                    claims.append((n, line, fam))
    if not claims or any(c[2] == want for c in claims):
        return None
    n, line, fam = claims[0]
    return {"kind": "licence", "line": n, "text": line,
            "other": _s.ev("file", f"{declared_file}:1", _line_at(os.path.join(root, declared_file), 1, root)),
            "what": f"README names {fam}, {declared_file} is identified as {declared}"}


# ---------------------------------------------------------------------------- dependencies

def _requirement(root):
    for name in sorted(os.listdir(root)):
        if re.match(r"requirements[^/]*\.txt$", name) and not re.search(r"dev|test|doc", name):
            for i, line in enumerate(_s.read_text(os.path.join(root, name), 100000, root).splitlines(), 1):
                s = line.strip()
                if s and not s.startswith(("#", "-")):
                    return name, i, s
    return None


def _toml_project(root, what):
    """The [project] table of pyproject.toml, or {} when the file is absent or its types are wrong."""
    p = os.path.join(root, "pyproject.toml")
    if not (tomllib and _s.is_regular(p, root)):
        return {}
    try:
        proj = tomllib.loads(_s.read_text(p, 200000, root)).get("project", {})
    except (tomllib.TOMLDecodeError, RecursionError):
        return {}
    if not isinstance(proj, dict):
        _s.limit_note(f"pyproject.toml: [project] is not a table, so {what} was left unchecked.")
        return {}
    return proj


def _package_json(root, what):
    p = os.path.join(root, "package.json")
    if not _s.is_regular(p, root):
        return {}
    try:
        data = json.loads(_s.read_text(p, 200000, root))
    except (ValueError, RecursionError):  # deeply nested input is not usable metadata
        return {}
    if not isinstance(data, dict):
        _s.limit_note(f"package.json: the top level is not an object, so {what} was left unchecked.")
        return {}
    return data


def _first_dependency(root):
    hit = _requirement(root)
    if hit:
        return _s.ev("file", f"{hit[0]}:{hit[1]}", hit[2])
    deps = _toml_project(root, "the dependency claim").get("dependencies") or []
    if not isinstance(deps, list):
        _s.limit_note("pyproject.toml: [project] dependencies is not a list, so the dependency claim was left unchecked.")
        deps = []
    if deps and isinstance(deps[0], str) and deps[0].split():
        return _dep_ev(os.path.join(root, "pyproject.toml"), deps[0].split()[0], root)
    deps = _package_json(root, "the dependency claim").get("dependencies")
    if isinstance(deps, dict) and deps:
        return _dep_ev(os.path.join(root, "package.json"), str(next(iter(deps))), root)
    if deps is not None and not isinstance(deps, dict):
        _s.limit_note("package.json: dependencies is not an object, so the dependency claim was left unchecked.")
    return None


def _line_at(path, n, root):
    lines = _s.read_text(path, 200000, root).splitlines()
    return lines[n - 1].strip() if 0 < n <= len(lines) else ""


def _dep_ev(path, needle, root):
    """Evidence on the first line of a manifest that holds the dependency name."""
    for i, line in enumerate(_s.read_text(path, 200000, root).splitlines(), 1):
        if needle in line:
            return _s.ev("file", f"{os.path.basename(path)}:{i}", line.strip())
    return _s.ev("file", f"{os.path.basename(path)}:1", _line_at(path, 1, root))


def dependency_mismatch(root, prose):
    claim = next(((n, ln) for n, ln in prose
                  if DEPENDENCY_CLAIM_RE.search(ln) and not SCOPE_RE.search(ln)), None)
    other = claim and _first_dependency(root)
    if not other:
        return None
    return {"kind": "dependencies", "line": claim[0], "text": claim[1], "other": other,
            "what": f"README says no dependencies, {other['ref']} lists one"}


# ---------------------------------------------------------------------------- flags

SOURCE_BUDGET = 5_000_000  # characters read across the whole tree by the flag and eval checks


def _is_code(rel):
    ext = os.path.splitext(rel)[1]
    return ext in _s.TEXT_EXT and ext not in DOC_EXT


def _scan_sources(root, names):
    """(a parser exists, the names found, complete). Reads one file at a time and stops when a
    parser is found and every name is, or when SOURCE_BUDGET characters have been read. A command
    file, a SKILL.md and a script with a shebang line can hold a flag, because for a plugin they
    are the program."""
    todo, found, has_parser, left = set(names), set(), False, SOURCE_BUDGET
    for p, rel in _s.walk(root, None, include_hidden=True):
        ext = os.path.splitext(rel)[1]
        code = _is_code(rel)
        if not (code or (ext == ".md" and re.search(r"(^|/)commands/[^/]+\.md$|(^|/)SKILL\.md$", rel))
                or (ext == "" and _shebang(p))):
            continue
        if left <= 0:
            _s.reached("README flag check: source characters read", SOURCE_BUDGET, count_only=True)
            return has_parser, found, False
        # the allowance counts what was read, not what survives line trimming
        # shortcut: a file cut by the allowance itself is not reported, only the next file is
        text, used = _s.read_counted(p, min(500000, left))
        left -= used
        has_parser = has_parser or (code and bool(PARSER_RE.search(text)))
        for n in [n for n in todo if _flag_in(n, text)]:
            todo.discard(n)
            found.add(n)
        if has_parser and not todo:
            break
    return has_parser, found, True


def _shebang(path):
    try:
        fh = _s.open_regular(path)
        if fh is None:
            return False
        with fh:
            return fh.read(2) == b"#!"
    except OSError:
        return False


def _norm(name):
    return re.sub(r"\.(py|js|mjs|ts|sh)$", "", os.path.basename(str(name)).lower()).replace("_", "-")


def own_names(root):
    """Names the project's command goes by: pyproject scripts, package.json bin, its folder name."""
    names = {_norm(os.path.basename(os.path.abspath(root)).split("__")[-1])}
    proj = _toml_project(root, "the command-line flag claims")
    scripts = proj.get("scripts", {})
    if not isinstance(scripts, dict):
        _s.limit_note("pyproject.toml: [project] scripts is not a table, so its command names were not used.")
        scripts = {}
    names |= {_norm(k) for k in scripts} | {_norm(proj.get("name", ""))}
    data = _package_json(root, "the command-line flag claims")
    bin_, pkg = data.get("bin"), data.get("name", "")
    if bin_ is not None and not isinstance(bin_, (dict, str)):
        _s.limit_note("package.json: bin is not an object or a string, so its command names were not used.")
    if not isinstance(pkg, str):
        _s.limit_note("package.json: name is not a string, so it was not used as a command name.")
        pkg = ""
    names |= {_norm(k) for k in bin_} if isinstance(bin_, dict) else \
        {_norm(bin_)} if isinstance(bin_, str) else {_norm(pkg)}
    return names - {""}


def _command_of(span):
    t = span.replace("$ ", "", 1).split()
    if t[:2] in (["python", "-m"], ["python3", "-m"], ["py", "-m"]):
        t = t[2:]
    elif t[:1] in (["npx"], ["uvx"]):
        t = t[1:]
    return _norm(t[0]) if t and not t[0].startswith("-") else None


def _flag_in(name, text):
    bare = name[2:]
    if re.search(re.escape(name), text) or re.search(rf"[\"']{re.escape(bare)}[\"']", text):
        return True
    # typer and clap derive --name from a parameter or field called name
    ident = re.escape(bare.replace("-", "_"))
    return bool(re.search(r"\b(typer|clap)\b", text) and re.search(rf"\b{ident}\s*:", text))


def flag_mismatches(root, prose):
    own, claimed, seen = own_names(root), [], set()
    for n, line in prose:
        if OTHER_COMMAND_RE.search(line) or (re.match(r"\s*[-*+]\s", line) and "](http" in line):
            continue
        for span in _spans(line):
            if _command_of(span) not in own:  # a flag with no command of this project beside it
                continue
            for name in re.findall(r"(?<![\w-])--[a-z][\w-]+", span):
                if name not in seen and name not in ("--help", "--version"):
                    seen.add(name)
                    claimed.append((n, line, name))
    if not claimed:
        return []
    has_parser, found, complete = _scan_sources(root, [c[2] for c in claimed])
    if not has_parser or not complete:  # an unfinished read proves no absence
        return []
    return [{"kind": "flag", "line": n, "text": line,
             "other": _s.ev("command", f"grep -rF -e {name} (source files)", "no match"),
             "what": f"README names {name}, no source file holds it"}
            for n, line, name in claimed if name not in found]


# ---------------------------------------------------------------------------- paths

def _gitignored(root, rel):
    p = os.path.join(root, ".gitignore")
    for pat in _s.read_text(p, 20000, root).splitlines() if _s.is_regular(p, root) else []:
        pat = pat.strip().strip("/")
        if pat and not pat.startswith(("#", "!")) and (
                fnmatch.fnmatch(rel.strip("/"), pat) or rel.strip("/").startswith(pat + "/")
                or any(fnmatch.fnmatch(part, pat) for part in rel.strip("/").split("/"))):
            return True
    return False


def path_mismatches(root, prose):
    out, seen = [], set()
    for n, line in prose:
        if not INCLUDES_RE.search(line) or NEGATED_RE.search(line) or READER_RE.search(line):
            continue
        for span in _spans(line):
            parts = span.rstrip("/").split("/")
            if (span in seen or "/" not in span or not re.fullmatch(r"[\w.\-]+(/[\w.\-]+)*/?", span)
                    or span.startswith(("./", "../", "/")) or ".." in parts or parts[0] in GENERATED_TOPS
                    or _gitignored(root, span)
                    # owner/repo and model ids: two names, no dot, and no such folder here
                    or (len(parts) == 2 and "." not in span and not (os.path.isdir(os.path.join(root, parts[0]))
                                            and not _s.leaves_root(root, os.path.join(root, parts[0]))))):
                continue
            seen.add(span)
            if not _s.exists_inside(root, os.path.join(root, span)):
                out.append({"kind": "path", "line": n, "text": line,
                            "other": _s.ev("command", f"test -e {span}", "not found"),
                            "what": f"README says the repository holds {span}, it does not"})
    return out


# ---------------------------------------------------------------------------- the flag

def readme_claim_flag(root, declared, declared_file):
    """The readme-claim-mismatch flag, or None. No caps: this check has no measured false
    positive rate yet, so it must not move a band."""
    name, prose = _readme(root)
    found = [m for m in (licence_mismatch(root, prose, declared, declared_file),
                         dependency_mismatch(root, prose)) if m]
    found += flag_mismatches(root, prose) + path_mismatches(root, prose)
    if not found:
        return None
    evidence = []
    for m in found[:12]:
        evidence += [_s.ev("file", f"{name}:{m['line']}", m["text"].strip()), m["other"]]
    return {"id": "readme-claim-mismatch", "severity": "info",
            "title": f"{len(found)} README statement(s) the files do not bear out",
            "detail": "; ".join(m["what"] for m in found[:12]) +
                      ". A reader should check each: the README may be out of date, or the files may be.",
            "evidence": evidence}


# ---------------------------------------------------------------------------- eval evidence
# Only layouts checked against the tools' own documentation. A setup file shows evals are
# configured; a recognised result file name is possible evidence that a run wrote output. Neither shows a README number is right.

SETUP_PATH_RES = [re.compile(p) for p in (
    r"(^|/)evals/evals\.json$", r"(^|/)promptfooconfig\.ya?ml$",
    r"(^|/)evals/registry/evals/[^/]+\.ya?ml$", r"(^|/)lm_eval/tasks/.+\.ya?ml$")]
RESULT_PATH_RES = [re.compile(p) for p in (
    r"(^|/)iteration-[^/]+/benchmark\.json$", r"(^|/)grading\.json$", r"(^|/)logs/[^/]+\.eval$",
    r"(^|/)\.deepeval/", r"(^|/)test_run_[^/]*\.json$", r"(?i)(^|/)[^/]*eval[^/]*/(.+/)?results\.json$")]
SETUP_TEXT_RES = [re.compile(r"(?m)^\s*@pytest\.mark\.langsmith\b"),
                  re.compile(r"(?s)\binspect_ai\b.*^\s*@task\b", re.M)]


def eval_evidence(root):
    """{"state": none|setup|result, "paths": the files that decided it}."""
    setup, result, left = [], [], SOURCE_BUDGET
    for p, rel in _s.walk(root, None, include_hidden=True):
        if any(r.search(rel) for r in RESULT_PATH_RES):
            result.append(rel)
        elif any(r.search(rel) for r in SETUP_PATH_RES):
            setup.append(rel)
        elif rel.endswith(".py") and os.path.getsize(p) <= 500_000:
            if left <= 0:
                _s.reached("eval evidence: python characters read", SOURCE_BUDGET, count_only=True)
                continue
            text, used = _s.read_counted(p, min(500_000, left))
            left -= used
            if any(r.search(text) for r in SETUP_TEXT_RES):
                setup.append(rel)
    state, paths = ("result", result) if result else ("setup", setup) if setup else ("none", [])
    # a path prints only if it is path-shaped by the rule for .scanignore patterns, so a file
    # name cannot carry text to the card
    paths = [x if _s.PATTERN_TEXT_RE.match(x) and not _s.holds_secret(x) else _s.PATTERN_WITHHELD for x in paths[:10]]
    return {"state": state, "paths": paths}


BENCH_NAMED = (r"SWE-?bench\w*|HumanEval|MBPP|MMLU\w*|GSM-?8K|GAIA|AgentBench|BFCL|tau-?bench|"
               r"Terminal-?Bench|HellaSwag|TruthfulQA|BIG-?bench|DeepSWE")
BENCH_RE = re.compile(rf"(?i)\b(?:{BENCH_NAMED}|benchmark|leaderboard)\b")
NAMED_RE = re.compile(rf"(?i)\b(?:{BENCH_NAMED})\b")
SOTA_RE = re.compile(r"(?i)\bstate[- ]of[- ]the[- ]art\b|\bSoTA\b")
PCT_RE = re.compile(r"\d{1,3}(?:\.\d+)?\s*%")
BEATS_RE = re.compile(r"(?i:\b(?:beats?|outperforms?|surpass(?:es)?|faster than|better than))\s+[A-Z][\w.-]+")
RANK_RE = re.compile(r"(?i)#\d+\s+(?:rank\w*|on\b)")
FEWER_RE = re.compile(r"(?i)\d+(?:\.\d+)?\s*%\s+(?:fewer|less|more|faster|cheaper)\b")


def _score_claim(line):
    line = re.sub(r"`[^`\n]*`", "", line)
    line = re.sub(r"\"[^\"\n]{25,}\"|\u201c[^\u201d\n]{25,}\u201d", "", line)
    if (SOTA_RE.search(line) and NAMED_RE.search(line)) or RANK_RE.search(line) or \
            FEWER_RE.search(line) or BEATS_RE.search(line):
        return True
    if re.search(r"(?i)leaderboard", line) and re.search(r"\d", line):
        return True
    starts = [b.start() for b in BENCH_RE.finditer(line)]
    return any(bisect.bisect_right(starts, p.start() + 80) - bisect.bisect_left(starts, p.start() - 80)
               for p in PCT_RE.finditer(line))


RESULT_DIRS = {"docs", "benchmarks", "benchmark", "results", "result"}
NUMBER_RE = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?")


def _figures(line):
    # only a figure with a percent sign or a decimal point; a bare integer matches anything
    return {m.group(0) for m in re.finditer(r"(?<![\w.-])(?:\d+(?:\.\d+)?(?=\s*%)|\d+\.\d+)",
                                            re.sub(r"`[^`\n]*`", "", line))}


def _held(fig, numbers):
    """True when a number rounds to the figure as written, as a percentage or as a fraction."""
    dec = len(fig.split(".")[1]) if "." in fig else 0
    want = float(fig)
    return any(round(n, dec) == want or round(n * 100, dec) == want for n in numbers)


def _held_figures(root, figs):
    """The figures that a JSON, CSV or Markdown file under docs, benchmarks or results holds.
    Reads one file at a time and stops after SOURCE_BUDGET characters, reported as a budget."""
    todo, held, left = set(figs), set(), SOURCE_BUDGET
    for p, rel in _s.walk(root, {".json", ".csv", ".md"}):
        if not todo:
            break
        if rel.lower().startswith("readme") or not RESULT_DIRS & set(rel.lower().split("/")[:-1]):
            continue
        if left <= 0:
            _s.reached("score check: result characters read", SOURCE_BUDGET, count_only=True)
            break
        text, used = _s.read_counted(p, min(1_000_000, left))
        left -= used
        numbers = [float(x) for x in NUMBER_RE.findall(text)]
        for fig in [f for f in todo if _held(f, numbers)]:
            todo.discard(fig)
            held.add(fig)
    return held


def score_flag(root, evidence):
    """score-without-result (information): the README quotes a score, ranking or benchmark
    comparison and the tree holds no result file. It says where it looked, never that the claim
    is wrong: a hosted service may keep the result."""
    if evidence["state"] == "result":
        return None
    name, prose = _readme(root)
    hits = [(n, ln) for n, ln in prose if not ln.lstrip().startswith(">") and _score_claim(ln)]
    if hits:  # a quoted figure that a result file elsewhere in the tree holds is not unbacked
        held = _held_figures(root, set().union(*(_figures(ln) for _, ln in hits)))
        hits = [(n, ln) for n, ln in hits if not (_figures(ln) & held)]
    if not hits:
        return None
    seen = ("Eval setup files were found (" + ", ".join(evidence["paths"][:3]) + ") but no result file."
            if evidence["state"] == "setup" else "No eval setup or result file was found.")
    return {"id": "score-without-result", "severity": "info",
            "title": f"README quotes a score or ranking; no result file found in the layouts checked ({len(hits)} line(s))",
            "detail": f"{seen} The result may be kept elsewhere, such as a hosted service, so this "
                      "says only that the repository holds no result file to read. It does not say "
                      "whether the number is right.",
            "evidence": [_s.ev("file", f"{name}:{n}", ln.strip()) for n, ln in hits[:5]] +
                        [_s.ev("command", "known eval result file names (see docs/CHECKS.md)", "none found")]}
