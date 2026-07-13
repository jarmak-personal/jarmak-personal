#!/usr/bin/env python3
"""Generate assets/jarmak-personal-smi.svg from smi.toml.

The output is a self-animating SVG (CSS only, no JS) that looks like a
Claude Code session: the prompt types itself, Claude "runs"
jarmak-personal-smi, and an nvidia-smi-style table of current projects
prints out. GitHub renders SVG animations fine through its image proxy.

Usage: python3 generate_smi.py
"""

from __future__ import annotations

import html
import textwrap
import tomllib
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "assets" / "jarmak-personal-smi.svg"

# ---- geometry -------------------------------------------------------------
TABLE_W = 89          # SMI table width in characters
C1, C2, C3 = 41, 22, 22  # interior column widths (41+22+22 + 4 pipes = 89)
FONT_SIZE = 12
CHAR_W = 7.23         # Menlo/Consolas advance width at 12px
LINE_H = 17
PAD_X = 22
PAD_Y = 14
TITLEBAR_H = 34

# ---- colors ---------------------------------------------------------------
BG = "#16171d"
CHROME = "#1f2027"
BORDER = "#2e303a"
FG = "#d0d3da"
DIM = "#5b5f6b"
ORANGE = "#d97757"   # Claude
GREEN = "#76b900"    # NVIDIA
BLUE = "#79c0ff"
MUTED = "#9aa0ac"


def fit(s: str, w: int, align: str = "l") -> str:
    """Pad or truncate s to exactly w characters."""
    s = s[:w]
    return s.ljust(w) if align == "l" else s.rjust(w)


# A rendered line is a list of (text, css_class) parts; '' = default color.
Line = list[tuple[str, str]]


def plain(s: str, cls: str = "") -> Line:
    return [(s, cls)]


def col_row(c1: str, c2: str, c3: str, parts_c1: Line | None = None) -> Line:
    """Build a 3-column SMI row. parts_c1 optionally replaces plain c1."""
    line: Line = [("|", "dim")]
    line += parts_c1 if parts_c1 is not None else [(fit(c1, C1), "")]
    line += [("|", "dim"), (fit(c2, C2), ""), ("|", "dim")]
    line += [(fit(c3, C3, "r"), ""), ("|", "dim")]
    return line


def full_row(s: str, cls: str = "") -> Line:
    return [("|", "dim"), (fit(s, TABLE_W - 2), cls), ("|", "dim")]


def smi_lines(cfg: dict) -> list[Line]:
    h = cfg["header"]
    edge = "+" + "-" * (TABLE_W - 2) + "+"
    split = "|" + "-" * C1 + "+" + "-" * C2 + "+" + "-" * C3 + "|"
    heavy = "|" + "=" * C1 + "+" + "=" * C2 + "+" + "=" * C3 + "|"
    row_edge = "+" + "-" * C1 + "+" + "-" * C2 + "+" + "-" * C3 + "+"

    lines: list[Line] = []
    lines.append(plain(edge, "dim"))
    title = f" JARMAK-PERSONAL-SMI {h['version']}"
    mid = f"Driver Version: {h['driver']}"
    right = f"CUDA Version: {h['cuda']} "
    lines.append(full_row(f"{fit(title, 33)}{fit(mid, 34)}{fit(right, TABLE_W - 2 - 33 - 34, 'r')}"))
    lines.append(plain(split, "dim"))
    lines.append(col_row(" Idx  Name                 Persistence-M", " Branch-Id     Disp.A", "Volatile Scope-Creep "))
    lines.append(col_row(" Vibe Temp   Perf          Pwr:Usage/Cap", "          Brain-Usage", "Repo-Util   Focus M. "))
    lines.append(plain(heavy, "dim"))

    for i, r in enumerate(cfg["repos"]):
        name_field = fit(r["name"], 21)
        pre = fit(f" {i:>3}  ", 6)
        post = fit("On ", C1 - 6 - 21, "r")
        parts: Line = [(pre, ""), (name_field, "green"), (post, "")]
        lines.append(col_row("", fit(f" {r['branch']}", C2 - 6) + fit("On ", 6, "r"), fit("N/A ", C3, "r"), parts_c1=parts))
        c1 = f" {r['vibe']:>4} {r['temp']:>5}  {r['perf']:>4} {r['power']:>18}"
        c3 = f"{r['focus']:>9} {r['mode']:>10} "
        lines.append(col_row(c1, fit("8192MiB / 8192MiB ", C2, "r"), c3))
        lines.append(plain(row_edge if i < len(cfg["repos"]) - 1 else edge, "dim"))

    lines.append(plain("", ""))
    lines.append(plain(edge, "dim"))
    lines.append(full_row(" Processes (tidbits):"))
    lines.append(full_row(f"  {'PID':>4}   {'Type':<6}  {fit('Process name', 59)}{'Mem Usage':>10}"))
    lines.append(plain("|" + "=" * (TABLE_W - 2) + "|", "dim"))
    for p in cfg["processes"]:
        body = f"  {p['pid']:>4}   {p['type']:<6}  {fit(p['name'], 59)}{p['mem']:>10}"
        lines.append(full_row(body))
    lines.append(plain(edge, "dim"))
    return lines


def build(cfg: dict) -> str:
    seq: list[dict] = []  # {parts, cls('fade'|'type'), delay, dur, nchars}
    t = 0.4

    def add(parts: Line, delay: float, anim: str = "fade", dur: float = 0.0):
        seq.append({"parts": parts, "anim": anim, "delay": delay, "dur": dur})

    add([("✻ ", "orange"), ("Welcome to Claude Code!", "bright")], t)
    add(plain(""), t)

    # typed prompt
    t += 0.6
    wrapped = textwrap.wrap(cfg["prompt"]["text"], width=83)
    for i, seg in enumerate(wrapped):
        prefix = "> " if i == 0 else "  "
        n = len(prefix + seg)
        dur = max(0.5, n * 0.032)
        add([(prefix, "dim"), (seg, "bright")], t, anim="type", dur=dur)
        t += dur
    add(plain(""), t)

    t += 0.5
    add([("● ", "orange"), ("I'll build jarmak-personal-smi and run it for you.", "")], t)
    t += 0.6
    add([("● ", "green"), ("Bash", "bright"), ("(./jarmak-personal-smi)", "muted")], t)
    t += 0.4
    add([("  ⎿  ", "dim"), ("Running…", "muted")], t)
    add(plain(""), t)

    # table cascade
    t += 0.4
    for line in smi_lines(cfg):
        add(line, t)
        t += 0.09
    add(plain(""), t)

    t += 0.5
    foot = cfg["footer"]["text"]
    link = cfg["footer"]["link"]
    pre, _, _ = foot.partition(link)
    add([("● ", "green"), (pre, ""), (link, "link")], t)
    t += 0.3
    add([("> ", "dim"), ("▋", "cursor")], t)

    # ---- render ----
    n_lines = len(seq)
    width = round(PAD_X * 2 + TABLE_W * CHAR_W)
    height = TITLEBAR_H + PAD_Y * 2 + n_lines * LINE_H + 6

    texts = []
    y = TITLEBAR_H + PAD_Y + LINE_H
    for item in seq:
        spans = []
        for text, cls in item["parts"]:
            if not text:
                continue
            esc = html.escape(text, quote=False)
            spans.append(f'<tspan class="{cls}">{esc}</tspan>' if cls else f"<tspan>{esc}</tspan>")
        if not spans:
            y += LINE_H
            continue
        if item["anim"] == "type":
            nchars = sum(len(p[0]) for p in item["parts"])
            style = f"--t:{item['delay']:.2f}s;--d:{item['dur']:.2f}s;--n:{nchars}"
            cls = "type"
        else:
            style = f"--t:{item['delay']:.2f}s"
            cls = "fade"
        texts.append(
            f'<text x="{PAD_X}" y="{y}" class="{cls}" style="{style}" xml:space="preserve">{"".join(spans)}</text>'
        )
        y += LINE_H

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace" role="img" aria-label="Claude Code session running jarmak-personal-smi, an nvidia-smi style readout of my current projects">
<style>
text {{ font-size: {FONT_SIZE}px; fill: {FG}; }}
.dim {{ fill: {DIM}; }} .muted {{ fill: {MUTED}; }} .bright {{ fill: #eceef2; }}
.orange {{ fill: {ORANGE}; }} .green {{ fill: {GREEN}; }} .link {{ fill: {BLUE}; text-decoration: underline; }}
.fade {{ opacity: 0; animation: appear 0.01s linear var(--t) forwards; }}
.type {{ clip-path: inset(0 100% 0 0); animation: typing var(--d) steps(var(--n)) var(--t) forwards; }}
.cursor {{ fill: {ORANGE}; animation: blink 1.1s step-end var(--t) infinite; }}
@keyframes appear {{ to {{ opacity: 1; }} }}
@keyframes typing {{ to {{ clip-path: inset(0 -2% 0 0); }} }}
@keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{
  .fade, .type, .cursor {{ animation: none; opacity: 1; clip-path: none; }}
}}
</style>
<rect width="{width}" height="{height}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<path d="M0 10 a10 10 0 0 1 10 -10 h{width - 20} a10 10 0 0 1 10 10 v{TITLEBAR_H - 10} h-{width} z" fill="{CHROME}"/>
<circle cx="22" cy="{TITLEBAR_H // 2}" r="6" fill="#ff5f57"/>
<circle cx="42" cy="{TITLEBAR_H // 2}" r="6" fill="#febc2e"/>
<circle cx="62" cy="{TITLEBAR_H // 2}" r="6" fill="#28c840"/>
<text x="{width // 2}" y="{TITLEBAR_H // 2 + 4}" text-anchor="middle" fill="{MUTED}" font-size="11">claude — ~/jarmak-personal</text>
{chr(10).join(texts)}
</svg>
"""


def main() -> None:
    cfg = tomllib.loads((HERE / "smi.toml").read_text())
    # sanity: every SMI table line must be exactly TABLE_W chars
    for line in smi_lines(cfg):
        s = "".join(p[0] for p in line)
        assert len(s) in (0, TABLE_W), f"bad width {len(s)}: {s!r}"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build(cfg))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
