"""Four checks written from public incident reports: commands that run when a folder opens,
install-time package scripts, workflow steps that send data to a bare address, and workflows
that run pull request content with secrets or agent write access.

Each check asks a person to look. None says who wrote the line or why. Standard library only.
Workflows are read line by line, not with a YAML parser, so anchors, flow-style maps, YAML
merge keys and values assembled in variables are not followed. Every hit carries the file and
the line it was read from.
"""

import json
import os
import re

from . import scan as _s

LEVELS = ("info", "warning", "serious", "critical")

# A path with a hidden folder in it, such as .vscode/setup.mjs. Tokens with "://" are URLs.
def _hidden_script(cmd):
    for tok in re.split(r"[\s\"'=;&|()]+", cmd):
        if "://" in tok:
            continue
        segs = re.split(r"[/\\]", tok)
        if any(s.startswith(".") and len(s) > 1 and s != ".." for s in segs[:-1]):
            return True
    return False


PIPE_SHELL_RE = re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b"
                           r"|\b(ba|z)?sh\s+<\(\s*(curl|wget)\b|\|\s*iex\b", re.I)


def _risky(cmd):
    return _hidden_script(cmd) or bool(PIPE_SHELL_RE.search(cmd))


def _hit(rel, line_no, lines, level):
    text = _s.clip(lines[line_no - 1]) if 0 < line_no <= len(lines) else ""
    return {"rel": rel, "line": line_no, "text": text, "level": level}


def _event_hidden(event, lines):
    """True when the event name, or a line that holds it as a key, would be withheld from a card, or
    when no line can be matched to the key (an escaped spelling): then the name is not shown."""
    key = json.dumps(event, ensure_ascii=False)
    own = [ln for ln in lines if key in ln]
    return _s.holds_secret(event) or not own or any(_s.holds_secret(ln) for ln in own)


def _flag(fid, title, detail, hits):
    """One flag per check: the worst level of its hits, the worst hits first."""
    hits = sorted(hits, key=lambda h: -LEVELS.index(h["level"]))
    loud = [f"{h['rel']}:{h['line']}" for h in hits if h["level"] not in ("info", "warning")]
    events = sorted({h["event"] for h in hits if h.get("event") and not h.get("event_hidden")})
    detail += f" Event: {', '.join(events)}." if events else ""
    return {"id": fid, "severity": hits[0]["level"], "title": title,
            "detail": detail + (f" Raised above a warning at {', '.join(loud[:5])}." if loud else ""),
            "evidence": [_s.ev("file", f"{h['rel']}:{h['line']}", h["text"]) for h in hits[:5]]}


# ------------------------------------------------------------------ C1 open-time hook

MAX_DEPTH = 40      # deepest nesting read from a configuration file
MAX_COMMANDS = 200  # commands read from one file
MAX_CMD = 4000      # characters of one command the patterns look at


def _load_json(text):
    """(data, state): state is "ok", "invalid" or "too deep". A deeply nested file is refused
    before it can overflow the parser's stack."""
    depth = deepest = 0
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c in "[{":
            depth += 1
            deepest = max(deepest, depth)
            if deepest > MAX_DEPTH:
                return None, "too deep"
        elif c in "]}":
            depth -= 1
        i += 1
    try:
        return json.loads(text), "ok"
    except (ValueError, RecursionError):
        return None, "invalid"


def _hook_commands(node):
    """`command` strings under a node, reading at most MAX_DEPTH levels and MAX_COMMANDS values."""
    out, stack = [], [(node, 0)]
    while stack and len(out) < MAX_COMMANDS:
        cur, depth = stack.pop()
        if depth > MAX_DEPTH:
            continue
        if isinstance(cur, dict):
            for k, v in reversed(list(cur.items())):
                if k == "command" and isinstance(v, str):
                    out.append(v[:MAX_CMD])
                else:
                    stack.append((v, depth + 1))
        elif isinstance(cur, list):
            stack.extend((v, depth + 1) for v in reversed(cur))
    return out


def _json_tokens(text):
    """Strings and punctuation of JSON that may carry comments, with the objects they form.

    Returns (tokens, objects). A token is (kind, position, text). objects maps the index of a
    `{` token to (index of its `}`, index of the container holding it, that container's key).
    Comments are skipped, so nothing inside one is a token."""
    toks, objects, stack = [], {}, []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            toks.append(("s", i, text[i:j + 1]))
            i = j + 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "{[":
            key = toks[-2][2] if len(toks) > 1 and toks[-1][0] == ":" and toks[-2][0] == "s" else None
            parent = stack[-1][0] if stack else None
            if c == "{":
                objects[len(toks)] = [None, parent, key]
            stack.append((len(toks), c, key))
            toks.append((c, i, c))
        elif c in "}]":
            if stack and stack[-1][1] == {"}": "{", "]": "["}[c]:
                start = stack.pop()[0]
                if c == "}":
                    objects[start][0] = len(toks)
            toks.append((c, i, c))
        elif c == ":":
            toks.append((c, i, c))
        i += 1
    return toks, objects


def _folder_open_tasks(text):
    """[(position of the runOn key, text of its task)] for each real task set to run when the
    folder opens: a `runOn` property of a `runOptions` object that is an element of `tasks`."""
    toks, objects = _json_tokens(text)
    owner, stack = {}, []
    for k, (kind, _pos, _t) in enumerate(toks):
        if k in objects:
            stack.append(k)
        owner[k] = stack[-1] if stack else None
        if kind == "}" and stack:
            stack.pop()
    out = []
    for k in range(len(toks) - 2):
        if toks[k][2] != '"runOn"' or toks[k + 1][0] != ":" or toks[k + 2][2] != '"folderOpen"':
            continue
        opts = owner[k]
        if opts is None or opts == k or objects[opts][0] is None:
            continue
        if not (opts >= 2 and toks[opts - 1][0] == ":" and toks[opts - 2][2] == '"runOptions"'):
            continue
        task = objects[opts][1]
        if task is None or task not in objects or objects[task][0] is None:
            continue
        # the task must itself sit in an array keyed "tasks" (its container's key)
        if objects[task][2] is not None or not _in_tasks_array(toks, task):
            continue
        out.append((toks[k][1], text[toks[task][1]:toks[objects[task][0]][1]][:20000]))
        if len(out) >= 50:
            break
    return out


def _in_tasks_array(toks, task):
    """Whether the `{` at index `task` is an element of an array whose key is "tasks"."""
    depth, k = 0, task - 1
    while k >= 0:
        kind = toks[k][0]
        if kind in "}]":
            depth += 1
        elif kind in "{[":
            if depth == 0:
                return kind == "[" and k >= 2 and toks[k - 1][0] == ":" and toks[k - 2][2] == '"tasks"'
            depth -= 1
        k -= 1
    return False


TASK_CMD_RE = re.compile(r'"(?:command|args)"\s*:\s*(\[[^\]]{0,4000}\]|"(?:[^"\\]|\\.){0,4000}")')


HOST_DIRS = (".claude", ".vscode", ".cursor", ".codex", ".gemini")
OPEN_EVENT = "SessionStart"


def _other_host_folder(cmd, own):
    """True when the command runs something inside a host folder other than its own."""
    for tok in re.split(r"[\s\"'=;&|()]+", cmd):
        if "://" not in tok and any(s in HOST_DIRS and s != own for s in re.split(r"[/\\]", tok)[:-1]):
            return True
    return False


def _open_level(cmd, own):
    """Serious for a download piped to a shell, or a script in a different host folder."""
    return "serious" if PIPE_SHELL_RE.search(cmd) or _other_host_folder(cmd, own) else "warning"


def _unreadable(rel, lines):
    return {"rel": rel, "line": 1, "text": (_s.clip(lines[0]) if lines else ""), "level": "warning"}


def open_time_hooks(root, unreadable):
    """Open-time hooks (a session-start hook, a folder-open task) and, at information level,
    the agent's other hook events. A file too deeply nested to read is added to `unreadable`."""
    hits = {"open-time-hook": [], "agent-hook": []}
    rel = ".claude/settings.json"
    text = _s.read_text(os.path.join(root, rel), 500_000, root)
    if text:
        lines = text.splitlines()
        data, state = _load_json(text)
        if state == "too deep":
            unreadable.append(_unreadable(rel, lines))
        hooks = data.get("hooks") if isinstance(data, dict) else None
        used = set()
        for event, body in (hooks.items() if isinstance(hooks, dict) else ()):
            for cmd in _hook_commands(body):
                needle = json.dumps(cmd, ensure_ascii=False)[1:-1]
                n = next((i for i, ln in enumerate(lines, 1) if i not in used and needle in ln), 0)
                used.add(n)
                hidden = _event_hidden(event, lines)
                if event == OPEN_EVENT:
                    h = _hit(rel, n or 1, lines, _open_level(cmd, ".claude"))
                    hits["open-time-hook"].append({**h, "event": event, "event_hidden": hidden})
                else:
                    hits["agent-hook"].append({**_hit(rel, n or 1, lines, "info"), "event": event,
                                               "event_hidden": hidden})
    rel = ".vscode/tasks.json"
    text = _s.read_text(os.path.join(root, rel), 500_000, root)
    lines = text.splitlines()
    for pos, task in (_folder_open_tasks(text) if text else ()):
        cmd = " ".join(TASK_CMD_RE.findall(task))[:MAX_CMD]
        hits["open-time-hook"].append({**_hit(rel, text.count("\n", 0, pos) + 1, lines,
                                              _open_level(cmd, ".vscode")), "event": "folderOpen"})
    return hits


# ------------------------------------------------------------------ C2 install-time script

INSTALL_KEYS = ("preinstall", "install", "postinstall")


def install_scripts(root, unreadable):
    hits = []
    for path, rel in _s.walk(root, {".json"}):
        if os.path.basename(path) != "package.json" or _s.FIXTURE_PATH_RE.search(rel):
            continue
        text = _s.read_text(path, 500_000)
        data, state = _load_json(text)
        if state == "too deep":
            unreadable.append(_unreadable(rel, text.splitlines()))
        scripts = data.get("scripts") if isinstance(data, dict) else None
        if not isinstance(scripts, dict):
            continue
        lines = text.splitlines()
        start = next((i for i, ln in enumerate(lines) if '"scripts"' in ln), 0)
        for key in INSTALL_KEYS:
            cmd = scripts.get(key)
            if not isinstance(cmd, str):
                continue
            n = next((i for i in range(start, len(lines)) if re.match(rf'\s*"{key}"\s*:', lines[i])),
                     start)
            hits.append(_hit(rel, n + 1, lines, "serious" if _risky(cmd[:MAX_CMD]) else "warning"))
    return hits


# ------------------------------------------------------------------ workflows, read by line

MAX_LINE = 2000  # characters of a workflow line the patterns look at


def _workflows(root):
    d = os.path.join(root, ".github", "workflows")
    if _s.leaves_root(root, d):
        return
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return
    for name in names:
        p = os.path.join(d, name)
        if name.endswith((".yml", ".yaml")) and os.path.isfile(p) and not _s.leaves_root(root, p):
            lines = _s.read_text(p, 200_000, root).splitlines()
            # the cut lines are for detection; evidence takes the whole line, and ev() withholds it if it holds a secret
            yield f".github/workflows/{name}", [ln[:MAX_LINE] for ln in lines], lines


def _steps(lines, offset=0):
    """Each step under every `steps:` key, as a list of (line_no, text). `offset` is the number of
    lines that precede `lines` in the file."""
    out, i, n = [], 0, len(lines)
    while i < n:
        m = re.match(r"^(\s*)steps:\s*(#.*)?$", lines[i])
        i += 1
        if not m:
            continue
        base, step_ind, cur = len(m.group(1)), None, None
        while i < n:
            ln, s = lines[i], lines[i].strip()
            if not s or s.startswith("#"):
                if cur is not None:
                    cur.append((i + 1 + offset, ln))
                i += 1
                continue
            ind = len(ln) - len(ln.lstrip())
            if step_ind is None:
                if not (s.startswith("-") and ind >= base):
                    break
                step_ind = ind
            if ind < step_ind or (ind == step_ind and not s.startswith("-")):
                break
            if ind == step_ind:
                cur = []
                out.append(cur)
            cur.append((i + 1 + offset, ln))
            i += 1
    return out


def _run_commands(step):
    """[(line_no, command)] from the step's `run:` value, continuation lines joined."""
    out, k = [], 0
    while k < len(step):
        no, ln = step[k]
        m = re.match(r"^(\s*(?:-\s+)?)run:\s*(.*?)\s*$", ln)
        k += 1
        if not m or ln.lstrip().startswith("#"):
            continue
        key_ind, val = len(m.group(1)), m.group(2)
        style = re.match(r"^([|>])[+-]?\d*\s*(#.*)?$", val)
        if not style:
            out.append((no, val.strip("\"'")))
            continue
        body = []
        while k < len(step):
            n2, l2 = step[k]
            if l2.strip() and len(l2) - len(l2.lstrip()) <= key_ind:
                break
            body.append((n2, l2.strip()))
            k += 1
        body = [(a, t) for a, t in body if t and not t.startswith("#")]
        if style.group(1) == ">" and body:
            out.append((body[0][0], " ".join(t for _, t in body)))
            continue
        cur_no, buf = None, ""
        for a, t in body:
            cur_no = cur_no or a
            if t.endswith("\\"):
                buf += t[:-1] + " "
                continue
            out.append((cur_no, buf + t))
            cur_no, buf = None, ""
        if buf:
            out.append((cur_no, buf))
    return [(n, c[:MAX_CMD]) for n, c in out]


# ------------------------------------------------------------------ C3 data out of a workflow

SEND_RE = re.compile(r"(?<![\w./-])(curl|wget|nc|ncat|netcat|socat|Invoke-WebRequest|"
                     r"Invoke-RestMethod|iwr|irm)\b", re.I)
UPLOAD_RE = re.compile(r"(\s-[dFTX]\b|\s--(?:data\S*|form|upload-file|post-data|post-file|"
                       r"body-data|json)\b|\s-Body\b|\s-InFile\b|\||<\s*\S)")
DATA_RE = re.compile(r"secrets\.|toJSON\(\s*secrets|git\s+log\b[^\n|;&]*(?:\s-p\b|--patch\b)", re.I)
SECRET_ENV_RE = re.compile(r"^\s+([A-Za-z_]\w*):\s*.*\$\{\{\s*(?:secrets\.|toJSON\(\s*secrets)")
LOCAL_HOSTS = {"localhost", "0.0.0.0", "[::1]"}


def _is_local(authority):
    """Whether the complete host of an http:// authority is this machine. A name that only
    begins with `localhost` or `127.0.0.1` is another machine, and user info before an `@` is
    not the host."""
    host = authority.rsplit("@", 1)[-1].lower()
    host = host[:host.index("]") + 1] if host.startswith("[") and "]" in host else host.split(":")[0]
    return host in LOCAL_HOSTS or re.fullmatch(r"127(\.\d{1,3}){3}", host) is not None


def _bad_destination(cmd):
    """A numeric IPv4 address, or a plain http:// host that is not this machine."""
    for m in re.finditer(r"(?:://|[\s\"'=@])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.])", cmd):
        parts = m.group(1).split(".")
        if all(int(p) <= 255 for p in parts) and parts[0] not in ("127", "0"):
            return m.group(1)
    for m in re.finditer(r"\bhttp://([^/\s\"'?]+)", cmd, re.I):
        if not _is_local(m.group(1)):
            return m.group(1)
    return None


def data_out(root):
    hits = []
    for rel, lines, whole in _workflows(root):
        env_names = sorted({m.group(1) for ln in lines if (m := SECRET_ENV_RE.match(ln))})[:100]
        for step in _steps(lines):
            cmds = _run_commands(step)
            step_has_data = any(DATA_RE.search(c) for _, c in cmds)
            for no, cmd in cmds:
                if not SEND_RE.search(cmd) or not _bad_destination(cmd):
                    continue
                from_env = any(re.search(rf"\$\{{?{n}\b|%{n}%|\$env:{n}\b", cmd) for n in env_names)
                if DATA_RE.search(cmd) or from_env or (step_has_data and UPLOAD_RE.search(cmd)):
                    hits.append(_hit(rel, no, whole, "serious"))
    return hits


# ------------------------------------------------------------------ C4 untrusted code with power

TRIGGER_RE = re.compile(r"\b(pull_request_target|issue_comment)\b")
HEAD_RE = re.compile(r"github\.event\.pull_request\.head\.(sha|ref|repo)|github\.head_ref|refs/pull/")
UNTRUSTED_RE = re.compile(
    r"\$\{\{[^}]*(?:github\.event\.(?:pull_request\.(?:title|body|head\.(?:ref|label))"
    r"|issue\.(?:title|body)|(?:comment|review|review_comment)\.body)|github\.head_ref"
    r"|steps\.[\w-]+\.outputs\.[\w-]*(?:head_ref|pr_title|pr_body))[^}]*\}\}")
AGENT_RE = re.compile(r"uses:\s*\S*(claude-code|codex|gemini-cli|openhands)", re.I)
OPEN_USERS_RE = re.compile(r"allowed_non_write_users:\s*['\"]?\*['\"]?")
INHERIT_RE = re.compile(r"^\s+secrets:\s*inherit\s*(?:#.*)?$")
PASSED_RE = re.compile(HEAD_RE.pattern + "|" + UNTRUSTED_RE.pattern)
WRITE_RE = re.compile(r"^\s*(?:permissions:\s*write-all|(?:contents|pull-requests|issues):\s*write)\s*$")


def _trigger_line(lines):
    """Line number of a pull_request_target or issue_comment trigger in the top-level `on:`."""
    live = [(i, ln) for i, ln in enumerate(lines, 1) if ln.strip() and not ln.lstrip().startswith("#")]
    start = next((k for k, (_, ln) in enumerate(live) if re.match(r"""^["']?on["']?\s*:""", ln)), None)
    if start is None:
        return None
    for k in range(start, len(live)):
        i, ln = live[k]
        if k > start and not ln.startswith((" ", "\t", "-")):
            break
        if TRIGGER_RE.search(ln):
            return i
    return None


def _job_ranges(lines):
    """(first, end) line indexes of each job under the top-level `jobs:` key."""
    head = next((i for i, ln in enumerate(lines) if re.match(r"^jobs:\s*(#.*)?$", ln)), None)
    if head is None:
        return []
    out, ind, start, end = [], None, None, len(lines)
    for j in range(head + 1, len(lines)):
        ln = lines[j]
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        cur = len(ln) - len(ln.lstrip())
        if cur == 0:
            end = j
            break
        ind = cur if ind is None else ind
        if cur == ind and re.match(r"""["']?[\w.-]+["']?\s*:""", ln.strip()):
            if start is not None:
                out.append((start, j))
            start = j
    if start is not None:
        out.append((start, end))
    return out


def untrusted_with_power(root):
    """The trigger, the untrusted input and the secrets or agent write access are paired inside
    one job. Workflow-level lines (`env:`, `permissions:`) count for every job. Anything that
    links one job to another, such as outputs or artifacts, is not followed. A job that calls a
    reusable workflow with `secrets: inherit` holds secrets, and pull request values it passes in
    `with:` count as untrusted; what the called workflow does with them is not read."""
    hits = []
    for rel, lines, whole in _workflows(root):
        trigger = _trigger_line(lines)
        if trigger is None:
            continue
        ranges = _job_ranges(lines) or [(0, len(lines))]
        inside = {i for a, b in ranges for i in range(a, b)}
        shared = [i for i in range(len(lines)) if i not in inside]

        def first(rx, idx):
            return next((i + 1 for i in idx if lines[i].strip() and not lines[i].lstrip().startswith("#")
                         and rx.search(lines[i])), None)

        for a, b in ranges:
            mine = range(a, b)
            untrusted = None
            for step in _steps(lines[a:b], a):
                text = "\n".join(t for _, t in step)
                if re.search(r"uses:\s*actions/checkout", text):
                    untrusted = untrusted or next((n for n, t in step if HEAD_RE.search(t)), None)
                for n, cmd in _run_commands(step):
                    if untrusted is None and (UNTRUSTED_RE.search(cmd) or re.search(r"\bgh pr checkout\b", cmd)):
                        untrusted = n
            inherit = first(INHERIT_RE, mine)
            if inherit and untrusted is None:  # a call to a reusable workflow has no steps, only `with:`
                untrusted = first(PASSED_RE, mine)
            secrets = first(re.compile(r"secrets\."), [*mine, *shared]) or inherit
            agent = first(AGENT_RE, mine)
            open_users, write = first(OPEN_USERS_RE, [*mine, *shared]), first(WRITE_RE, [*mine, *shared])
            power = secrets or (agent and (open_users or write))
            if untrusted and power:
                level = "critical" if agent else "serious"
                for n in dict.fromkeys([trigger, untrusted, power, agent if agent and agent != power else None]):
                    if n:
                        hits.append(_hit(rel, n, whole, level))
    return hits


# ------------------------------------------------------------------ entry point

def incident_flags(root):
    out, bad = [], []
    opened = open_time_hooks(root, bad)
    for fid, title, detail, fn in (
        ("open-time-hook", "Commands set to run when a folder opens or an agent session starts",
         "Projects use these for setup. Look at what each command runs and who added it.",
         lambda _: opened["open-time-hook"]),
        ("agent-hook", "Commands set to run on other agent hook events",
         "These run during an agent session, not when it opens. Listed for information.",
         lambda _: opened["agent-hook"]),
        ("install-time-script", "A package runs a script when it is installed",
         "Native builds use these. Look at what the script runs and who added it.",
         lambda r: install_scripts(r, bad)),
        ("workflow-data-out", "A workflow step sends data to a bare IP address or a plain HTTP address",
         "Secrets or repository history appear in the same step. Look at where the data goes.",
         data_out),
        ("untrusted-code-with-power", "A workflow runs pull request content with secrets or agent write access",
         "The trigger gives the run the base repository's rights while the code or text comes "
         "from outside. Look at who can start it and what it can reach.", untrusted_with_power),
    ):
        hits = fn(root)
        if hits:
            out.append(_flag(fid, title, detail, hits))
    if bad:
        out.append(_flag("unreadable-configuration", "A configuration file is nested too deeply to read",
                         "The file was not read, so any hook or install script in it was not checked. "
                         "Look at it.", bad))
    return out
