#!/usr/bin/env python3
"""Classify, screen and integrity-check an agent project.

Standard library only, no network. Every number reported carries the command or the path that
produced it, because a number a reader cannot re-derive has no place in a verdict.

This module measures, flags and bands. It never scores: every dimension it emits is
`unverified` until a person or an evaluator working from docs/RUBRIC.md scores it.
"""

import datetime as _dt
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess

from . import __version__ as VERSION

SKIP_DIRS = {".git", "node_modules", "vendor_bundle", "__pycache__", ".venv", "venv",
             "dist", "build", ".next", ".cache", "target"}
TEXT_EXT = {".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh",
            ".yml", ".yaml", ".json", ".toml", ".rb", ".go", ".rs", ".java", ".kt", ".html",
            ".css", ".cfg", ".ini", ".env", ".mjs", ".cjs"}

# Characters that can hide an instruction from a human reader.
# Characters with no visible form, split deliberately. The first set has no legitimate use in
# instruction text. The second is ordinary typography in Persian, Arabic, Hindi and emoji
# sequences, and flagging it would call every translated README an attack.
HIDING_RE = re.compile(
    "[\u200b\u202a-\u202e\u2060-\u2064\u2066-\u2069]"
    "|[\U000e0000-\U000e007f]")
TYPOGRAPHIC_RE = re.compile("[\u200c-\u200f\ufeff]")
HIDDEN_RE = HIDING_RE

# Text addressed to whatever is reading the repository. Deliberately narrow: these phrases have
# no innocent use inside a submission, and a wider net would flag ordinary documentation.
EVALUATOR_DIRECTED = [
    r"(?i)ignore (all |any )?(previous|prior|above) instructions",
    r"(?i)disregard (all |any )?(previous|prior|above)",
    r"(?i)you (are|act) (now )?(a|an) (judge|evaluator|grader|scorer)\b.{0,80}(score|rate|award)",
    r"(?i)(give|award|assign) (this|it|us) (a )?(perfect|full|10|ten|max)",
    r"(?i)(score|rate) (this|it|us) (a )?(10|ten|highest|maximum)",
    r"(?i)this (project|submission|repo(sitory)?) (has already been|is) (verified|approved|pre-?approved)",
    r"(?i)do not (report|flag|mention) (any|the) (issues?|problems?|findings?)",
    r"(?i)system prompt:.{0,60}(score|grade|judge)",
]

# High-confidence shapes: these strings have essentially no innocent form. Low-confidence ones
# match far more example config than real credentials, so they are reported at lower severity.
HIGH_CONFIDENCE_SECRETS = {"aws-access-key", "private-key-block", "github-token", "slack-token",
                           "google-api-key", "stripe-key"}
# A credential in a path like tests/ or examples/, or a value that looks like a placeholder, is
# reported but never raised as critical: fixtures that look like secrets are extremely common,
# and a scanner that cries wolf on them stops being read.
FIXTURE_PATH_RE = re.compile(
    r"(?i)((^|/)(tests?|__tests__|fixtures?|examples?|samples?|docs?|mocks?|demo)(/|$)"
    r"|[._-](test|spec|fixture|mock|example)s?\.[a-z]+$)")
# A test path: a directory named for tests, or a test file by name. Narrower than the fixture
# pattern above, which also covers examples, docs and samples.
TEST_PATH_RE = re.compile(r"(?i)((^|/)(tests?|testdata|fixtures|__tests__)/|(^|/)test_[^/]*$"
                          r"|(^|/)[^/]*_test\.[^/]*$)")
PLACEHOLDER_RE = re.compile(r"(?i)(example|sample|placeholder|redacted|synthetic|fixture|dummy|"
                            r"changeme|your[-_]|xxx+|<[^>]{2,}>|\$\{|\bfake\b|\btest\b|"
                            r"0{8,}|1234567890)")

SECRET_PATTERNS = [
    ("aws-access-key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("private-key-block", r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    ("github-token", r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    ("slack-token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("google-api-key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("stripe-key", r"\bsk_(live|test)_[0-9a-zA-Z]{20,}"),
    ("jwt", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    ("generic-secret-assignment",
     r"(?i)\b(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*\\?[\"'][^\"'\s\\]{16,}\\?[\"']"),
]

SUPPLY_CHAIN_PATTERNS = [
    ("curl-pipe-shell", r"(curl|wget)[^\n|]{0,120}\|\s*(sudo\s+(-\S+\s+)*)?(ba|z|da)?sh(?![\w-])"),
    ("tls-verification-off",
     r"(NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|verify\s*=\s*False|rejectUnauthorized:\s*false"
     r"|curl[^\n]{0,80}(-k\b|--insecure)|GIT_SSL_NO_VERIFY)"),
    ("commit-hook-bypass", r"--no-verify\b"),
]

COPYLEFT_MARKERS = [
    ("GPL", r"GNU GENERAL PUBLIC LICENSE|(?<![A-Za-z])GPL-[23]\.0|SPDX-License-Identifier:\s*GPL"),
    ("AGPL", r"GNU AFFERO GENERAL PUBLIC LICENSE|AGPL-3\.0|SPDX-License-Identifier:\s*AGPL"),
    ("LGPL", r"GNU LESSER GENERAL PUBLIC LICENSE|LGPL-[23]"),
]
PERMISSIVE_MARKERS = [
    ("MIT", r"\bMIT License\b|SPDX-License-Identifier:\s*MIT"),
    ("Apache-2.0", r"Apache License\s*,?\s*Version 2\.0|SPDX-License-Identifier:\s*Apache-2\.0"),
    ("BSD", r"BSD [23]-Clause|SPDX-License-Identifier:\s*BSD"),
    ("ISC", r"\bISC License\b|SPDX-License-Identifier:\s*ISC"),
]
OTHER_LICENCE_MARKERS = [
    ("CC-BY-SA-4.0", r"Attribution-ShareAlike 4\.0|CC-BY-SA-4\.0"),
    ("CC-BY-NC-4.0", r"Attribution-NonCommercial|CC-BY-NC"),
    ("CC-BY-4.0", r"Creative Commons Attribution 4\.0|CC-BY-4\.0"),
    ("MPL-2.0", r"Mozilla Public License,? v(ersion)?\.? ?2\.0"),
    ("BUSL-1.1", r"Business Source License"),
    ("PolyForm", r"PolyForm"),
]

# Files an agent host reads as its own configuration or standing instructions. A project that
# writes to them changes how every later session behaves, so the write should be something the
# user asked for. Installing skills, commands or agents into a host's folders is ordinary
# catalogue installation and is not listed here.
HOST_CONFIG_RE = re.compile(
    r"(\.claude/settings(\.local)?\.json|\.claude\.json\b|\.claude/hooks\b|\.mcp\.json\b"
    r"|claude_desktop_config\.json|\.codex/(hooks\.json|config\.toml)|\.cursor/(mcp|hooks)\.json"
    r"|\.cursor/rules\b|\.cursorrules\b|\.gemini/settings\.json|copilot-instructions\.md"
    r"|(^|[\s'\"/(])(CLAUDE|AGENTS|GEMINI)\.md\b"
    r"|['\"]\.claude['\"]\s*[,/]\s*['\"](settings(\.local)?\.json|hooks)['\"])")
WRITE_CALL_RE = re.compile(
    r"(write_text|write_bytes|writeFileSync|writeFile|appendFileSync|appendFile|outputFile"
    r"|Set-Content|Add-Content|json\.dump\b|shutil\.copy\w*|copyFileSync)\s*\(?")
GATE_RE = re.compile(r"(?i)(--dry-run|\bread\s+-r?p\b|\binput\s*\(|\bconfirm\s*\(|\bprompt\s*\(|"
                     r"inquirer|questionary|\[y/n\]|are you sure)")
CODE_EXT = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".ps1"}
RULEBOOKS = ("AGENTS.md", "CLAUDE.md", "AGENT.md", "GEMINI.md", ".cursorrules")
ASSIGN_RE = re.compile(r"^\s*(?:export\s+|const\s+|let\s+|var\s+|readonly\s+)?([A-Za-z_]\w*)\s*:?=\s*")


def _writes_target(line, start, name=None):
    """Whether this line writes to the host file that starts at `start`, or to the variable
    `name` holding it. The file must be the target: `cat CLAUDE.md > copy.txt` reads it."""
    before = line[:start]
    if re.search(r">>?\s*[\"']?[^\s\"'>]*$", before):
        return True
    if re.search(r"\btee\s+(-a\s+)?[\"']?[^\s\"']*$", before):
        return True
    if re.search(r"\b(cp|mv|install)\b[^|;&]*\s[\"']?[^\s\"']*$", before) or \
            re.search(r"\bln\s+-s\w*\s[^|;&]*\s[\"']?[^\s\"']*$", before):
        return True
    if re.search(r"\bsed\s+-i\b", before):
        return True
    if re.search(r"open\([^)]*$", before) and re.search(r"^[^)]*,\s*(mode\s*=\s*)?['\"][wax]", line[start:]):
        return True
    return bool(WRITE_CALL_RE.search(line))


def host_config_writes(root):
    """[(rel, line_no, line, gated)] for code that writes to a host's settings, hooks or
    standing-instruction files. Reading those files, or naming them in comments and
    documentation, is not a write. A confirmation, prompt or dry run in the same file counts as
    a gate; an option that skips the prompt does not."""
    hits = []
    for path, rel in walk(root, CODE_EXT, include_hidden=True):
        if FIXTURE_PATH_RE.search(rel):
            continue
        if len(hits) >= 20:
            reached("host-config writes", 20)
            break
        lines = read_text(path, 500_000).splitlines()
        code = [ln for ln in lines if not ln.lstrip().startswith(("#", "//", "*", "/*"))]
        gated = any(GATE_RE.search(ln) for ln in code)
        held = {}
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith(("#", "//", "*", "/*")):
                continue
            found = list(HOST_CONFIG_RE.finditer(line))
            if found:
                if any(_writes_target(line, m.start()) for m in found):
                    hits.append((rel, i, clip(line), gated))
                    continue
                a = ASSIGN_RE.match(line)
                if a and a.end() <= found[0].start():
                    held[a.group(1)] = i
                continue
            for name in held:
                v = re.search(rf"(\$\{{?{name}\b|\b{name}\b)", line)
                if v and _writes_target(line, v.start(), name):
                    hits.append((rel, i, clip(line), gated))
                    break
    return hits


PATH_SPAN_RE = re.compile(r"`([A-Za-z0-9_.][\w./*-]*)`")


def _ignored_tops(root):
    try:
        with open(os.path.join(root, ".gitignore"), encoding="utf-8") as fh:
            return {ln.strip().strip("/") for ln in fh if ln.strip() and not ln.startswith(("#", "!"))}
    except OSError:
        return set()


def stale_rulebook_paths(root):
    """[(file, line_no, path)] for every repository path a root instruction file names in inline
    code that does not exist. Stale instructions mislead the agent that loads them every
    session; the research names this context debt."""
    out, names, ignored = [], None, _ignored_tops(root)
    for name in RULEBOOKS:
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        raw = read_text(p, 200_000)
        original = raw.splitlines()
        # A fence becomes spaces, every line break in it stays where it was (splitlines() breaks on
        # more than \n), so line numbers of `text` and `original` agree.
        text = re.sub(r"(```|~~~).*?\1", lambda m: re.sub(r"[^\n\r\x0b\x0c\x1c-\x1e\x85\u2028\u2029]", " ", m.group(0)),
                      raw, flags=re.S)
        seen = set()
        for i, line in enumerate(text.splitlines(), 1):
            hidden = holds_secret(original[i - 1])
            for m in PATH_SPAN_RE.finditer(line):
                ref = m.group(1).rstrip(".,;:")
                if ref in seen or ref.startswith(("http", "www.")) or "://" in ref:
                    continue
                seen.add(ref)
                bare = "/" not in ref.rstrip("/")
                first = ref.split("/")[0]
                if bare:
                    # a bare file name such as `SKILL.md` names a kind of file, so it is stale
                    # only when no file of that name exists anywhere; `Next.js` is a product
                    if not re.search(r"\.(md|py|sh|json|toml|ya?ml|txt)$", ref):
                        continue
                    if names is None:
                        names = {os.path.basename(r)
                                 for _, r in walk(root, None, max_files=200000, include_hidden=True)}
                    # walk() skips .github, so a workflow named bare is looked up where it lives
                    in_workflows = os.path.exists(os.path.join(root, ".github", "workflows", ref))
                    if ref not in names and not in_workflows and                             not os.path.exists(os.path.join(root, ref)):
                        out.append((name, i, WITHHELD if hidden else ref))
                    continue
                # owner/repo names such as `someone/tool` are references, not paths: a slash
                # counts only when the first segment is in the tree or the span is explicitly a
                # path; build outputs the project ignores are expected to be missing
                rooted = os.path.exists(os.path.join(root, first)) or ref.endswith("/") or \
                    ref.startswith("./") or re.search(r"\.(md|py|sh|js|ts|json|toml|ya?ml|txt)$", ref)
                if not rooted or first in ignored:
                    continue
                target = os.path.join(root, ref.rstrip("/"))
                exists = glob.glob(target, recursive=True) if "*" in ref else os.path.exists(target)
                if not exists:
                    out.append((name, i, WITHHELD if hidden else ref))
    if len(out) > 40:
        reached("stale references", 40)
    return out[:40]


CLAIM_PATTERNS = [
    ("tests", r"(\d[\d,]{0,7})\s+(?:unit\s+|integration\s+)?tests?\b"),
    ("skills", r"(\d[\d,]{0,7})\s+skills?\b"),
    ("agents", r"(\d[\d,]{0,7})\s+(?:sub-?)?agents?\b"),
    ("commands", r"(\d[\d,]{0,7})\s+commands?\b"),
    ("coverage", r"(\d{1,3})%\s+(?:test\s+)?coverage"),
    ("speedup", r"(\d[\d.]{0,5})\s*[x×]\s+(?:faster|speed-?up|improvement)"),
]
UNSUPPORTABLE_CLAIMS = [
    ("soc2", r"\bSOC\s?2\b"),
    ("slsa", r"\bSLSA\b(\s+level)?\s*[0-9]?"),
    ("iso27001", r"\bISO\s?27001\b"),
    ("hipaa", r"\bHIPAA\b"),
    ("production-ready", r"\bproduction[- ]ready\b"),
    ("battle-tested", r"\bbattle[- ]tested\b"),
    ("enterprise-grade", r"\benterprise[- ]grade\b"),
]


# ----------------------------------------------------------------------------- helpers

def sig(value, command=None, unit=None, note=None):
    out = {"value": value}
    if command:
        out["command"] = command
    if unit:
        out["unit"] = unit
    if note:
        out["note"] = note
    return out


# A line holding a credential shape or one of these words is never copied, in whole or in part. The
# words ignore what follows them, so no assignment grammar can slip past. secrets.X names a reference.
SECRET_WORD_RE = re.compile(r"(?i)secret(?!s\.)|token|api[_-]?key|_key\b|passw|passphrase|_pass\b|pwd|credential|bearer|"
                            r"authorization|://[^/\s:@]+:[^/\s@]+@")
SHAPE_RES = [(label, re.compile(pat)) for label, pat in SECRET_PATTERNS]
WITHHELD = "<line withheld>"


def holds_secret(line):
    return bool(SECRET_WORD_RE.search(line)) or any(rx.search(line) for _, rx in SHAPE_RES)


def redact(text):
    """Credential shapes out of a string that is not a source line: a path, a key, a name. The
    private-key header is not a secret; the key body that follows it is not a shape."""
    for label, rx in SHAPE_RES:
        if label != "private-key-block":
            text = rx.sub("<redacted>", text)
    return text


def clip(line, n=200):
    """A source line for a scorecard: withheld whole if it holds a secret, otherwise cut."""
    return WITHHELD if holds_secret(line) else line.strip()[:n]


def redact_all(value):
    """redact() applied to every string in a scorecard, keys included, so no credential shape in a
    name or a key survives. Two keys that redact to the same text stay two entries (#2, #3, ...)."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_all(v) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            base = nk = redact(k) if isinstance(k, str) else k
            n = 1
            while nk in out:
                n += 1
                nk = f"{base}#{n}"
            out[nk] = redact_all(v)
        return out
    return value


def ev(kind, ref, excerpt=None, label=""):
    out = {"kind": kind, "ref": ref}
    if excerpt is not None:
        excerpt = WITHHELD if re.search(r":\d+$", ref) and holds_secret(excerpt) else excerpt
        out["excerpt"] = label + excerpt[:400] + ("…" if len(excerpt) > 400 else "")
    return out


# Budgets a detector can reach while a screen runs: (detector, budget). screen() empties it first
# and turns each entry into a card limit and one warning, because a detector that stopped early has
# not read the rest of the tree.
_REACHED = []
_NOTES = []  # limits that are not a budget: input a check could not use


def limit_note(text):
    """Record on the card that a check left something unchecked, with the reason."""
    if text not in _NOTES:
        _NOTES.append(text)


def reached(detector, budget, count_only=False):
    """Record that a detector stopped. A `count_only` detector feeds a number on the card and no
    flag, so the card says the count is a floor and nothing else changes."""
    if (detector, budget, count_only) not in _REACHED:
        _REACHED.append((detector, budget, count_only))


def _is_ignore_file(root, name):
    """The root ignore file, by the same rule as its lookup: on a file system that folds case,
    `.SCANIGNORE` is the file the lookup opens. On one that does not, it is an ordinary file."""
    if name == IGNORE_FILE:
        return True
    if name.lower() != IGNORE_FILE:
        return False
    try:
        return os.path.samefile(os.path.join(root, name), os.path.join(root, IGNORE_FILE))
    except OSError:
        return False


def walk(root, exts=None, max_files=40000, include_hidden=False, github=False):
    """Yield (abs_path, rel_path) for files under root, skipping build and VCS directories.

    Hidden directories are skipped by default. This matters more than it looks: a catalogue
    installed into `.agents/` or `.claude/` is a COPY of the same definitions, and counting both
    triples the apparent size of the project. `include_hidden=True` counts the copies too, and
    the screen reports the difference rather than silently picking one. `.github` holds workflows
    and issue templates that a reader and a CI run both read, so `github=True` keeps it in a walk
    that otherwise skips hidden directories. Only `.git` itself is a version-control directory.
    """
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Sorted, so evidence order is the same on every filesystem and the committed example
        # is reproducible byte for byte.
        dirnames[:] = [d for d in sorted(dirnames)
                       if d not in SKIP_DIRS
                       and (include_hidden or not d.startswith(".") or (github and d == ".github"))]
        for name in sorted(filenames):
            # The project's ignore file is read by the signal alone: in no detector's hit, copy or
            # file budget, so a repository cannot use it to push a real finding past a limit.
            if dirpath == root and _is_ignore_file(root, name):
                continue
            if exts and os.path.splitext(name)[1].lower() not in exts:
                continue
            p = os.path.join(dirpath, name)
            # Pipes, sockets and devices, or links to them, are never opened: reading one can
            # hang the screen or never end.
            if not os.path.isfile(p):
                continue
            # Forward slashes on every OS, so a scorecard built on Windows is identical to one
            # built on Linux and every path pattern below means the same thing everywhere.
            if n >= max_files:
                reached("file walk", max_files)
                return
            yield p, os.path.relpath(p, root).replace(os.sep, "/")
            n += 1


def read_counted(path, limit=2_000_000):
    """(text, characters consumed). The text is up to `limit` characters with a final line the
    limit cut in two dropped, so detection and evidence see whole lines only. The count is what
    was read before that trimming, for a caller that keeps a budget."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(limit)
            used = len(text)
            if used == limit and fh.read(1) not in ("", "\n") and not text.endswith("\n"):
                text = text[:text.rfind("\n") + 1]
            return text, used
    except OSError:
        return "", 0


def read_text(path, limit=2_000_000):
    """The file's text up to `limit` characters, whole lines only."""
    return read_counted(path, limit)[0]


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                             timeout=60)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    keys, current = {}, None
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            current = m.group(1)
            keys[current] = m.group(2).strip().lstrip(">|").strip()
        elif current and line.strip():
            keys[current] = (keys[current] + " " + line.strip()).strip()
    return keys


def grep(root, patterns, exts=TEXT_EXT, max_hits=40, detector=None, count_only=False):
    """Return [(label, rel_path, line_no, line)] for each pattern hit. The line is stripped and
    whole, because callers judge the text; ev() withholds a line that holds a secret before it is cut."""
    hits = []
    for hit in iter_grep(root, patterns, exts):
        if len(hits) >= max_hits:
            if detector:
                reached(detector, max_hits, count_only)
            break
        hits.append(hit)
    return hits


def iter_grep(root, patterns, exts=TEXT_EXT):
    """Yield (label, rel_path, line_no, line) for each pattern hit, in a stable order."""
    compiled = [(label, re.compile(pat)) for label, pat in patterns]
    for path, rel in walk(root, exts, github=True):
        if os.path.getsize(path) > 2_000_000:
            continue
        text = read_text(path)
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for label, rx in compiled:
                if rx.search(line):
                    yield (label, rel, i, line.strip())


# ----------------------------------------------------------------------------- classify

def _identity(rel):
    """Identity of a definition: its own directory name, or its file stem for flat files.

    Large catalogues carry the same definition many times over — translations under docs/<lang>/,
    installed copies under hidden directories, vendored mirrors. Counting files answers "how many
    files"; counting identities answers "how many distinct things this project offers", which is
    what every published skill or agent count means.
    """
    base = os.path.basename(rel)
    if base.lower() in ("skill.md", "skills.md"):
        return os.path.basename(os.path.dirname(rel)).lower()
    return os.path.splitext(base)[0].lower()


def dedupe(rels):
    """Return (unique_identities, copy_count, duplicate_roots)."""
    seen, dupes, roots = {}, 0, {}
    for rel in rels:
        key = _identity(rel)
        if key in seen:
            dupes += 1
            root = rel.split("/")[0] if "/" in rel else "."
            roots[root] = roots.get(root, 0) + 1
        else:
            seen[key] = rel
    return sorted(seen), dupes, dict(sorted(roots.items(), key=lambda kv: -kv[1])[:5])


def find_skill_files(root, include_hidden=False):
    out = []
    for path, rel in walk(root, {".md"}, include_hidden=include_hidden):
        base = os.path.basename(path).lower()
        if base in ("skill.md", "skills.md"):
            out.append(rel)
        elif base.endswith(".md") and os.path.basename(os.path.dirname(path)).lower() in (
                "skills", "prompts", "rules"):
            fm = frontmatter(read_text(path, 4000))
            if "description" in fm and "name" in fm:
                out.append(rel)
    return sorted(set(out))


def find_agent_files(root, include_hidden=False):
    """Agent definitions are found by shape, not by path: a definition that declares a tool
    surface and is not itself a skill or a command. Commands frequently declare tools too, so
    path-based exclusion of commands/ and skills/ is what keeps the three categories apart."""
    out = []
    for path, rel in walk(root, {".md"}, include_hidden=include_hidden):
        parts = {p.lower() for p in rel.split("/")}
        if parts & {"commands", "skills"} or os.path.basename(path).lower() == "skill.md":
            continue
        looks_agenty = bool(parts & {"agents", "subagents", "personas", "roles"})
        fm = frontmatter(read_text(path, 4000))
        if looks_agenty and fm.get("description"):
            out.append(rel)
        elif fm and ("tools" in fm or "allowed-tools" in fm) and "model" in fm:
            out.append(rel)
    return sorted(set(out))


def classify(root):
    # Hidden directories are searched here, not skipped: `.claude/agents/` and `.agents/skills/`
    # are where several hosts expect definitions to live, and a scan that ignores them reports a
    # project with fifteen agents as having none. Duplicates are collapsed by identity instead.
    skills = find_skill_files(root, include_hidden=True)
    agents = find_agent_files(root, include_hidden=True)
    commands = [rel for _, rel in walk(root, {".md", ".toml"}, include_hidden=True)
                if "commands" in {p.lower() for p in rel.split("/")}]
    evidence, scores = [], {k: 0.0 for k in
                           ("catalogue", "harness", "orchestrator", "tool", "application")}

    if skills:
        scores["catalogue"] += 3
        scores["harness"] += 2
        unique, copies, _roots = dedupe(skills)
        evidence.append(ev("file",
                           f"{len(unique)} distinct skill definitions"
                           + (f" ({copies} duplicate copies)" if copies else ""),
                           ", ".join(skills[:3]) + ("…" if len(skills) > 3 else "")))
    if agents:
        scores["orchestrator"] += 1.5
        scores["harness"] += 1
        uagents, acopies, _r = dedupe(agents)
        evidence.append(ev("file",
                           f"{len(uagents)} distinct agent definitions declaring tools"
                           + (f" ({acopies} duplicate copies)" if acopies else ""),
                           ", ".join(agents[:3])))

    installers = [rel for _, rel in walk(root, {".sh", ".js", ".py"})
                  if re.search(r"(install|add)[-_]?(skills?|plugin|agents?)", rel, re.I)]
    if installers:
        scores["catalogue"] += 2
        evidence.append(ev("file", "install script", installers[0]))

    checkers = [rel for _, rel in walk(root, {".sh", ".js", ".py", ".ts"})
                if re.search(r"(^|/)(tools|scripts|bin)/.*(check|lint|validate|gate|guard)",
                             rel, re.I)]
    if checkers:
        # Checkers make a catalogue into a harness. Without a catalogue they are just scripts,
        # which nearly every repository has, so they cannot carry the harness classification on
        # their own — an early version called six ordinary applications harnesses this way.
        scores["harness" if skills else "tool"] += 2 if skills else 0.5
        evidence.append(ev("file", f"{len(checkers)} checker scripts", checkers[0]))

    gov = [n for n in ("RELEASES.md", "GOVERNANCE.md", "MAINTAINERS.md", "SECURITY.md",
                       "CHANGELOG.md", "RECORDS.md") if os.path.exists(os.path.join(root, n))]
    if gov:
        scores["harness" if skills else "application"] += 1.5 if skills else 0.5
        evidence.append(ev("file", "governance documents", ", ".join(gov)))

    orch_hits = grep(root, [("orchestration",
                             r"(?i)\b(session|queue|sandbox|permission|dispatch)"
                             r"\w*\s*(manager|registry|pool|store|policy)\b")],
                     {".py", ".js", ".ts", ".go", ".rs"}, max_hits=5)
    if orch_hits:
        scores["orchestrator"] += 2.5
        evidence.append(ev("file", f"{orch_hits[0][1]}:{orch_hits[0][2]}", orch_hits[0][3]))

    for manifest in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod"):
        p = os.path.join(root, manifest)
        if os.path.exists(p):
            text = read_text(p, 4000)
            if manifest == "package.json" and ('"bin"' in text or '"main"' in text):
                scores["tool"] += 2
            else:
                scores["tool"] += 1
            evidence.append(ev("file", manifest, clip(text.splitlines()[0], 100) if text else ""))
            break

    app_markers = [rel for _, rel in walk(root, {".html", ".tsx", ".jsx", ".vue", ".svelte"})][:5]
    if len(app_markers) >= 3:
        scores["application"] += 2.5
        evidence.append(ev("file", "application sources", ", ".join(app_markers[:3])))
    if os.path.exists(os.path.join(root, "Dockerfile")) or \
            os.path.exists(os.path.join(root, "docker-compose.yml")):
        scores["application"] += 0.5
        scores["tool"] += 0.5

    if not skills:
        scores["harness"] = 0.0
        if scores["catalogue"] < 2:
            scores["catalogue"] = 0.0

    best = max(scores, key=scores.get)
    archetype = best if scores[best] >= 2 else "unknown"
    return archetype, scores, evidence, {"skills": skills, "agents": agents,
                                         "commands": sorted(set(commands))}


# ----------------------------------------------------------------------------- integrity

def hidden_char_hits(root):
    """Invisible and direction-changing characters in text an agent reads.

    Two exclusions, both learned from real repositories: a byte-order mark at the start of a file
    or line is an encoding artifact, not a hiding place; and sanitiser code that inserts a
    zero-width character on purpose is the defence against this, not an instance of it.
    """
    hits = []
    for path, rel in walk(root, TEXT_EXT, github=True):
        text = read_text(path, 500_000)
        for i, line in enumerate(text.splitlines(), 1):
            probe = line.lstrip("\ufeff")
            m = HIDING_RE.search(probe)
            if m and not defensive(root, rel, i, line) and not FIXTURE_PATH_RE.search(rel):
                cps = " ".join(f"U+{ord(c):04X}" for c in set(HIDING_RE.findall(probe) or m.group()))
                if len(hits) >= 25:
                    reached("hidden characters", 25)
                    return hits
                hits.append((rel, i, cps, clip(line, 120)))
    return hits


# A repository that defends against a practice has to name it. Denylists, sanitisers, security
# guides and test fixtures all contain the exact strings a naive scanner hunts for, and flagging
# them as findings is how a scanner loses its reader. Every pattern sweep below runs its hits
# through this test first.
DEFENSIVE_CONTEXT = re.compile(
    r"(?i)(deny|denies|denied|reject|refus|block|forbid|disallow|never |do not |don't |"
    r"require.{0,20}(review|approval)|sanitiz|sanitis|redact|strip|escape|sentinel|guard|"
    r"detect|warn|lint|policy|rule:|allowlist|blocklist|injection|untrusted|malicious)")


def defensive(root, rel, lineno, line, window=3):
    """True when a hit sits inside text that is fighting the thing, not doing it."""
    if DEFENSIVE_CONTEXT.search(line):
        return True
    lines = read_text(os.path.join(root, rel), 500_000).splitlines()
    lo, hi = max(0, lineno - window), min(len(lines), lineno + window - 1)
    return bool(DEFENSIVE_CONTEXT.search(" ".join(lines[lo:hi])))


DISCUSSION_MARKERS = re.compile(
    r"(?i)(injection|untrusted|malicious|attack|adversar|never follow|do not follow|ignore any|"
    r"e\.g\.|example|such as|detect|guard|defen[cs]e|refuse|treat .{0,20}as data|prompt-?inject)")


DIRECTED_LIMIT = 25


def evaluator_directed_hits(root, limit=DIRECTED_LIMIT, judged_quoted=None):
    """Text addressed to whatever is reading the repository, minus the text the tool judges to be
    defensive or quoted from its surroundings.

    Every repository with good security guidance quotes the attack it defends against. Three
    clean repositories tripped this check in testing before the context test was added, and a
    critical flag that fires on good practice trains people to ignore it. The judgement is made
    from nearby words, so an author can write them on purpose. A hit set aside is therefore
    appended to the list passed as `judged_quoted`, and the screen lists it at information level.
    """
    # The limit applies after the defensive-text test, separately inside and outside test paths,
    # so early test strings cannot hide a later instruction.
    # Case-only matches have their own lists, so they cannot use up the room an original-case hit needs.
    sides = {False: ([], []), True: ([], [])}
    cached = (None, [])
    for label, rel, lineno, line in iter_grep(
            root, [("evaluator-directed", p) for p in EVALUATOR_DIRECTED],
            TEXT_EXT | {".json", ".yaml", ".yml"}):
        if cached[0] != rel:
            cached = (rel, read_text(os.path.join(root, rel), 500_000).splitlines())
        text = cached[1]
        lo, hi = max(0, lineno - 3), min(len(text), lineno + 2)
        context = " ".join(text[lo:hi])
        quoted = bool(re.search(r"[\"“‘'`].{0,40}(ignore|disregard|score|rate)", line, re.I))
        if DISCUSSION_MARKERS.search(context) or quoted:
            if judged_quoted is not None and not any(q[1:3] == (rel, lineno) for q in judged_quoted[-1:]):
                judged_quoted.append((label, rel, lineno, line))  # one entry per line, whatever matched it
            continue
        folded = not any(re.search(q[4:], line) for q in EVALUATOR_DIRECTED)
        if folded:
            label = "evaluator-directed-folded"  # matches only with case ignored
        side = sides[folded][bool(TEST_PATH_RE.search(rel))]
        if len(side) < limit:
            side.append((label, rel, lineno, line))
        else:  # a warning listing has no band effect, so its limit is a count and raises no flag
            reached("evaluator-directed text", limit, count_only=folded)
    return sides[False][0] + sides[False][1] + sides[True][0] + sides[True][1]


def _normalised_hash(data):
    """Hash of a text file with provenance and licence lines removed and whitespace collapsed,
    so a copy that gained a source line at the top still matches the file it came from."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    kept = [" ".join(line.split()) for line in text.splitlines()
            if line.strip() and not PROVENANCE_RE.search(line) and not LICENCE_LINE_RE.match(line)]
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest() if kept else None


def _source_licence(corpus, rel):
    """The licence of the corpus project a file came from: the file's own declaration if it has
    one, else the nearest licence file above it inside the corpus."""
    path = os.path.join(corpus, rel)
    own = declared_licences(read_text(path, 200_000))
    if own:
        return own[0][1], "the file's own declaration", _project_of(rel), own[0][4]
    parts = rel.split("/")[:-1]
    while True:
        here = os.path.join(corpus, *parts) if parts else corpus
        found = _licence_file_in(here)
        if found:
            label = identify_licence(read_text(os.path.join(here, found), 20000))
            where = "/".join(parts + [found])
            return label, f"corpus {where}", _project_of(rel), False
        if not parts:
            return None, "no licence file in the source project", _project_of(rel), False
        parts.pop()


def _project_of(rel):
    return rel.split("/")[0] if "/" in rel else "."


def _licence_file_in(directory):
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return None
    for name in names:
        if re.match(r"(?i)^(licen[cs]e|copying)(\.|$)", name) and \
                os.path.isfile(os.path.join(directory, name)):
            return name
    return None


ATTRIBUTION_FILE_RE = re.compile(r"(?i)^(notice|third[-_ ]?party[\w.-]*|credits|acknowledg\w*|"
                                 r"attribution\w*)(\.\w+)?$")


def attribution_for(root, rel, source_project):
    """Where a copied file's credit lives, or None. The file's own source or licence line, a
    licence file beside it or above it below the root, or a root NOTICE, third-party, credits or
    attribution file naming the source project. A README mention is too loose to count."""
    text = read_text(os.path.join(root, rel), 200_000)
    head = text.splitlines()[:15]
    for i, line in enumerate(head, 1):
        if PROVENANCE_RE.search(line) or LICENCE_LINE_RE.match(line) or \
                re.search(r"(?i)\bcopyright\b|licensed under", line):
            return f"{rel}:{i}"
    parts = rel.split("/")[:-1]
    while parts:
        found = _licence_file_in(os.path.join(root, *parts))
        if found:
            return "/".join(parts + [found])
        parts.pop()
    name = os.path.basename(source_project.rstrip("/")) if source_project != "." else None
    for fname in sorted(os.listdir(root)):
        if ATTRIBUTION_FILE_RE.match(fname) and name and os.path.isfile(os.path.join(root, fname)):
            if name.lower() in read_text(os.path.join(root, fname), 200_000).lower():
                return fname
    return None


def corpus_duplicates(root, corpus, min_bytes=400, limit=200):
    """Content-hash every file in corpus once, then report submission files that match, either
    byte for byte or once provenance and licence lines are set aside. Each match carries the
    source project's licence and where the copy credits it, if anywhere."""
    index, normalised = {}, {}
    for path, rel in walk(corpus, None, max_files=200000):
        try:
            if os.path.getsize(path) < min_bytes:
                continue
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        index.setdefault(hashlib.sha256(data).hexdigest(), rel)
        n = _normalised_hash(data)
        if n:
            normalised.setdefault(n, rel)

    dups, checked = [], 0
    for path, rel in walk(root, None, github=True):
        try:
            size = os.path.getsize(path)
            if size < min_bytes:
                continue
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        checked += 1
        h, how = hashlib.sha256(data).hexdigest(), "identical"
        match = index.get(h)
        if match is None:
            n = _normalised_hash(data)
            match = normalised.get(n) if n else None
            how = "identical apart from provenance and licence lines"
        if match is None:
            continue
        licence, found_in, project, hidden = _source_licence(corpus, match)
        if len(dups) >= limit:
            reached("corpus duplicates", limit)
            break
        dups.append({"file": rel, "bytes": size, "corpus_match": match, "match": how,
                     "source_project": project, "source_licence": WITHHELD if hidden else licence or "none",
                     "source_licence_found": found_in,
                     "source_class": licence_class(licence),
                     "attribution": attribution_for(root, rel, project)})
    return dups, checked, len(index)


def history_facts(root):
    if not os.path.isdir(os.path.join(root, ".git")):
        return {"available": False, "reason": "no git directory — history cannot be measured"}
    if git(root, "rev-parse", "--is-shallow-repository") == "true":
        return {"available": False, "shallow": True,
                "reason": "shallow clone: the history present is an artifact of how it was "
                          "fetched, not of how it was written. Re-clone with full history to "
                          "measure provenance."}
    count = git(root, "rev-list", "--count", "HEAD")
    authors = git(root, "log", "--format=%ae")
    first = git(root, "log", "--reverse", "--format=%H %aI", "--max-parents=0")
    first_sha = first.split()[0] if first else ""
    first_date = first.split()[1] if len(first.split()) > 1 else ""
    last_date = git(root, "log", "-1", "--format=%aI")
    first_files = git(root, "show", "--name-only", "--format=", first_sha) if first_sha else ""
    committer_vs_author = git(
        root, "log", "--format=%aI|%cI", "-50")
    drift = 0
    for line in committer_vs_author.splitlines():
        if "|" in line:
            a, c = line.split("|", 1)
            if a[:10] != c[:10]:
                drift += 1
    return {
        "available": True,
        "commits": int(count) if count.isdigit() else None,
        "authors": len({a for a in authors.splitlines() if a}),
        "first_commit": first_sha[:12],
        "first_commit_date": first_date,
        "last_commit_date": last_date,
        "first_commit_files": len([f for f in first_files.splitlines() if f]),
        "author_committer_date_drift": drift,
    }


def spdx_labels(line):
    """The copyleft families an SPDX line names, or None for any other line. Every identifier
    counts whatever joins it: the check reads names and a person reads AND and OR. The word after
    WITH names an exception, not a licence."""
    m = re.search(r"SPDX-License-Identifier:\s*([\w.+:()\s-]*)", line)
    if not m:
        return None
    ids = re.findall(r"[\w.+:-]+", re.sub(r"\bWITH\s+\S+", "", m.group(1), flags=re.I))
    return {label for label, _ in COPYLEFT_MARKERS for i in ids if i.upper().startswith(label)}


def licence_facts(root):
    declared, declared_file = None, None
    for name in sorted(os.listdir(root)):
        if re.match(r"(?i)^(licen[cs]e|copying)(\.|$)", name):
            declared_file = name
            declared = identify_licence(read_text(os.path.join(root, name), 20000))
            break
    nested = []
    for path, rel in walk(root, {".md", ".txt", ""}, github=True):
        base = os.path.basename(path)
        if re.match(r"(?i)^(licen[cs]e|copying)(\.|$)", base) and rel != declared_file:
            nested.append(rel)
    # Only a licence FILE or an SPDX header counts. Prose that mentions GPL — a list of licence
    # options, a comparison table, a question in a wizard — is not redistribution of GPL code,
    # and treating it as one produced a critical flag on three clean repositories in testing.
    copyleft_inside, live_hits = [], 0
    for path, rel in walk(root, None, github=True):
        if live_hits >= 15:  # hits under a test path do not use this budget
            reached("copyleft licence text", 15)
            break
        base = os.path.basename(path)
        is_licence_file = bool(re.match(r"(?i)^(licen[cs]e|copying|notice)(\.|$)", base))
        if not is_licence_file and os.path.splitext(base)[1].lower() not in TEXT_EXT:
            continue
        if os.path.getsize(path) > 500_000:
            continue
        text = read_text(path, 200_000)
        for label, pat in COPYLEFT_MARKERS:
            for i, line in enumerate(text.splitlines()[:400], 1):
                labels = spdx_labels(line)
                if label in labels if labels is not None else is_licence_file and re.search(pat, line):
                    copyleft_inside.append((label, rel, i, clip(line)))
                    live_hits += not TEST_PATH_RE.search(rel)
                    break
    return {"declared": declared, "declared_file": declared_file,
            "nested_licences": nested[:20], "copyleft_hits": copyleft_inside}


def identify_licence(text):
    """The licence a licence file's text is, by its known markers, or None."""
    for label, pat in PERMISSIVE_MARKERS + COPYLEFT_MARKERS + OTHER_LICENCE_MARKERS:
        if re.search(pat, text):
            return label
    return None


def licence_class(name):
    """Sort a licence name into the classes the provenance check acts on.

    permissive     MIT, Apache-2.0, BSD, ISC and the like: copy, keeping licence and credit
    share-alike    GPL, AGPL, CC-BY-SA, EUPL: copying passes the licence on to the whole work
    weak-copyleft  LGPL, MPL, EPL: file- or library-level conditions a person should read
    not-osi        open, but not an OSI licence (CC-BY): terms a person should read
    restricted     non-commercial, no-derivatives, source-available, proprietary, unlicensed
    none           no licence found, which means all rights reserved
    unknown        a name this table does not know
    """
    if not name or not str(name).strip():
        return "none"
    n = re.sub(r"[\s_]+", "-", str(name).strip().upper())
    n = re.sub(r"-LICEN[CS]E$", "", n)
    if re.search(r"NOASSERTION", n):
        return "unknown"
    if re.search(r"(^|-)(NC|ND)(-|$)|NON-?COMMERCIAL|NO-?DERIV|BUSL|BUSINESS-SOURCE|POLYFORM|SSPL|"
                 r"ELASTIC|COMMONS-CLAUSE|PROPRIETARY|ALL-RIGHTS-RESERVED|SOURCE-AVAILABLE|"
                 r"^UNLICENSED$|CONFIDENTIAL", n):
        return "restricted"
    if re.search(r"^(A|L)?GPL|^AGPL|GNU-(AFFERO|GENERAL)|CC-BY-SA|EUPL|^OSL", n) and \
            not re.search(r"^LGPL|GNU-LESSER", n):
        return "share-alike"
    if re.search(r"^LGPL|GNU-LESSER|^MPL|MOZILLA|^EPL|ECLIPSE|^CDDL", n):
        return "weak-copyleft"
    if re.search(r"^CC-BY(-\d|$)", n):
        return "not-osi"
    if re.search(r"^(MIT(-0)?|APACHE(-LICENSE)?(-2(\.0)?)?|BSD.*|0BSD|ISC|ZLIB|UNLICENSE|"
                 r"CC0.*|BSL-1\.0|BOOST.*|PYTHON-2\.0|PSF.*)$", n):
        return "permissive"
    return "unknown"


# A provenance line: "source: <url> @ <commit>, licence: <name>" and its common variants. The
# URL must be real, so a template with <placeholders> in a guide does not count as a declaration.
PROVENANCE_RE = re.compile(
    r"(?i)^\s*(?:[#>*/;-]+\s*|<!--\s*)?(?:source|copied from|vendored from|adapted from|upstream)"
    r"\s*[:=]\s*(https?://[^\s<>]+|(?:github|gitlab|codeberg)\.(?:com|org)/[^\s<>]+)")
LICENCE_IN_LINE_RE = re.compile(r"(?i)\blicen[cs]e\s*[:=]\s*([A-Za-z0-9][A-Za-z0-9.+\- ]{1,40})")
LICENCE_LINE_RE = re.compile(r"(?i)^\s*(?:[#>*/;-]+\s*)?(?:licen[cs]e\s*:|SPDX-License-Identifier:)")
SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+\-]+(?:\s+(?:OR|AND|WITH)\s+"
                     r"[A-Za-z0-9.+\-]+)*)")


DATA_EXT = {".yaml", ".yml", ".json", ".toml", ".csv", ".jsonl"}


def declared_licences(text, data_file=False):
    """[(line, licence, kind, source)] for every licence a file declares about itself: its
    frontmatter licence key, a provenance line in its header, or an SPDX header. Prose is never
    read. A provenance line counts only in the header, the frontmatter and the few lines after
    it, because that is where the convention puts it, and a `source:` key deeper in a document
    or anywhere in a data file is a field, not a statement about where the file came from."""
    out = []
    lines = text.splitlines()
    end = None
    if text.startswith("---"):
        end = next((i for i, ln in enumerate(lines[1:60], 1) if ln.strip() == "---"), None)
        for i in range(1, end or 0):
            m = re.match(r"(?i)^licen[cs]e:\s*['\"]?([^'\"#]+?)['\"]?\s*$", lines[i])
            if m and "<" not in m.group(1):
                out.append((i + 1, m.group(1).strip(), "frontmatter", None, holds_secret(lines[i])))
    header = (end + 1 if end else 0) + 8
    for i, line in enumerate(lines[:400], 1):
        hidden = holds_secret(line)
        m = PROVENANCE_RE.search(line) if i <= header and not data_file else None
        if m:
            lic = LICENCE_IN_LINE_RE.search(line[m.end():])
            name = lic.group(1).strip().rstrip(".,;") if lic and "<" not in lic.group(1) else None
            out.append((i, name, "source line", m.group(1).rstrip(".,;)"), hidden))
            continue
        m = SPDX_RE.search(line)
        if m:
            out.append((i, m.group(1), "SPDX header", None, hidden))
    return out


def provenance_facts(root):
    """Every file that declares a licence of its own or a source it was copied from."""
    records = []
    for path, rel in walk(root, TEXT_EXT, github=True):
        if len(records) >= 400:
            reached("declared licences", 400)
            break
        try:
            if os.path.getsize(path) > 500_000:
                continue
        except OSError:
            continue
        data_file = os.path.splitext(path)[1].lower() in DATA_EXT
        for line, licence, kind, source, hidden in declared_licences(read_text(path, 500_000), data_file):
            records.append({"file": rel, "line": line, "licence": WITHHELD if hidden else licence or "not stated",
                            "class": licence_class(licence) if licence else "unknown",
                            "kind": kind, "source": WITHHELD if hidden and source else source})
    return records


FUTURE_RE = re.compile(r"(?i)(plans?(ned)? to|will (add|ship|include|have|offer)|roadmap|going to)")
NOT_COUNT_AFTER_RE = re.compile(r"\s*(?i:categor|levels?\b)")


def _not_a_count(text, m):
    """A figure followed by 'categories' or 'levels', or in a sentence about a future plan, is not a
    count of what the tree ships."""
    if NOT_COUNT_AFTER_RE.match(text, m.end()):
        return True
    sentence = re.split(r"[.!?]\s|\n", text[:m.start()])[-1]
    return bool(FUTURE_RE.search(sentence))


def extract_claims(root):
    """Claims the project makes about itself, from its README."""
    claims = []
    for name in sorted(os.listdir(root)):
        if re.match(r"(?i)^readme(\.|$)", name):
            text = read_text(os.path.join(root, name), 200000)
            # "Works with 15 agents" is a compatibility claim about hosts, not an inventory
            # claim about definitions. Reading it as inventory produced a false contradiction
            # against a clean repository, so context decides which kind of claim it is.
            compat = re.compile(r"(?i)(works? with|compatible|support(s|ed)?|runs? on|across|"
                                r"funciona con|available (in|on)|integrat)")
            for label, pat in CLAIM_PATTERNS:
                for m in re.finditer(pat, text):
                    if label in ("skills", "agents", "commands") and _not_a_count(text, m):
                        continue
                    ctx = text[max(0, m.start() - 80):m.end() + 40]
                    claims.append({"claim": m.group(0).strip(), "kind": label,
                                   "location": f"{name}", "status": "unchecked",
                                   "kind_of_claim": "compatibility" if compat.search(ctx)
                                                    else "inventory"})
            for label, pat in UNSUPPORTABLE_CLAIMS:
                for m in re.finditer(pat, text, re.I):
                    claims.append({"claim": m.group(0).strip(), "kind": label,
                                   "location": f"{name}", "status": "unchecked"})
            break
    # de-duplicate, keep order
    seen, out = set(), []
    for c in claims:
        key = (c["kind"], c["claim"].lower())
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out[:40]


# ----------------------------------------------------------------------------- screen

IGNORE_FILE = ".scanignore"
PATTERN_TEXT_RE = re.compile(r"^[\w./*?!\[\]-]{1,200}\Z")
PATTERN_WITHHELD = "<pattern withheld>"
PATTERNS_SHOWN = 50


def ignore_patterns(root):
    """Patterns from the project's own .scanignore, one per line, # for comments.

    A pattern ending in / excludes a directory prefix; anything else is a glob matched against
    the path from the project root. The file does not hide anything: findings under an excluded
    path are still reported, downgraded to information and marked, but only when the person
    screening passes --honour-ignore. By default the patterns are a signal and change no flag.
    A symlink is refused: its target's lines would print on the card.
    """
    path = os.path.join(root, IGNORE_FILE)
    if os.path.islink(path) or not os.path.isfile(path):
        return []
    out = []
    for line in read_text(path, 20000).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def is_ignored(rel, patterns):
    for pat in patterns:
        if pat.endswith("/"):
            if rel == pat[:-1] or rel.startswith(pat):
                return True
        elif fnmatch.fnmatch(rel, pat):
            return True
    return False


def _evidence_path(e):
    if e.get("kind") != "file":
        return None
    ref = e.get("ref", "")
    head, _, tail = ref.rpartition(":")
    return head if head and tail.isdigit() else ref


# Flags a project's own ignore file cannot lower. The text is aimed at the evaluator, so a
# project that excluded it would be choosing whether the evaluator is told. --honour-ignore
# changes nothing for these, and every other flag keeps the downgrade rule above.
NEVER_EXCLUDED = {"evaluator-directed-text"}


def apply_ignore(flags, patterns):
    """Downgrade, never drop. Returns (flags, number of evidence items that were in excluded paths)."""
    if not patterns:
        return flags, 0
    moved, out = 0, []
    for f in flags:
        if f["id"] in NEVER_EXCLUDED and f["severity"] == "critical":
            out.append(f)
            continue
        kept, excluded = [], []
        for e in f.get("evidence", []):
            p = _evidence_path(e)
            (excluded if p and is_ignored(p, patterns) else kept).append(e)
        moved += len(excluded)
        if not excluded:
            out.append(f)
            continue
        if kept:
            f = {**f, "evidence": kept,
                 "detail": (f.get("detail", "") + f" {len(excluded)} more in paths the project "
                            f"excludes, shown separately.").strip()}
            out.append(f)
        out.append({
            "id": f["id"], "severity": "info",
            "title": f"In a path the project excludes: {f['title']}",
            "detail": f"Downgraded from {f['severity']} because the person screening asked "
                      f"(--honour-ignore) to apply {IGNORE_FILE}. Without that option these "
                      f"findings count at full severity.",
            "excluded": True, "original_severity": f["severity"],
            "evidence": excluded,
        })
    return out, moved


def _now():
    """The current time, or QUIET_COUNSEL_NOW when set. Tests and the committed example use it, so a
    scorecard built twice from the same tree is byte-identical and can be diffed in CI."""
    fixed = os.environ.get("QUIET_COUNSEL_NOW")
    if fixed:
        return _dt.datetime.fromisoformat(fixed.replace("Z", "+00:00"))
    return _dt.datetime.now(_dt.timezone.utc)


def screen(root, corpus=None, event=None, honour_ignore=False):
    _REACHED.clear()
    _NOTES.clear()
    started = _now()
    given = root
    root = os.path.abspath(root)
    archetype, arch_scores, arch_ev, found = classify(root)
    signals, flags, limits = {}, [], []

    # --- methodology signals
    skills = found["skills"]
    unique_skills, skill_copies, skill_copy_roots = dedupe(skills)
    hidden_files = skills
    signals["skill_definitions"] = sig(
        len(unique_skills), "distinct skill identities (directory name), hidden dirs excluded")
    signals["skill_definition_files"] = sig(
        len(skills), "raw SKILL.md file count, hidden dirs excluded")
    if skill_copies or len(hidden_files) > len(skills):
        signals["duplicate_definition_copies"] = sig(
            {"within_tree": skill_copies, "under_hidden_dirs": len(hidden_files) - len(skills),
             "top_copy_roots": skill_copy_roots},
            "same identity appearing more than once",
            note="translations, installed copies and vendored mirrors. A published count that "
                 "includes them overstates the catalogue.")
    unique_agents, agent_copies, _ = dedupe(found["agents"])
    signals["agent_definitions"] = sig(
        len(unique_agents), "distinct agent identities declaring a tool surface",
        note=(f"{agent_copies} duplicate copies also found" if agent_copies else None))
    unique_cmds, cmd_copies, _ = dedupe(found["commands"])
    signals["command_definitions"] = sig(
        len(unique_cmds), "distinct command identities",
        note=(f"{cmd_copies} duplicate copies also found" if cmd_copies else None))

    desc_chars, nonspec, declared_tools, no_when = 0, {}, 0, 0
    SPEC = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}
    # Cost is counted once per distinct definition. A host loads one copy of each skill, so
    # summing translations and installed mirrors would report a context cost nobody pays.
    first_of_identity, _seen = [], set()
    for rel in skills:
        key = _identity(rel)
        if key not in _seen:
            _seen.add(key)
            first_of_identity.append(rel)
    for rel in first_of_identity:
        fm = frontmatter(read_text(os.path.join(root, rel), 20000))
        d = fm.get("description", "")
        desc_chars += len(d)
        if "when" not in d.lower():
            no_when += 1
        if "allowed-tools" in fm or "tools" in fm:
            declared_tools += 1
        for k in fm:
            if k not in SPEC:
                nonspec[k] = nonspec.get(k, 0) + 1
    signals["always_loaded_description_chars"] = sig(
        desc_chars, "sum of description frontmatter, one copy per distinct definition")
    signals["always_loaded_description_tokens_est"] = sig(desc_chars // 4, "chars / 4",
                                                          note="estimate")
    signals["descriptions_without_when"] = sig(no_when, "description lacking 'when'")
    signals["definitions_declaring_tools"] = sig(declared_tools, "allowed-tools or tools key")
    signals["non_spec_frontmatter_keys"] = sig(nonspec, "frontmatter keys outside the spec")

    rulebook = {}
    for name in RULEBOOKS:
        p = os.path.join(root, name)
        if os.path.exists(p):
            rulebook[name] = os.path.getsize(p)
    signals["always_loaded_rulebook_bytes"] = sig(rulebook, "wc -c on root instruction files")

    # --- evidence signals
    test_files = [rel for _, rel in walk(root, {".py", ".js", ".ts", ".tsx", ".sh", ".go", ".rs"})
                  if re.search(r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.", rel)]
    signals["test_files"] = sig(len(test_files), "files under tests/ or named *.test.*")
    eval_dirs = sorted({rel.split("/")[0] for _, rel in walk(root, {".md", ".json", ".jsonl", ".yaml", ".yml", ".csv"})
                        if re.search(r"(^|/)evals?/", rel)})
    signals["eval_dirs"] = sig(eval_dirs, "directories named eval/ or evals/")
    wf_dir = os.path.join(root, ".github", "workflows")
    workflows = sorted(os.listdir(wf_dir)) if os.path.isdir(wf_dir) else []
    signals["ci_workflow_files"] = sig(len(workflows), "ls .github/workflows")
    uses, pinned = 0, 0
    for w in workflows:
        for line in read_text(os.path.join(wf_dir, w), 200000).splitlines():
            m = re.search(r"uses:\s*([^\s]+)", line)
            if m:
                uses += 1
                if re.search(r"@[0-9a-f]{40}$", m.group(1)):
                    pinned += 1
    signals["ci_actions_pinned_by_digest"] = sig(f"{pinned}/{uses}" if uses else "0/0",
                                                 "uses: lines pinned to a 40-char digest")
    signals["jenkinsfile"] = sig(os.path.exists(os.path.join(root, "Jenkinsfile")), "test -f Jenkinsfile")

    # --- safety signals
    secret_hits = grep(root, SECRET_PATTERNS, TEXT_EXT | {".pem", ".key", ""}, max_hits=40,
                       detector="credential-shaped values")
    live, benign = [], []
    for h in secret_hits:
        label, rel, lineno, line = h
        looks_real = (label in HIGH_CONFIDENCE_SECRETS
                      and not FIXTURE_PATH_RE.search(rel)
                      and not PLACEHOLDER_RE.search(line))
        (live if looks_real else benign).append(h)
    signals["secret_pattern_hits"] = sig(
        {"high_confidence": len(live), "fixture_or_placeholder": len(benign)},
        "credential-shape sweep, split by confidence",
        note="fixtures, examples and documented placeholders match the same shapes as real keys")
    if live:
        flags.append({
            "id": "secret-in-tree", "severity": "critical",
            "title": f"{len(live)} credential-shaped string(s) outside test and example paths",
            "detail": "The lines are withheld here. Verify each before acting; a live credential "
                      "caps the safety group at 3 and should be rotated, not just deleted.",
            "caps": "safety<=3",
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3], f"[{h[0]}] ") for h in live[:5]],
        })
    elif benign:
        flags.append({
            "id": "credential-shaped-fixtures", "severity": "info",
            "title": f"{len(benign)} credential-shaped string(s), all in test, example or "
                     f"placeholder positions",
            "detail": "Reported for completeness. Not treated as a finding.",
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3], f"[{h[0]}] ") for h in benign[:3]],
        })

    def executable_context(label, rel, line):
        """A pattern quoted inside a denylist, a test string or a config array does not run."""
        if FIXTURE_PATH_RE.search(rel):
            return False
        if label == "curl-pipe-shell":
            stripped = re.sub(r"^(-\s+)?run:\s*", "", line.lstrip("$# \t`"))
            return bool(re.match(r"(sudo\s+)?(curl|wget)\b", stripped))
        return True

    # Filter first, then bound: a hit that is quoted or defensive must not use up the budget.
    supply, more, seen = [], False, 0
    for h in iter_grep(root, SUPPLY_CHAIN_PATTERNS, TEXT_EXT):
        seen += 1
        if seen > 2000:  # raw matches examined, so quoted lines cannot cost unbounded work
            more = True
            break
        if defensive(root, h[1], h[2], h[3]) or not executable_context(h[0], h[1], h[3]):
            continue
        if len(supply) >= 60:
            more = True
            break
        supply.append(h)
    if more:
        reached("supply-chain patterns", 60)
    signals["supply_chain_hits"] = sig(len(supply), "installer and TLS patterns")
    for label in sorted({h[0] for h in supply}):
        sample = [h for h in supply if h[0] == label][:3]
        # A pipe-to-shell line inside the project's own script is the project doing it; the same
        # line in a README is the project repeating a third-party vendor's install instruction.
        in_script = any(h[1].endswith((".sh", ".bash", ".zsh")) for h in supply if h[0] == label)
        sev = "warning"
        if label == "curl-pipe-shell":
            sev = "serious" if in_script else "warning"
        elif label == "tls-verification-off":
            sev = "serious"
        flags.append({
            "id": label, "severity": sev,
            "title": {"curl-pipe-shell": "Installer pipes a download into a shell",
                      "tls-verification-off": "Certificate verification disabled",
                      "commit-hook-bypass": "Commit-hook bypass present"}[label],
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3]) for h in sample],
        })

    lockfiles = [n for n in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
                             "requirements.txt", "Cargo.lock", "go.sum")
                 if os.path.exists(os.path.join(root, n))]
    signals["lockfiles"] = sig(lockfiles, "test -f on known lockfiles")

    untrusted = grep(root, [("untrusted-guidance",
                             r"(?i)(prompt injection|untrusted (content|input|text)"
                             r"|treat .{0,30}as data)")], TEXT_EXT, max_hits=6,
                     detector="untrusted-content guidance", count_only=True)
    signals["untrusted_content_guidance_hits"] = sig(len(untrusted), "guidance phrases")

    writes = host_config_writes(root)
    signals["host_config_writes"] = sig(
        len(writes), "code writing to host settings, hooks or CLAUDE.md, AGENTS.md, GEMINI.md",
        note=(f"{sum(1 for w in writes if not w[3])} in files with no confirmation, dry run or "
              "opt-in flag" if writes else None))
    ungated = [w for w in writes if not w[3]]
    if writes:
        flags.append({
            "id": "writes-host-config",
            "severity": "serious" if ungated else "warning",
            "title": "Writes to an agent host's settings or standing instructions"
                     + ("" if ungated else ", behind a confirmation or flag"),
            "detail": "Hooks, settings and instruction files change every later session. A write "
                      "the user did not confirm is how a tool ends up reading every prompt.",
            "evidence": [ev("file", f"{w[0]}:{w[1]}", w[2] + ("" if w[3] else "  [no gate in file]"))
                         for w in (ungated or writes)[:5]],
        })

    stale = stale_rulebook_paths(root)
    signals["rulebook_missing_paths"] = sig(
        len(stale), "paths named in root instruction files that do not exist")
    if stale:
        flags.append({
            "id": "stale-instructions", "severity": "warning",
            "title": f"Instruction files name {len(stale)} path(s) that do not exist",
            "detail": "An always-loaded file that points at missing paths sends every session "
                      "looking for them.",
            "evidence": [ev("file", f"{f}:{n}", ref) for f, n, ref in stale[:5]],
        })

    # imported here because checks.py reads this module's helpers
    from .checks import incident_flags
    flags.extend(incident_flags(root))

    hidden = hidden_char_hits(root)
    signals["hidden_character_hits"] = sig(len(hidden), "scan for zero-width, bidi, tag blocks")
    if hidden:
        flags.append({
            "id": "hidden-characters", "severity": "serious",
            "title": f"Hidden or direction-changing characters in {len(hidden)} line(s)",
            "detail": "These can hide text from a human reader while a model still reads it.",
            "evidence": [ev("file", f"{h[0]}:{h[1]}", h[3], f"{h[2]} in: ") for h in hidden[:5]],
        })

    quoted_hits = []
    directed = evaluator_directed_hits(root, judged_quoted=quoted_hits)
    folded = [h for h in directed if h[0] == "evaluator-directed-folded"]
    directed = [h for h in directed if h[0] != "evaluator-directed-folded"]
    outside = [h for h in directed if not TEST_PATH_RE.search(h[1])]
    if outside:
        shown = [ev("file", f"{h[1]}:{h[2]}", h[3]) for h in outside + [d for d in directed if d not in outside] + folded]
        if len(outside) >= DIRECTED_LIMIT:
            shown = shown[:4] + [ev("note", "evaluator-directed-text",
                                    f"listing stopped at the limit of {DIRECTED_LIMIT} hits outside "
                                    f"test paths; more may exist")]
        flags.append({
            "id": "evaluator-directed-text", "severity": "critical",
            "title": "Text in the submission addresses the evaluator",
            "detail": "Reported, never acted on. Scoring stops until a person rules on it.",
            "caps": "do-not-score",
            "evidence": shown[:5],
        })
    elif directed:
        flags.append({
            "id": "evaluator-directed-text", "severity": "serious",
            "title": "Text in a test path addresses the evaluator",
            "detail": "Every hit is under a test path, where a project keeps strings that defend "
                      "against this. Listed for a person to read; scoring is not stopped. A "
                      "project can place text under a test path to receive this lower severity.",
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3]) for h in (directed + folded)[:5]],
        })
    elif folded:
        flags.append({
            "id": "evaluator-directed-text", "severity": "warning",
            "title": "Text that may address the evaluator (matched with case ignored)",
            "detail": "The wording matches a phrase only when capital letters are ignored. On 100 "
                      "field repositories every critical or serious flag of this kind was ruled "
                      "false by one AI reader, so it is a warning: no cap and no effect on the "
                      "band. Listed for a person to read.",
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3]) for h in folded[:5]],
        })
    if quoted_hits:
        flags.append({
            "id": "quoted-evaluator-text", "severity": "info",
            "title": f"{len(quoted_hits)} line(s) addressed to the evaluator were judged quoted or "
                     f"defensive and do not stop scoring",
            "detail": "The tool judges this from the words around each line, and an author can "
                      "write those words on purpose. Read the listed lines to check the judgement. "
                      "Up to five are listed.",
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3]) for h in quoted_hits[:5]],
        })

    # --- integrity signals
    lic = licence_facts(root)
    signals["licence_declared"] = sig(lic["declared"] or "none",
                                      "root LICENSE file, matched against known texts")
    signals["nested_licence_files"] = sig(len(lic["nested_licences"]), "LICENSE files below root")
    if not lic["declared_file"]:
        flags.append({"id": "no-licence", "severity": "serious",
                      "title": "No licence file at the repository root",
                      "detail": "Without one, nobody may reuse the work.",
                      "evidence": [ev("command", f"ls {os.path.basename(root)} | grep -i licence",
                                      "no match")]})
    if lic["declared"] in {"MIT", "Apache-2.0", "BSD", "ISC"} and lic["copyleft_hits"]:
        hits = lic["copyleft_hits"]
        outside = [h for h in hits if not TEST_PATH_RE.search(h[1])]
        flag = {
            "id": "copyleft-in-permissive-tree", "severity": "critical",
            "title": f"Copyleft licence text inside a {lic['declared']}-licensed tree",
            "detail": "Redistribution may be non-compliant. These are facts only; a person rules.",
            "caps": "D1=0",
            "evidence": [ev("file", f"{h[1]}:{h[2]}", h[3], f"[{h[0]}] ")
                         for h in (outside + [d for d in hits if d not in outside])[:5]],
        }
        if not outside:
            flag.update(severity="warning", detail="Every hit is inside a test file, where a "
                        "project keeps licence strings it tests against. Listed for a person to "
                        "read. A project can place text under a test path to receive this lower "
                        "severity.")
            del flag["caps"]
        flags.append(flag)

    hist = history_facts(root)
    signals["history"] = sig(hist, "git rev-list / log")
    if not hist.get("available"):
        limits.append("Provenance was not measured: " + hist.get("reason", "no history"))
    if hist.get("available") and hist.get("first_commit_files", 0) > 200:
        flags.append({
            "id": "imported-first-commit", "severity": "warning",
            "title": f"First commit contains {hist['first_commit_files']} files",
            "detail": "Consistent with importing an existing project. Not wrong by itself.",
            "evidence": [ev("commit", hist["first_commit"],
                            f"{hist['first_commit_files']} files, {hist['first_commit_date']}")],
        })
    if event and hist.get("available"):
        start, end = event
        if hist.get("first_commit_date") and hist["first_commit_date"] < start:
            flags.append({
                "id": "work-predates-event", "severity": "warning",
                "title": "History begins before the stated event window",
                "evidence": [ev("commit", hist["first_commit"],
                                f"first commit {hist['first_commit_date']}, window opens {start}")],
            })

    if corpus:
        dups, checked, indexed = corpus_duplicates(root, corpus)
        signals["corpus_duplicate_files"] = sig(
            len(dups), f"sha256 match against {indexed} corpus files",
            note=f"{checked} submission files compared")
        if dups:
            flags.append({
                "id": "corpus-duplication", "severity": "warning" if len(dups) < 10 else "serious",
                "title": f"{len(dups)} file(s) identical to a corpus file",
                "detail": "Identical content, not paraphrase. Credited reuse is legitimate, so "
                          "check the licence dimension before concluding.",
                "evidence": [ev("file", d["file"], f"matches corpus: {d['corpus_match']}")
                             for d in dups[:5]],
            })
    else:
        limits.append("No corpus given, so duplication against known public projects was not "
                      "measured (--corpus DIR).")

    # --- third-party text: what the tree says about its own borrowed files, and, with a corpus,
    # what the copies it could match actually came from.
    declared = provenance_facts(root)
    proj_label = lic["declared"]
    proj_class = licence_class(proj_label)
    groups = {"share-alike": [], "restricted": [], "unattributed": [], "read": []}

    def same_licence(name):
        return proj_label and name and re.sub(r"[\W_]", "", name.upper()).startswith(
            re.sub(r"[\W_]", "", proj_label.upper()))

    # A closed project that marks its own files proprietary is stating its own terms. Terms that
    # forbid reuse count as third-party only when the file names a source, or when the project
    # itself is open, so the file's terms conflict with the licence the tree is published under.
    open_project = proj_class in {"permissive", "share-alike", "weak-copyleft", "not-osi"}
    for r in declared:
        where, what = f"{r['file']}:{r['line']}", f"[{r['licence']}] declared by {r['kind']}" + (
            f", source {r['source']}" if r["source"] else "")
        c = r["class"]
        if c == "permissive" or same_licence(r["licence"]):
            continue
        if c == "share-alike":
            if r["kind"] != "SPDX header":  # SPDX copyleft headers already raise the flag above
                groups["share-alike"].append(ev("file", where, what))
        elif not (r["source"] or open_project):
            continue
        elif c in {"restricted", "none"}:
            groups["restricted"].append(ev("file", where, what))
        else:
            groups["read"].append(ev("file", where, what + (
                "; no licence stated with the source" if r["licence"] == "not stated" else "")))
    copies = [d for d in (dups if corpus else []) if d.get("source_class")]
    for d in copies:
        what = (f"{d['match']} to corpus {d['corpus_match']}; source licence {d['source_licence']} "
                f"({d['source_licence_found']})")
        c = d["source_class"]
        if c == "share-alike" and not same_licence(d["source_licence"]):
            groups["share-alike"].append(ev("file", d["file"], what))
        elif c in {"restricted", "none"}:
            groups["restricted"].append(ev("file", d["file"], what))
        elif c == "permissive" and not d["attribution"]:
            groups["unattributed"].append(ev("file", d["file"], what + "; no credit found"))
        elif c != "permissive":
            groups["read"].append(ev("file", d["file"], what))
    signals["third_party_declarations"] = sig(
        len(declared), "frontmatter licence keys, source lines and SPDX headers",
        note=", ".join(f"{k} {v}" for k, v in sorted(
            {c: sum(1 for r in declared if r["class"] == c) for c in {r["class"] for r in declared}}
            .items())) or None)
    if corpus:
        signals["copies_credited"] = sig(
            f"{sum(1 for d in copies if d['attribution'])} of {len(copies)}",
            "matched files with a source line, a licence beside them, or a NOTICE entry")
    if groups["share-alike"]:
        flags.append({
            "id": "share-alike-text", "severity": "critical",
            "title": f"Share-alike text inside a {proj_label or 'unlicensed'} tree",
            "detail": "Copying share-alike text passes its licence on to the work that carries it. "
                      "These are facts only; a person rules.",
            "caps": "D1=0", "evidence": groups["share-alike"][:5]})
    if groups["restricted"]:
        flags.append({
            "id": "restricted-licence-text", "severity": "serious",
            "title": "Third-party text whose licence does not allow reuse, or has no licence",
            "detail": "Text with no licence is all rights reserved. Non-commercial, no-derivatives "
                      "and source-available terms do not allow redistribution here.",
            "caps": "D1<=3", "evidence": groups["restricted"][:5]})
    if groups["unattributed"]:
        flags.append({
            "id": "copied-without-attribution", "severity": "serious",
            "title": f"{len(groups['unattributed'])} copied file(s) with no credit to their source",
            "detail": "Permissive licences still require the licence and credit to travel with the "
                      "copy: a source line, a licence file beside it, or a NOTICE entry.",
            "caps": "D2<=3", "evidence": groups["unattributed"][:5]})
    if groups["read"]:
        flags.append({
            "id": "licence-needs-reading", "severity": "warning",
            "title": "Third-party text under terms a person should read",
            "detail": "Not an OSI licence, a file-level copyleft, a name this tool does not know, or "
                      "a source named with no licence beside it.",
            "evidence": groups["read"][:5]})

    # --- claims
    claims = extract_claims(root)
    for c in claims:
        if c["kind"] == "tests":
            # A claim of "N tests" counts test CASES; this tool counts test FILES. They are not
            # the same quantity, so the claim is reported as unchecked with both numbers rather
            # than scored as a contradiction. Running the suite is the deep pass's job.
            c["measured"] = f"{len(test_files)} test files present (cases not counted here)"
            c["status"] = "unchecked"
            c["evidence"] = [ev("command", "files under tests/ or named *.test.*",
                                str(len(test_files)))]
        elif c["kind"] in ("skills", "agents", "commands") and \
                c.get("kind_of_claim") != "compatibility":
            n = int(re.sub(r"[^\d]", "", c["claim"]) or 0)
            actual = {"skills": len(unique_skills), "agents": len(unique_agents),
                      "commands": len(unique_cmds)}[c["kind"]]
            c["measured"] = f"{actual} distinct {c['kind']} found"
            c["evidence"] = [ev("command", f"distinct {c['kind']} identities", str(actual))]
            # Only an INFLATED claim is a contradiction. Finding more than claimed usually means
            # the project counts a subdirectory and the tool counts the tree — over-delivery, or
            # a difference in definition, never dishonesty.
            if n and actual < n * 0.5:
                c["status"] = "contradicted"
            elif n and abs(actual - n) <= max(2, n * 0.15):
                c["status"] = "confirmed"
            else:
                c["status"] = "unchecked"
                c["measured"] += " — counted differently from the claim; check what it scopes"
        elif c["kind"] in {"soc2", "slsa", "iso27001", "hipaa", "production-ready",
                           "battle-tested", "enterprise-grade"}:
            c["status"] = "unsupported"
            c["measured"] = "no supporting artifact found in the repository"
    for c in claims:
        if c.get("kind_of_claim") == "compatibility" and c["status"] == "unchecked":
            c["measured"] = "reads as a compatibility claim about hosts, not an inventory count"
    contradicted = [c for c in claims if c["status"] == "contradicted"]
    if contradicted:
        flags.append({
            "id": "contradicted-claim", "severity": "serious",
            "title": f"{len(contradicted)} claim(s) the repository contradicts",
            "caps": "B2<=2",
            "evidence": [ev("note", f"{c['location']}: “{c['claim']}”", c.get("measured", ""))
                         for c in contradicted[:5]],
        })

    # Own module, new check: no caps until a field run has measured its false positives.
    from .claims import eval_evidence, readme_claim_flag, score_flag
    evals = eval_evidence(root)
    signals["eval_evidence"] = sig(
        evals, "known eval setup and result file names and decorators, by path and content",
        note="setup shows evals are configured; only a result file shows a run wrote output")
    scored = score_flag(root, evals)
    if scored:
        flags.append(scored)
    mismatch = readme_claim_flag(root, lic["declared"], lic["declared_file"])
    if mismatch:
        flags.append(mismatch)

    # --- product signals
    signals["readme_bytes"] = sig(
        next((os.path.getsize(os.path.join(root, n)) for n in sorted(os.listdir(root))
              if re.match(r"(?i)^readme(\.|$)", n)), 0), "wc -c README")
    abs_paths = grep(root, [("absolute-path", r"(?<![\w.])/(Users|home)/[a-zA-Z0-9._-]+/")],
                     TEXT_EXT, max_hits=10,
                     detector="machine-specific paths", count_only=True)
    signals["absolute_path_hits"] = sig(len(abs_paths), "machine-specific paths in text files")

    # --- the project's own exclusions: shown, never hidden
    patterns = ignore_patterns(root)
    flags, downgraded = apply_ignore(flags, patterns if honour_ignore else [])
    if patterns:
        # Only a path-shaped pattern prints; anything else (instructions, control or bidi
        # characters, a credential, markup, an overlong line) is shown as a placeholder.
        shown = []
        for pat in patterns:
            text = pat if PATTERN_TEXT_RE.match(pat) and not holds_secret(pat) else PATTERN_WITHHELD
            if text not in shown:
                shown.append(text)
        unique = list(dict.fromkeys(patterns))
        signals["excluded_by_project"] = sig(
            {"file": IGNORE_FILE, "patterns": shown[:PATTERNS_SHOWN],
             "patterns_dropped": max(0, len(shown) - PATTERNS_SHOWN),
             "honoured": honour_ignore,
             "files_matched": sum(is_ignored(rel, unique) for _, rel in walk(root, include_hidden=True)),
             "findings_downgraded": downgraded},
            f"patterns read from {IGNORE_FILE}",
            note="a pattern list changes no flag unless the person screening asked for --honour-ignore")
        if honour_ignore:
            limits.append(f"--honour-ignore applied {IGNORE_FILE}: findings in the paths it lists became "
                          "information, so this band can be lower than the same tree screens without it.")
    contradicted = [c for c in claims if c["status"] == "contradicted"]

    # --- a detector that stopped at its budget has not read the rest of the tree
    stopped = [(d, b) for d, b, count_only in _REACHED if not count_only]
    for detector, budget, count_only in _REACHED:
        limits.append(f"{detector}: " + (f"stopped at its budget of {budget}; the count or result is a floor. No flag or band changed." if count_only else
                      f"stopped at its budget of {budget}; later files were not read for this check, "
                      "so its result is incomplete."))
    limits.extend(_NOTES)
    if stopped:
        flags.append({
            "id": "scan-limit-reached", "severity": "warning",
            "title": f"{len(stopped)} check(s) stopped at a budget before the whole tree was read",
            "detail": "Later files were not read for these checks and their result is incomplete. "
                      "A credential or licence line past the budget would not appear on this card.",
            "evidence": [ev("note", "scan-limit-reached", f"{d}: budget {b}") for d, b in stopped[:5]],
        })

    # --- band
    sev = {f["severity"] for f in flags}
    if "critical" in sev:
        band = "blocked"
    elif "serious" in sev or contradicted or stopped:  # an incomplete read is not "nothing to see"
        band = "review"
    elif len(test_files) > 0 and lic["declared"] and (workflows or signals["jenkinsfile"]["value"]):
        band = "shortlist"
    else:
        band = "screened"

    dims = []
    for dim_id, group in [("A1", "methodology"), ("A2", "methodology"), ("A3", "methodology"),
                          ("A4", "methodology"), ("B1", "evidence"), ("B2", "evidence"),
                          ("B3", "evidence"), ("C1", "safety"), ("C2", "safety"),
                          ("C3", "safety"), ("C4", "safety"), ("D1", "integrity"),
                          ("D2", "integrity"), ("E1", "product"), ("E2", "product"),
                          ("E3", "product")]:
        applicable = True
        na = None
        if dim_id in ("A1", "A2") and archetype in ("tool", "application", "orchestrator", "unknown") \
                and not skills:
            applicable, na = False, f"no instruction catalogue in a project classified {archetype}"
        dims.append({"id": dim_id, "group": group, "applicable": applicable,
                     **({"na_reason": na} if na else {}),
                     "score": None, "confidence": "unverified",
                     "rationale": "screen mode measures signals; it does not score",
                     "evidence": []})

    limits.append("Screen mode is mechanical. No score here is a judgement, and every dimension "
                  "is marked unverified until a deep pass.")
    limits.append("Regex sweeps find shapes, not meanings: a fixture can look like a credential "
                  "and a quoted licence can look like a breach. Every flag names its evidence, a file and "
                  "line or a command or commit, so a reader can check.")

    return redact_all({
        "schema": "scorecard/1", "mode": "screen",
        "project": {
            # The path as the caller gave it, never the absolute one: a scorecard is published
            # and shared, and an absolute path would carry one machine's layout with it.
            "name": os.path.basename(root), "path": given,
            "commit": git(root, "rev-parse", "--short", "HEAD") or None,
            "measured_at": started.isoformat(timespec="seconds"),
            "archetype": archetype,
            "archetype_evidence": arch_ev,
        },
        "signals": signals, "flags": flags, "dimensions": dims, "claims": claims,
        "totals": {"mean": None, "group_means": {}, "band": band,
                   "caps_applied": [f["caps"] for f in flags
                                    if f.get("caps") and f["severity"] != "info"]},
        "limits": limits,
        "run": {"tool_version": VERSION, "corpus": os.path.basename(os.path.normpath(corpus)) if corpus else None,
                "duration_s": 0.0 if os.environ.get("QUIET_COUNSEL_NOW") else
                round((_dt.datetime.now(_dt.timezone.utc) - started).total_seconds(), 2)},
    })
