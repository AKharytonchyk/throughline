"""Hand-rolled inline SVG for the tool heatmap (no external assets, no JS libraries).

Frequency (x) x volume (y), log-log, dot area ~ volume, hue by source kind (matches the
breakdown), shade warmer when survival is low. Colours reference CSS variables so the chart
re-themes with the page. Dots carry data-tip for the page's custom tooltip.
"""
from __future__ import annotations

import html
import math


def _log(v: float) -> float:
    return math.log10(v + 1)


def _kind_class(key: str) -> str:
    if key.startswith("mcp:"):
        return "k-mcp"
    if key.startswith("builtin:"):
        return "k-builtin"
    return "k-unattr"


def _short(key: str) -> str:
    if key.startswith("mcp:") and "/" in key:
        return key.split("/", 1)[1]
    if key.startswith("builtin:"):
        return key.split(":", 1)[1]
    return key


def scatter(cells: list[dict], width: int = 720, height: int = 420) -> str:
    if not cells:
        return '<p class="muted">No tool calls to plot.</p>'
    padl, padr, padt, padb = 60, 24, 24, 52
    xs = [max(c["call_count"], 1) for c in cells]
    ys = [max(c["total_size"], 1) for c in cells]
    xmaxL = _log(max(xs)) or 1
    ymaxL = _log(max(ys)) or 1

    def px(v):
        return padl + (_log(v) / xmaxL) * (width - padl - padr)

    def py(v):
        return height - padb - (_log(v) / ymaxL) * (height - padt - padb)

    p = [f'<svg viewBox="0 0 {width} {height}" role="img" '
         f'aria-label="Tool heatmap: frequency by volume" class="thl-scatter">']

    # gridlines + ticks at powers of ten
    def fmt_tick(n):
        return f"{n//1000}k" if n >= 1000 else str(n)

    for e in range(0, int(math.ceil(ymaxL)) + 1):
        v = 10 ** e
        y = py(v)
        p.append(f'<line class="grid" x1="{padl}" y1="{y:.1f}" x2="{width-padr}" y2="{y:.1f}"/>')
        p.append(f'<text class="tick" x="{padl-8}" y="{y+3:.1f}" text-anchor="end">{fmt_tick(v)}</text>')
    for e in range(0, int(math.ceil(xmaxL)) + 1):
        v = 10 ** e
        x = px(v)
        p.append(f'<line class="grid" x1="{x:.1f}" y1="{padt}" x2="{x:.1f}" y2="{height-padb}"/>')
        p.append(f'<text class="tick" x="{x:.1f}" y="{height-padb+16}" text-anchor="middle">{fmt_tick(v)}</text>')

    p.append(f'<text class="axtitle" x="{padl+(width-padl-padr)/2:.0f}" y="{height-6}" '
             f'text-anchor="middle">calls →</text>')
    p.append(f'<text class="axtitle" x="{14}" y="{padt+(height-padt-padb)/2:.0f}" '
             f'text-anchor="middle" transform="rotate(-90 14 {padt+(height-padt-padb)/2:.0f})">'
             f'volume returned →</text>')

    for c in sorted(cells, key=lambda c: c["total_size"], reverse=True):
        cx, cy = px(max(c["call_count"], 1)), py(max(c["total_size"], 1))
        r = 5 + 13 * (_log(c["total_size"]) / ymaxL)
        cls = _kind_class(c["tool_key"])
        surv = c.get("survival")
        extra = ""
        if surv and surv.get("available") and surv.get("rate") is not None:
            extra = f' style="opacity:{0.45 + 0.5*(1-surv["rate"]):.2f}"'
        tip = f'{_short(c["tool_key"])} — {c["call_count"]} calls · {c["total_size"]:,} chars'
        p.append(f'<circle class="dot {cls}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                 f'data-tip="{html.escape(tip, quote=True)}"{extra}>'
                 f'<title>{html.escape(tip)}</title></circle>')

    for c in sorted(cells, key=lambda c: c["total_size"], reverse=True)[:6]:
        cx, cy = px(max(c["call_count"], 1)), py(max(c["total_size"], 1))
        p.append(f'<text class="ptlabel" x="{cx+8:.1f}" y="{cy-8:.1f}">'
                 f'{html.escape(_short(c["tool_key"]))}</text>')
    p.append("</svg>")
    return "".join(p)
