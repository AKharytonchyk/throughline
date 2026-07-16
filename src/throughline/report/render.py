"""Render the interactive dashboard (feature 002).

Emits a single self-contained HTML file: shell (head/CSS/header/filter bar/containers) +
the EmbeddedData blob (`<script type="application/json" id="thl-data">`) + the inlined
`app.js`. All views are rendered client-side by `app.js` from the blob; Python no longer
builds view HTML. No CDN, no external assets, no network.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

_APP_JS_PATH = Path(__file__).parent / "app.js"

_CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#0B0E17;--panel:#141A28;--panel-2:#1B2334;--line:#26314A;--line-2:#33415F;
  --ink:#EAEEF7;--ink-2:#9FABC6;--ink-3:#66738F;
  --k-builtin:#3B82C4;--k-mcp:#C4671F;--k-nontool:#1AA36E;--k-unattr:#6B7794;
  --estimate:#E0921A;--cut:#F2685E;--thread-a:#22D3EE;--thread-b:#8B5CF6;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 30px rgba(0,0,0,.28);--radius:16px;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
:root[data-theme=light]{
  --bg:#EEF1F7;--panel:#FFFFFF;--panel-2:#F6F8FC;--line:#E4E9F2;--line-2:#D2DAE8;
  --ink:#111827;--ink-2:#51607A;--ink-3:#8592AC;
  --k-builtin:#1F6FB2;--k-mcp:#C05A17;--k-nontool:#0E8A57;--k-unattr:#8592AC;
  --estimate:#B4740A;--cut:#D64A3F;--thread-a:#0891B2;--thread-b:#7C3AED;
  --shadow:0 1px 2px rgba(20,30,60,.06),0 10px 30px rgba(20,30,60,.08);}
html{background:var(--bg);scrollbar-width:none}
body{-ms-overflow-style:none}
::-webkit-scrollbar{width:0;height:0;background:transparent}
body{margin:0;color:var(--ink);background:var(--bg);font-family:var(--sans);font-size:15px;line-height:1.55}
.mono{font-family:var(--mono)} .num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-3);margin:0 0 6px}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
header{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:saturate(140%) blur(10px);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;gap:16px;padding:16px 0}
.brand{display:flex;flex-direction:column;gap:6px}
.brand h1{margin:0;font-size:19px;font-weight:800;letter-spacing:-.02em}
.brand h1 .line{background:linear-gradient(90deg,var(--thread-a),var(--thread-b));-webkit-background-clip:text;background-clip:text;color:transparent}
.thread{height:2px;width:132px;border-radius:2px;background:linear-gradient(90deg,var(--thread-a),var(--thread-b));background-size:200% 100%;animation:flow 6s linear infinite}
.brand .meta{font-family:var(--mono);font-size:11px;color:var(--ink-3)}
.spacer{flex:1}
.toggle{font-family:var(--mono);font-size:12px;color:var(--ink-2);background:var(--panel);border:1px solid var(--line-2);border-radius:999px;padding:7px 12px;cursor:pointer}
.toggle:hover{border-color:var(--thread-b);color:var(--ink)}
.scrollbar{height:3px;background:var(--line);position:relative;overflow:hidden}
.scrollbar>span{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--thread-a),var(--thread-b))}
.filterbar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding:12px 0}
.filterbar label{font-size:12px;color:var(--ink-2);display:flex;gap:6px;align-items:center}
.filterbar select,.filterbar input,.ctl select{font-family:var(--mono);font-size:12px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:5px 8px}
.filterbar input[type=date]{cursor:pointer;color-scheme:dark}
:root[data-theme=light] .filterbar input[type=date]{color-scheme:light}
.filterbar input[type=date]:hover{border-color:var(--thread-b)}
.filterbar input[type=date]::-webkit-calendar-picker-indicator{cursor:pointer;opacity:.65;margin-left:2px}
.filterbar input[type=date]:hover::-webkit-calendar-picker-indicator{opacity:1}
.frange{width:100%;margin:-2px 0 0;font-family:var(--mono);font-size:11px;color:var(--ink-3)}
.presets{display:flex;gap:6px;align-items:center}
.preset{font-family:var(--mono);font-size:11px;color:var(--ink-2);background:var(--panel);border:1px solid var(--line-2);border-radius:999px;padding:5px 11px;cursor:pointer}
.preset:hover{border-color:var(--thread-b);color:var(--ink)}
.preset.active{color:#fff;border-color:transparent;background:linear-gradient(120deg,var(--thread-a),var(--thread-b))}
/* one height + font across every filter control so text fields and buttons share the same rhythm */
.filterbar select,.filterbar input{height:30px;font-size:12px}
.filterbar .preset,.filterbar .toggle{height:30px;font-size:12px;padding:0 12px;display:inline-flex;align-items:center;justify-content:center;line-height:1}
main{padding:20px 0 80px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:14px;margin:8px 0 26px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow)}
.kpi .v{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:28px;font-weight:700;line-height:1.05;letter-spacing:-.02em}
.kpi .u{font-size:13px;color:var(--ink-3);font-weight:400} .kpi .sub{font-size:12px;color:var(--ink-2);margin-top:6px}
.kpi.hero{border-color:transparent;background:linear-gradient(var(--panel),var(--panel)) padding-box,linear-gradient(120deg,var(--thread-a),var(--thread-b)) border-box;border:1px solid transparent}
.kpi.hero .v{background:linear-gradient(120deg,var(--thread-a),var(--thread-b));-webkit-background-clip:text;background-clip:text;color:transparent}
.kpi.cut .v{color:var(--cut)}
.panel-head{display:flex;align-items:baseline;gap:12px;margin-top:6px} .panel-head .idx{font-family:var(--mono);font-size:12px;color:var(--ink-3)}
h2{margin:2px 0;font-size:17px;font-weight:750;letter-spacing:-.01em}
section.card,.viewsec{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:22px 24px;margin:0 0 22px;box-shadow:var(--shadow)}
.lede{color:var(--ink-2);font-size:13px;margin:2px 0 16px;max-width:72ch}
.chip{font-family:var(--mono);font-size:9.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:5px}
.chip.est{background:color-mix(in srgb,var(--estimate) 20%,transparent);color:var(--estimate);border:1px solid color-mix(in srgb,var(--estimate) 40%,transparent)}
.rows{border-top:1px solid var(--line);margin-top:6px}
.row{display:grid;grid-template-columns:14px minmax(0,1.4fr) minmax(80px,1fr) 90px 64px 58px;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);font-size:13px}
.row .sw{width:10px;height:10px;border-radius:3px}
.row .name{font-family:var(--mono);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.track{height:8px;background:var(--line);border-radius:5px;overflow:hidden}
.track>span{display:block;height:100%;border-radius:5px}
.track>span.hatch{background-image:repeating-linear-gradient(45deg,transparent 0 4px,rgba(255,255,255,.28) 4px 5px)}
.row .n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink-2)} .row .n.big{color:var(--ink)}
.rhead{color:var(--ink-3);font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase}
.total-row{display:flex;justify-content:space-between;padding:12px 0 2px;font-family:var(--mono);font-variant-numeric:tabular-nums}
.sidechain{font-size:12.5px;color:var(--ink-2);margin:12px 0 0;padding-top:12px;border-top:1px dashed var(--line-2)}
.sidechain code{font-family:var(--mono);font-size:11px;background:var(--panel-2);padding:1px 5px;border-radius:4px}
.ctl{margin:2px 0 12px}
.thl-scatter{width:100%;height:auto;background:var(--panel-2);border:1px solid var(--line);border-radius:12px}
.thl-scatter .dot{stroke:var(--panel-2);stroke-width:1.5}
.dot.k-builtin{fill:var(--k-builtin)} .dot.k-mcp{fill:var(--k-mcp)} .dot.k-unattr{fill:var(--k-unattr)}
.thl-scatter .pt{fill:var(--thread-b)} .thl-scatter .trendline{fill:none;stroke:url(#g);stroke-width:2.5;stroke:var(--thread-b)}
.thl-scatter .tick{fill:var(--ink-3);font-family:var(--mono);font-size:10px}
.thl-scatter .axtitle{fill:var(--ink-3);font-family:var(--mono);font-size:11px}
.thl-scatter .ptlabel{fill:var(--ink);font-family:var(--mono);font-size:10.5px}
.thl-scatter .marker{stroke:var(--estimate);stroke-width:1.5;stroke-dasharray:3 3}
.thl-scatter .grid{stroke:var(--line);stroke-width:1;opacity:.45}
.thl-scatter .axis{stroke:var(--line-2);stroke-width:1}
.thl-scatter .tickval{fill:var(--ink-3);font-family:var(--mono);font-size:9.5px}
.thl-scatter .dot,.thl-scatter [data-tip]{cursor:pointer}
.thl-tip{position:fixed;left:0;top:0;z-index:60;pointer-events:none;opacity:0;transition:opacity .08s;background:var(--panel);border:1px solid var(--line-2);border-radius:8px;padding:7px 10px;font-family:var(--mono);font-size:11.5px;color:var(--ink);box-shadow:var(--shadow);max-width:300px;white-space:nowrap}
.thl-tip.on{opacity:1}
.thl-tip .s{display:block;color:var(--ink-2);font-size:10.5px;margin-top:3px;white-space:normal}
.hlegend{display:flex;gap:16px;margin-top:10px;font-size:12px;color:var(--ink-2)}
.hlegend .item{display:flex;gap:7px;align-items:center} .hlegend .d{width:11px;height:11px;border-radius:50%}
.modeview{display:flex;flex-direction:column;gap:8px;margin-top:6px}
.moderow{display:grid;grid-template-columns:90px 1fr 100px 1fr 120px 70px;align-items:center;gap:10px;font-size:13px}
.moderow .mname{font-family:var(--mono);color:var(--ink)}
.mbar{height:8px;background:var(--line);border-radius:5px;overflow:hidden}
.mbar>span{display:block;height:100%;background:var(--k-builtin)} .mbar>span.alt{background:var(--thread-b)}
.chain{border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 12px;background:var(--panel-2)}
.chain-head{display:flex;align-items:center;gap:14px;margin-bottom:12px}
.rank{font-family:var(--mono);font-size:13px;font-weight:700;color:var(--ink-3);width:32px;height:32px;display:grid;place-items:center;border:1px solid var(--line-2);border-radius:9px}
.chain:nth-child(-n+4) .rank{color:var(--ink);border-color:transparent;background:linear-gradient(135deg,color-mix(in srgb,var(--thread-a) 26%,transparent),color-mix(in srgb,var(--thread-b) 26%,transparent))}
.save{margin-left:auto;text-align:right} .save .v{font-family:var(--mono);font-size:18px;font-weight:700;background:linear-gradient(120deg,var(--thread-a),var(--thread-b));-webkit-background-clip:text;background-clip:text;color:transparent} .save .l{font-size:11px;color:var(--ink-3)}
.pipe{display:flex;align-items:center;flex-wrap:wrap;row-gap:8px;margin:2px 0 12px}
.node{font-family:var(--mono);font-size:12px;background:var(--panel);border:1px solid var(--line-2);border-radius:9px;padding:6px 10px;white-space:nowrap}
.node.fan{border-color:color-mix(in srgb,var(--thread-b) 55%,var(--line-2))} .node .fantag{display:block;font-size:8.5px;color:var(--thread-b)}
.conn{width:26px;height:2px;border-radius:2px;background:linear-gradient(90deg,var(--thread-a),var(--thread-b))}
.metrics{display:flex;gap:22px;font-size:12.5px;color:var(--ink-2);margin-bottom:10px} .metrics b{color:var(--ink);font-family:var(--mono)}
.proposal{background:var(--panel);border:1px dashed var(--line-2);border-radius:10px;padding:10px 12px;font-size:12.5px}
.proposal .pname{font-family:var(--mono);color:var(--ink)}
.proposal code{font-family:var(--mono);font-size:11.5px;background:var(--panel-2);padding:1px 6px;border-radius:5px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;vertical-align:bottom}
.muted{color:var(--ink-3);font-style:italic}
#empty{color:var(--ink-2);text-align:center;padding:60px 0}
footer{color:var(--ink-3);font-size:11.5px;padding:24px 0 0;border-top:1px solid var(--line);margin-top:24px;font-family:var(--mono)}
@keyframes flow{to{background-position:200% 0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
#tip{position:fixed;pointer-events:none;opacity:0}

/* ---- feature 003: token-usage lens (separate views; own classes, no occupancy collision) ---- */
.lensswitch{display:inline-flex;background:var(--panel);border:1px solid var(--line-2);border-radius:999px;padding:3px;gap:2px;margin-right:10px}
.lensbtn{font-family:var(--mono);font-size:12px;color:var(--ink-2);background:transparent;border:0;border-radius:999px;padding:6px 13px;cursor:pointer;line-height:1}
.lensbtn:hover{color:var(--ink)}
.lensbtn.active{color:#fff;background:linear-gradient(120deg,var(--thread-a),var(--thread-b))}
.chip.exact{background:color-mix(in srgb,var(--k-nontool) 18%,transparent);color:var(--k-nontool);border:1px solid color-mix(in srgb,var(--k-nontool) 40%,transparent)}
.tkshare{display:flex;align-items:baseline;gap:12px;margin:2px 0 16px}
.tkshare .big{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:34px;font-weight:750;letter-spacing:-.02em;background:linear-gradient(120deg,var(--thread-a),var(--thread-b));-webkit-background-clip:text;background-clip:text;color:transparent}
.tkshare .lbl{font-size:13px;color:var(--ink-2)}
.tkrow{display:grid;grid-template-columns:12px 150px minmax(0,1fr) 116px 60px;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);font-size:13px}
.tkrow .sw{width:10px;height:10px;border-radius:3px}
.tkrow .name{font-family:var(--mono);font-size:12.5px}
.tktrack{height:9px;background:var(--line);border-radius:5px;overflow:hidden}
.tktrack>span{display:block;height:100%;border-radius:5px}
.tkrow .n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink-2)} .tkrow .n.big{color:var(--ink)}
.tktable{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
.tktable th{text-align:right;color:var(--ink-3);font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:7px 8px;border-bottom:1px solid var(--line);font-weight:600}
.tktable td{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;padding:7px 8px;border-bottom:1px solid var(--line);color:var(--ink-2)}
.tktable td.l,.tktable th.l{text-align:left}
.tktable td.big{color:var(--ink)} .tktable tr.sum td{border-top:1px solid var(--line-2);border-bottom:0;color:var(--ink);font-weight:600}
.tktable .mdl{font-family:var(--mono);font-size:12px;color:var(--ink)}
.tknote{font-size:12.5px;color:var(--ink-2);margin:14px 0 0;padding-top:12px;border-top:1px dashed var(--line-2)}
.thl-scatter .tkarea{fill:var(--thread-b);opacity:.16}
.thl-scatter .tkline{fill:none;stroke:var(--thread-b);stroke-width:2}
.thl-scatter .tktotal{fill:none;stroke:var(--ink-2);stroke-width:1.5;stroke-dasharray:4 3}
.tkdelta{font-size:12.5px;color:var(--ink-2);margin:10px 0 0;display:flex;flex-direction:column;gap:5px}
.tkdelta .d-up{color:var(--cut)} .tkdelta .d-dn{color:var(--k-nontool)}
.tkdelta b{color:var(--ink);font-family:var(--mono)}
.tkunpriced{color:var(--ink-3);font-style:italic}
.tkhelp{border-bottom:1px dotted var(--ink-3);cursor:help}
.tktable th.tkhelp{border-bottom:1px dotted var(--ink-3)}
.tkcaption{font-size:12.5px;color:var(--ink-2);margin:2px 0 16px;max-width:80ch;line-height:1.5}
.tkcaption .mono{background:var(--panel-2);padding:1px 5px;border-radius:4px;font-size:11.5px}
"""


def render_html(embedded: dict) -> str:
    blob = json.dumps(embedded, ensure_ascii=False).replace("</", "<\\/")
    app_js = _APP_JS_PATH.read_text(encoding="utf-8")
    scope = f"{embedded['scope']['sessions'] if 'scope' in embedded else len(embedded.get('session_facts', []))} sessions"
    n_sessions = len({sf["sess"] for sf in embedded.get("session_facts", [])})
    P = []
    P.append("<!doctype html><html lang='en' data-theme='dark'><head><meta charset='utf-8'>")
    P.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    P.append("<title>Throughline — cost over time</title>")
    P.append(f"<style>{_CSS}</style></head><body>")
    P.append("<header><div class='wrap bar'><div class='brand'>"
             "<h1><span>through</span><span class='line'>line</span></h1><div class='thread'></div>"
             f"<div class='meta'>{n_sessions} sessions · {html.escape(embedded['unit'])} · "
             f"{html.escape(embedded['generated_at'][:19])}Z</div></div>"
             "<div class='spacer'></div>"
             "<div class='lensswitch' id='lensswitch'>"
             "<button class='lensbtn active' data-lens='occupancy'>Context window</button>"
             "<button class='lensbtn' data-lens='tokens'>Token usage</button></div>"
             "<button class='toggle' id='themeToggle'>◐ dark</button></div>"
             "<div class='wrap'><div class='filterbar' id='filterbar'></div></div>"
             "<div class='scrollbar'><span id='scrollfill'></span></div></header>")
    P.append("<main><div class='wrap'>")
    P.append("<div id='empty'>Nothing to show for this filter. Clear it, or run "
             "<span class='mono'>throughline collect</span> then <span class='mono'>report</span>.</div>")
    P.append("<div id='views'>"
             "<div id='kpis' class='kpis'></div>"
             "<section class='viewsec' id='view-spend'></section>"
             "<section class='viewsec' id='view-trend'></section>"
             "<section class='viewsec' id='view-heatmap'></section>"
             "<section class='viewsec' id='view-mode'></section>"
             "<section class='viewsec' id='view-chains'></section>"
             "</div>")
    # feature 003: the token-usage lens (hidden until the lens switch selects it)
    P.append("<div id='token-views' style='display:none'>"
             "<div id='token-kpis' class='kpis'></div>"
             "<section class='viewsec' id='tview-flow'></section>"
             "<section class='viewsec' id='tview-growth'></section>"
             "<section class='viewsec' id='tview-trend'></section>"
             "<section class='viewsec' id='tview-cost'></section>"
             "</div>")
    P.append("<footer>100% local — no network. Two lenses: <b>Context window</b> (chars, per-tool "
             "occupancy) and <b>Token usage</b> (tokens, per-turn flow) — kept separate, never merged. "
             "Token counts are exact; dollar cost is an opt-in labeled estimate. Filtering is "
             "client-side over pre-aggregated data.</footer>")
    P.append("</div></main>")
    P.append(f"<script type='application/json' id='thl-data'>{blob}</script>")
    P.append(f"<script>{app_js}</script>")
    P.append("</body></html>")
    return "".join(P)


def render_to_file(embedded: dict, out_path: str | Path) -> Path:
    out = Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(embedded), encoding="utf-8")
    return out
