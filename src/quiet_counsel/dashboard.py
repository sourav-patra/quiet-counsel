#!/usr/bin/env python3
"""Render scorecards as one self-contained HTML page.

No external assets, no network calls and no build step, so the page opens from a file path,
survives being emailed, and can be committed beside the scorecards it was made from.

One rule is enforced in code: a dimension that carries a score but no evidence renders as
unevidenced, and `render(..., strict=True)` refuses to build the page.
"""

import html
import json

# Colors come from a validated palette: one blue hue for magnitude, four fixed status steps that
# never double as series colors. Every status is shown with a word as well as a color, and every
# score prints its number, so nothing here depends on a reader seeing hue.
LIGHT_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
              "#2a78d6", "#256abf", "#1c5cab", "#184f95"]
DARK_RAMP = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5",
             "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4"]
# Four fixed status steps plus a neutral. "info" is deliberately grey: a green pill beside a
# finding reads as approval, and an informational note is not approval.
STATUS = {"critical": "#d03b3b", "serious": "#ec835a", "warning": "#fab219",
          "info": "#8a8880", "good": "#0ca30c"}
BAND_STATUS = {"blocked": "critical", "review": "serious", "shortlist": "good",
               "screened": "info"}
DIMENSION_NAMES = {
    "A1": "Instruction-format conformance", "A2": "Context economy",
    "A3": "Capability boundaries", "A4": "Determinism and reproducibility",
    "B1": "Evaluation rigour", "B2": "Claim accuracy", "B3": "Audit trail",
    "C1": "Secret hygiene", "C2": "Untrusted-content posture", "C3": "Supply chain",
    "C4": "Destructive-action gating", "D1": "Licence compliance",
    "D2": "Originality and provenance", "E1": "Coverage", "E2": "Portability",
    "E3": "Maintainability and onboarding",
}
GROUP_NAMES = {"methodology": "Methodology", "evidence": "Evidence", "safety": "Safety",
               "integrity": "Integrity", "product": "Product"}


def esc(x):
    return html.escape(str(x), quote=True)


def ramp_style(score):
    if score is None:
        return ""
    idx = max(0, min(10, int(round(float(score)))))
    return (f"--cell-light:{LIGHT_RAMP[idx]};--cell-dark:{DARK_RAMP[idx]};"
            f"--cell-ink:{'#0b0b0b' if idx <= 5 else '#ffffff'};"
            f"--cell-ink-dark:{'#ffffff' if idx <= 5 else '#0b0b0b'}")


def evidence_html(items):
    if not items:
        return '<p class="none">No evidence attached.</p>'
    rows = []
    for e in items:
        ref = esc(e.get("ref", ""))
        kind = esc(e.get("kind", ""))
        exc = esc(e.get("excerpt", "")) if e.get("excerpt") else ""
        rows.append(f'<li><span class="kind">{kind}</span><code>{ref}</code>'
                    + (f'<pre>{exc}</pre>' if exc else '') + '</li>')
    return f'<ul class="evidence">{"".join(rows)}</ul>'


def signal_rows(signals):
    out = []
    for key, s in signals.items():
        val = s.get("value")
        if isinstance(val, (dict, list)):
            val = json.dumps(val, ensure_ascii=False)
        note = s.get("note") or ""
        cmd = s.get("command") or ""
        out.append(
            f'<tr><th>{esc(key.replace("_", " "))}</th><td class="num">{esc(val)}</td>'
            f'<td class="how"><code>{esc(cmd)}</code>{f"<em>{esc(note)}</em>" if note else ""}</td></tr>')
    return "".join(out)


def project_card(card, idx):
    p = card["project"]
    band = card.get("totals", {}).get("band", "screened")
    flags = card.get("flags", [])
    claims = card.get("claims", [])
    dims = card.get("dimensions", [])
    mode = card.get("mode", "screen")

    flag_html = []
    severity_order = ["critical", "serious", "warning", "info"]
    for f in sorted(flags, key=lambda f: severity_order.index(f.get("severity", "info"))):
        sev = f.get("severity", "info")
        cap = f'<span class="cap">caps {esc(f["caps"])}</span>' if f.get("caps") else ""
        detail = f'<p>{esc(f["detail"])}</p>' if f.get("detail") else ""
        opened = " open" if sev in ("critical", "serious") else ""
        flag_html.append(
            f'<details class="flag sev-{esc(sev)}"{opened}>'
            f'<summary><span class="pill" style="--pill:{STATUS[sev]}">{esc(sev)}</span>'
            f'{esc(f.get("title", f.get("id")))}{cap}</summary>'
            f'{detail}{evidence_html(f.get("evidence", []))}</details>')

    dim_html = []
    for d in dims:
        did = d["id"]
        name = DIMENSION_NAMES.get(did, did)
        if not d.get("applicable", True):
            dim_html.append(
                f'<div class="dim na" title="{esc(d.get("na_reason", "not applicable"))}">'
                f'<span class="did">{esc(did)}</span><span class="score">n/a</span>'
                f'<span class="dname">{esc(name)}</span>'
                f'<span class="why">{esc(d.get("na_reason", ""))}</span></div>')
            continue
        original = d.get("score")
        capped = d.get("capped_to")
        score = capped if original is not None and capped is not None and capped < original else original
        ev_count = len(d.get("evidence") or [])
        unevidenced = score is not None and ev_count == 0
        cls = "dim" + (" pending" if score is None else "") + (" unevidenced" if unevidenced else "")
        shown = "—" if score is None else f"{score:g}"
        cap_note = f" · scored {original:g}, capped to {score:g}" if score != original else ""
        dim_html.append(
            f'<div class="{cls}" style="{ramp_style(score)}">'
            f'<span class="did">{esc(did)}</span>'
            f'<span class="score">{shown}</span>'
            f'<span class="dname">{esc(name)}</span>'
            f'<span class="why">{esc(d.get("rationale", ""))}{cap_note}'
            f'{f" · {ev_count} evidence item(s)" if ev_count else ""}'
            f'{" · SCORED WITHOUT EVIDENCE" if unevidenced else ""}</span></div>')

    claim_rows = "".join(
        f'<tr class="claim-{esc(c.get("status", "unchecked"))}">'
        f'<td>{esc(c.get("claim"))}</td><td>{esc(c.get("location", ""))}</td>'
        f'<td>{esc(c.get("status"))}</td><td>{esc(c.get("measured", ""))}</td></tr>'
        for c in claims) or '<tr><td colspan="4" class="none">No self-claims extracted.</td></tr>'

    limits = "".join(f"<li>{esc(l)}</li>" for l in card.get("limits", []))

    return f"""
<section class="project" id="p{idx}">
  <header>
    <h3>{esc(p.get('name'))}</h3>
    <span class="pill" style="--pill:{STATUS[BAND_STATUS.get(band, 'warning')]}">{esc(band)}</span>
    <span class="tag">{esc(p.get('archetype', 'unknown'))}</span>
    <span class="tag">{esc(mode)} pass</span>
    <span class="meta">{esc(p.get('commit') or 'no commit recorded')} · {esc(p.get('measured_at', ''))}</span>
  </header>
  <div class="cols">
    <div>
      <h4>Dimensions</h4>
      <div class="dims">{''.join(dim_html)}</div>
      <h4>What the project says about itself</h4>
      <table class="claims"><thead><tr><th>Claim</th><th>Where</th><th>Status</th><th>Measured</th></tr></thead>
      <tbody>{claim_rows}</tbody></table>
    </div>
    <div>
      <h4>Flags</h4>
      {''.join(flag_html) or '<p class="none">Nothing flagged.</p>'}
      <h4>Signals</h4>
      <details class="signals"><summary>{len(card.get('signals', {}))} measurements, each with the command that produced it</summary>
      <table class="sig"><tbody>{signal_rows(card.get('signals', {}))}</tbody></table></details>
      <h4>What this run did not establish</h4>
      <ul class="limits">{limits or '<li>Nothing recorded.</li>'}</ul>
    </div>
  </div>
</section>"""


class Unevidenced(ValueError):
    """Raised under strict mode when a scored dimension has nothing behind it."""


def build(cards, title, strict=False):
    unevidenced = []
    for c in cards:
        for d in c.get("dimensions", []):
            if d.get("score") is not None and not d.get("evidence"):
                unevidenced.append(f"{c['project']['name']}:{d['id']}")

    order = {"blocked": 0, "review": 1, "shortlist": 2, "screened": 3}
    cards = sorted(cards, key=lambda c: (order.get(c.get("totals", {}).get("band"), 9),
                                         -(c.get("totals", {}).get("mean") or 0),
                                         c["project"]["name"]))
    counts = {}
    for c in cards:
        b = c.get("totals", {}).get("band", "screened")
        counts[b] = counts.get(b, 0) + 1

    tiles = "".join(
        f'<div class="tile"><span class="n" style="color:{STATUS[BAND_STATUS[b]]}">{counts.get(b, 0)}</span>'
        f'<span class="l">{b}</span></div>'
        for b in ("blocked", "review", "shortlist", "screened"))

    rows = []
    for i, c in enumerate(cards):
        p, t = c["project"], c.get("totals", {})
        band = t.get("band", "screened")
        sev_counts = {}
        for f in c.get("flags", []):
            sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
        flag_cell = " ".join(
            f'<span class="pill sm" style="--pill:{STATUS[s]}">{n} {s}</span>'
            for s, n in sorted(sev_counts.items(),
                               key=lambda kv: ["critical", "serious", "warning", "info"]
                               .index(kv[0]))) or '<span class="none">none</span>'
        sg = c.get("signals", {})

        def v(k):
            got = sg.get(k, {}).get("value")
            return "—" if got is None else (json.dumps(got) if isinstance(got, (dict, list))
                                            else got)
        mean = t.get("mean")
        rows.append(
            f'<tr><td><a href="#p{i}">{esc(p["name"])}</a></td>'
            f'<td>{esc(p.get("archetype", "?"))}</td>'
            f'<td><span class="pill sm" style="--pill:{STATUS[BAND_STATUS.get(band, "warning")]}">{esc(band)}</span></td>'
            f'<td class="num">{"not scored" if mean is None else f"{mean:g}"}</td>'
            f'<td class="num">{esc(v("skill_definitions"))}</td>'
            f'<td class="num">{esc(v("agent_definitions"))}</td>'
            f'<td class="num">{esc(v("test_files"))}</td>'
            f'<td class="num">{esc(v("ci_actions_pinned_by_digest"))}</td>'
            f'<td>{esc(v("licence_declared"))}</td>'
            f'<td>{flag_cell}</td></tr>')

    if strict and unevidenced:
        raise Unevidenced(", ".join(unevidenced))
    warn = ""
    if unevidenced:
        warn = (f'<div class="warnbar">{len(unevidenced)} scored dimension(s) carry no evidence: '
                f'{esc(", ".join(unevidenced[:8]))}. A score with nothing behind it is not a '
                f'finding, and <code>--strict</code> refuses to build a page containing one.</div>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root {{
  color-scheme: light;
  --surface: #fcfcfb; --panel: #ffffff; --line: #e3e2de;
  --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #75736d;
  --cell-bg: var(--cell-light); --cell-fg: var(--cell-ink);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface: #1a1a19; --panel: #232322; --line: #383835;
    --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #9a998f;
    --cell-bg: var(--cell-dark); --cell-fg: var(--cell-ink-dark);
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface: #1a1a19; --panel: #232322; --line: #383835;
  --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #9a998f;
  --cell-bg: var(--cell-dark); --cell-fg: var(--cell-ink-dark);
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--surface); color:var(--ink);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:32px 16px 96px; }}
h1 {{ font-size:26px; margin:0 0 6px; letter-spacing:-.01em; }}
h2 {{ font-size:19px; margin:40px 0 10px; }}
h3 {{ font-size:17px; margin:0; }}
h4 {{ font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--ink-3);
     margin:22px 0 8px; }}
p.lede {{ color:var(--ink-2); margin:0 0 18px; max-width:70ch; }}
.tiles {{ display:flex; gap:10px; flex-wrap:wrap; margin:18px 0 8px; }}
.tile {{ background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:12px 16px; min-width:110px; }}
.tile .n {{ display:block; font-size:26px; font-weight:650; font-variant-numeric:tabular-nums; }}
.tile .l {{ color:var(--ink-2); font-size:13px; }}
table {{ width:100%; border-collapse:collapse; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:14px; }}
th,td {{ text-align:left; padding:9px 11px; border-bottom:1px solid var(--line);
  vertical-align:top; }}
th {{ color:var(--ink-2); font-weight:600; font-size:12.5px; }}
td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
tbody tr:last-child td {{ border-bottom:none; }}
a {{ color:inherit; }}
.pill {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:12px;
  font-weight:600; color:#0b0b0b; background:var(--pill); white-space:nowrap; }}
.pill.sm {{ font-size:11.5px; }}
.tag {{ font-size:12px; color:var(--ink-2); border:1px solid var(--line);
  border-radius:999px; padding:1px 8px; }}
.meta {{ font-size:12px; color:var(--ink-3); margin-left:auto; }}
.project {{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
  padding:16px 18px; margin:16px 0; }}
.project > header {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap;
  padding-bottom:10px; border-bottom:1px solid var(--line); }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:26px; }}
@media (max-width:860px) {{ .cols {{ grid-template-columns:1fr; }} }}
.dims {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(148px,1fr)); gap:7px; }}
.dim {{ background:var(--cell-bg); color:var(--cell-fg); border-radius:8px; padding:8px 9px;
  border:1px solid var(--line); position:relative; }}
.dim .did {{ font-size:11px; font-weight:700; opacity:.85; }}
.dim .score {{ float:right; font-size:17px; font-weight:700; font-variant-numeric:tabular-nums; }}
.dim .dname {{ display:block; font-size:12px; margin-top:2px; }}
.dim .why {{ display:block; font-size:11px; margin-top:4px; opacity:.8; }}
.dim.na, .dim.pending {{ background:transparent; color:var(--ink-2);
  border:1px dashed var(--line); }}
.dim.unevidenced {{ outline:2px solid {STATUS['critical']}; }}
.flag {{ border:1px solid var(--line); border-left:4px solid var(--sev,var(--line));
  border-radius:8px; padding:8px 10px; margin:7px 0; background:var(--panel); }}
.flag.sev-critical {{ --sev:{STATUS['critical']}; }}
.flag.sev-serious {{ --sev:{STATUS['serious']}; }}
.flag.sev-warning {{ --sev:{STATUS['warning']}; }}
.flag.sev-info {{ --sev:{STATUS['info']}; }}
.flag summary {{ cursor:pointer; font-weight:600; display:flex; gap:8px; align-items:center;
  flex-wrap:wrap; }}
.flag p {{ color:var(--ink-2); margin:6px 0; font-size:13.5px; }}
.cap {{ font-size:11px; color:var(--ink-3); }}
ul.evidence {{ list-style:none; padding:0; margin:6px 0 0; }}
ul.evidence li {{ border-top:1px solid var(--line); padding:6px 0; font-size:13px; }}
ul.evidence .kind {{ font-size:11px; color:var(--ink-3); margin-right:6px; }}
code {{ font:12.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; word-break:break-all; }}
pre {{ font:12px/1.45 ui-monospace,Menlo,monospace; background:var(--surface);
  border:1px solid var(--line); border-radius:6px; padding:6px 8px; margin:5px 0 0;
  white-space:pre-wrap; color:var(--ink-2); }}
.none {{ color:var(--ink-3); font-size:13px; }}
.limits {{ margin:0; padding-left:18px; color:var(--ink-2); font-size:13px; }}
.claims td {{ font-size:13px; }}
.claim-contradicted td:nth-child(3) {{ color:{STATUS['critical']}; font-weight:650; }}
.claim-unsupported td:nth-child(3) {{ color:{STATUS['serious']}; font-weight:650; }}
.claim-confirmed td:nth-child(3) {{ color:{STATUS['info']}; font-weight:650; }}
.warnbar {{ background:{STATUS['critical']}; color:#fff; padding:10px 14px; border-radius:8px;
  margin:14px 0; font-size:14px; }}
.legend {{ display:flex; gap:14px; flex-wrap:wrap; color:var(--ink-2); font-size:12.5px;
  margin:10px 0 0; }}
.legend span b {{ font-weight:600; color:var(--ink); }}
.sig th {{ width:44%; font-weight:500; color:var(--ink-2); }}
.sig .how {{ color:var(--ink-3); }}
.sig em {{ display:block; font-style:normal; font-size:11.5px; }}
button.theme {{ position:fixed; right:14px; bottom:14px; border:1px solid var(--line);
  background:var(--panel); color:var(--ink); border-radius:999px; padding:7px 13px;
  font-size:13px; cursor:pointer; }}
</style></head>
<body><div class="wrap">
<h1>{esc(title)}</h1>
<p class="lede">{len(cards)} project(s). Bands order attention, they do not rank quality, and
nothing here is eliminated by a band. Every number below was produced by a command that is
printed beside it, and every flag names its evidence (a file and line, or a command or commit),
so you can check any claim on this page against the repository it describes.</p>
{warn}
<div class="tiles">{tiles}</div>
<div class="legend">
  <span><b>blocked</b> a critical flag: a person rules before anything else happens</span>
  <span><b>review</b> serious flags or a contradicted claim</span>
  <span><b>shortlist</b> clean screen, strong signals</span>
  <span><b>screened</b> clean screen, thin signals</span>
</div>

<h2>The cohort</h2>
<table><thead><tr><th>Project</th><th>Archetype</th><th>Band</th><th class="num">Mean</th>
<th class="num">Skills</th><th class="num">Agents</th><th class="num">Test files</th>
<th class="num">CI pinned</th><th>Licence</th><th>Flags</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2>Each project</h2>
{''.join(project_card(c, i) for i, c in enumerate(cards))}

<h2>What this page does not show</h2>
<ul class="limits">
<li>Whether the code works. Nothing here runs a project's own tests or uses its output.</li>
<li>Paraphrased copying. Duplication is measured by content hash against a corpus you supply,
    so it finds identical files and misses rewritten ones.</li>
<li>Anything outside the corpus you pointed the tool at.</li>
<li>Whether a person or a model wrote the code. There is no reliable detector, and a false
    accusation costs more than a missed one.</li>
<li>Judgement. A screen-mode dimension shows a dash because the screen measures signals and
    does not score.</li>
</ul>
</div>
<button class="theme" onclick="var r=document.documentElement;
  r.dataset.theme = r.dataset.theme === 'dark' ? 'light' : 'dark';">theme</button>
</body></html>"""
