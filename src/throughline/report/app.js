/* Throughline dashboard client (feature 002). Vanilla JS, no libraries.
 * Reads the embedded EmbeddedData blob and re-aggregates + re-renders on every filter
 * change. It only SUMS/GROUPS a Python-built, Python-tested cube — no analysis is re-run.
 * Pure aggregation functions are exported for node unit tests (T034); the browser branch
 * does all DOM work. */
(function () {
  "use strict";

  // ---------- pure helpers (no DOM; node-testable) ----------
  function dayInRange(day, from, to) {
    if (from && day < from) return false;
    if (to && day > to) return false;
    return true;
  }
  function passesCell(blob, filter, cell) {
    var d = blob.dims.days[cell.d];
    if (filter.project && blob.dims.projects[cell.p] !== filter.project) return false;
    return dayInRange(d, filter.from, filter.to);
  }
  function passesRow(blob, filter, row) {
    var d = blob.dims.days[row.d];
    if (filter.project && blob.dims.projects[row.p] !== filter.project) return false;
    return dayInRange(d, filter.from, filter.to);
  }
  function filterCells(blob, filter) {
    return blob.cube.filter(function (c) { return passesCell(blob, filter, c); });
  }

  function aggregateBreakdown(blob, filter) {
    var cells = filterCells(blob, filter);
    var facts = blob.session_facts.filter(function (r) { return passesRow(blob, filter, r); });
    var perTool = {}; // toolIdx -> {n,s}
    cells.forEach(function (c) {
      var t = perTool[c.t] || (perTool[c.t] = { n: 0, s: 0 });
      t.n += c.n; t.s += c.s;
    });
    var perCall = 0, resident = 0, nonTool = 0, unattr = 0;
    var rows = [];
    Object.keys(perTool).forEach(function (ti) {
      var meta = blob.dims.tools[ti], t = perTool[ti];
      if (meta.kind === "unattributed") { unattr += t.s; }
      rows.push({ key: meta.key, kind: meta.kind, cost_kind: "per_call",
                  size: t.s, calls: t.n, is_estimate: false });
      perCall += t.s;
    });
    facts.forEach(function (r) { resident += r.resident_est; nonTool += r.non_tool; });
    var total = perCall + resident + nonTool;
    // aggregate resident + non-tool buckets (resident is a labeled estimate)
    if (resident) rows.push({ key: "resident (system prompt + schemas)", kind: "resident",
                              cost_kind: "resident", size: resident, calls: 0, is_estimate: true });
    rows.push({ key: "non-tool content", kind: "non_tool", cost_kind: "per_call",
                size: nonTool, calls: 0, is_estimate: false });
    rows.sort(function (a, b) { return b.size - a.size; });
    rows.forEach(function (r) { r.share = total ? r.size / total : 0; });
    // mounted-but-unused (over the filtered window)
    var seen = {}; cells.forEach(function (c) { seen[blob.dims.tools[c.t].key] = 1; });
    var unused = (blob.mounted_keys || []).filter(function (k) { return !seen[k]; });
    var sidechain = { size: 0, calls: 0 };
    facts.forEach(function (r) { sidechain.size += r.sidechain_size; sidechain.calls += r.sidechain_calls; });
    return { rows: rows, total: total, sidechain: sidechain, unused: unused,
             toolsUsed: Object.keys(perTool).length, resident: resident };
  }

  function aggregateHeatmap(blob, filter) {
    var cells = filterCells(blob, filter);
    var per = {};
    cells.forEach(function (c) {
      var meta = blob.dims.tools[c.t];
      var e = per[meta.key] || (per[meta.key] = { key: meta.key, kind: meta.kind, calls: 0, size: 0, t: c.t });
      e.calls += c.n; e.size += c.s;
    });
    var out = Object.keys(per).map(function (k) {
      var e = per[k], rate = blob.survival.by_tool[e.t];
      e.survival = (rate === undefined || rate === null) ? null : rate;
      return e;
    });
    out.sort(function (a, b) { return b.size - a.size; });
    return out;
  }

  function spanDays(days) {
    if (!days.length) return 0;
    var s = days.slice().sort();
    return Math.round((Date.parse(s[s.length - 1]) - Date.parse(s[0])) / 86400000) + 1;
  }
  function weekOf(day) {
    var d = new Date(day + "T00:00:00Z");
    var dow = (d.getUTCDay() + 6) % 7; // Mon=0
    d.setUTCDate(d.getUTCDate() - dow);
    return d.toISOString().slice(0, 10);
  }
  function chooseGranularity(days, dailyMax) {
    return spanDays(days) <= (dailyMax || 14) ? "day" : "week";
  }

  function aggregateTrend(blob, filter, toolKey) {
    var cells = filterCells(blob, filter);
    var wantT = toolKey ? blob.dims.tools.findIndex(function (t) { return t.key === toolKey; }) : -1;
    var days = {};
    cells.forEach(function (c) {
      if (wantT >= 0 && c.t !== wantT) return;
      var day = blob.dims.days[c.d];
      var e = days[day] || (days[day] = { n: 0, s: 0 });
      e.n += c.n; e.s += c.s;
    });
    var gran = chooseGranularity(Object.keys(days));
    var buckets = {};
    Object.keys(days).forEach(function (day) {
      var b = gran === "day" ? day : weekOf(day);
      var e = buckets[b] || (buckets[b] = { n: 0, s: 0 });
      e.n += days[day].n; e.s += days[day].s;
    });
    return Object.keys(buckets).sort().map(function (b) {
      var e = buckets[b];
      return { bucket: b, calls: e.n, total: e.s, avg_per_call: e.n ? e.s / e.n : 0 };
    });
  }

  function aggregateMode(blob, filter) {
    var cells = filterCells(blob, filter);
    var per = {};
    cells.forEach(function (c) {
      var mode = blob.dims.modes[c.m];
      var e = per[mode] || (per[mode] = { mode: mode, n: 0, s: 0, sess: {} });
      e.n += c.n; e.s += c.s; e.sess[c.sess] = 1;
    });
    return Object.keys(per).map(function (m) {
      var e = per[m], sessions = Object.keys(e.sess).length;
      return { mode: m, calls: e.n, total: e.s, sessions: sessions,
               avg_per_call: e.n ? e.s / e.n : 0,
               avg_per_session: sessions ? e.s / sessions : 0 };
    }).sort(function (a, b) { return b.total - a.total; });
  }

  function aggregateChains(blob, filter) {
    var occ = blob.chain_occurrences.filter(function (o) { return passesRow(blob, filter, o); });
    var byChain = {};
    occ.forEach(function (o) {
      var e = byChain[o.chain_id] || (byChain[o.chain_id] = { rec: 0, cost: 0, inter: 0 });
      e.rec += 1; e.cost += o.total_cost; e.inter += o.intermediate;
    });
    var shapes = {}; blob.chain_shapes.forEach(function (s) { shapes[s.chain_id] = s; });
    var out = [];
    Object.keys(byChain).forEach(function (cid) {
      var e = byChain[cid], shape = shapes[cid];
      if (!shape || e.rec < blob.min_recurrence) return;
      var avgCost = Math.round(e.cost / e.rec);
      // survival factor: mean over step tools (global rates); 1 when unavailable
      var rates = [];
      shape.steps.forEach(function (st) {
        var ti = blob.dims.tools.findIndex(function (t) { return t.key === st.signature; });
        var r = ti >= 0 ? blob.survival.by_tool[ti] : null;
        if (r !== undefined && r !== null) rates.push(r);
      });
      var surv = rates.length ? rates.reduce(function (a, b) { return a + b; }, 0) / rates.length : null;
      var factor = surv === null ? 1 : (1 - surv);
      out.push({ chain_id: cid, steps: shape.steps, proposal: shape.proposal,
                 recurrence: e.rec, avg_cost: avgCost, est_saved: Math.round(e.inter / e.rec),
                 survival: surv, score: Math.round(e.rec * avgCost * factor) });
    });
    out.sort(function (a, b) { return b.score - a.score; });
    return out;
  }

  // ---------- token-flow pure aggregation (feature 003; node-testable) ----------
  // Reads the SEPARATE blob.token_flow section — never the occupancy cube. Units: tokens only.
  var TK_KEYS = ["input", "output", "cache_write", "cache_read"];
  function emptyFlow() { return { input: 0, output: 0, cache_write: 0, cache_read: 0 }; }
  function withTotals(t) {
    t.total = t.input + t.output + t.cache_write + t.cache_read;
    t.cache_read_share = t.total ? t.cache_read / t.total : 0;  // 0 (never NaN) when total is 0
    return t;
  }
  function passesTokenSession(blob, filter, s) {
    if (filter.project && blob.dims.projects[s.p] !== filter.project) return false;
    return dayInRange(blob.dims.days[s.d], filter.from, filter.to);
  }
  function flowTotals(blob, filter) {
    var tf = blob.token_flow, t = emptyFlow();
    if (!tf) return withTotals(t);
    tf.sessions.forEach(function (s) {
      if (!passesTokenSession(blob, filter, s)) return;
      TK_KEYS.forEach(function (k) { t[k] += s.totals[k]; });
    });
    return withTotals(t);
  }
  function flowByModel(blob, filter) {
    var tf = blob.token_flow, out = {};
    if (!tf) return out;
    tf.sessions.forEach(function (s) {
      if (!passesTokenSession(blob, filter, s)) return;
      Object.keys(s.by_model).forEach(function (m) {
        var a = out[m] || (out[m] = emptyFlow());
        TK_KEYS.forEach(function (k) { a[k] += s.by_model[m][k]; });
      });
    });
    Object.keys(out).forEach(function (m) { withTotals(out[m]); });
    return out;  // Σ flowByModel === flowTotals (parts reconcile to whole; FR-009)
  }
  function flowByDay(blob, filter) {
    var tf = blob.token_flow;
    if (!tf) return [];
    var days = {};
    (tf.by_day || []).forEach(function (r) {
      if (filter.project && blob.dims.projects[r.p] !== filter.project) return;
      var day = blob.dims.days[r.d];
      if (day === "undated") return;                         // can't place on the time axis
      if (!dayInRange(day, filter.from, filter.to)) return;
      var e = days[day] || (days[day] = emptyFlow());
      TK_KEYS.forEach(function (k) { e[k] += r[k]; });
    });
    var gran = chooseGranularity(Object.keys(days));
    var buckets = {};
    Object.keys(days).forEach(function (day) {
      var b = gran === "day" ? day : weekOf(day);
      var e = buckets[b] || (buckets[b] = emptyFlow());
      TK_KEYS.forEach(function (k) { e[k] += days[day][k]; });
    });
    return Object.keys(buckets).sort().map(function (b) {
      return withTotals(Object.assign({ bucket: b }, buckets[b]));
    });
  }
  function sessionGrowth(blob, sessionId) {
    var tf = blob.token_flow;
    if (!tf) return [];
    var s = tf.sessions.filter(function (x) { return x.session === sessionId; })[0];
    return s ? s.growth : [];
  }
  function costEstimate(blob) {  // present ONLY when a non-empty prices.json was loaded (US4)
    var tf = blob.token_flow;
    return tf && tf.cost && tf.cost.available ? tf.cost : null;
  }

  var API = {
    dayInRange: dayInRange, passesCell: passesCell, filterCells: filterCells,
    aggregateBreakdown: aggregateBreakdown, aggregateHeatmap: aggregateHeatmap,
    aggregateTrend: aggregateTrend, aggregateMode: aggregateMode,
    aggregateChains: aggregateChains, chooseGranularity: chooseGranularity, weekOf: weekOf,
    spanDays: spanDays,
    flowTotals: flowTotals, flowByModel: flowByModel, flowByDay: flowByDay,
    sessionGrowth: sessionGrowth, costEstimate: costEstimate
  };

  if (typeof module !== "undefined" && module.exports) { module.exports = API; return; }

  // ---------- browser branch: DOM + rendering ----------
  var BLOB = JSON.parse(document.getElementById("thl-data").textContent);
  var UNIT = BLOB.unit;
  var TF = BLOB.token_flow || null;                 // feature 003: the separate token-flow section
  var filter = Object.assign({ project: null, from: null, to: null }, BLOB.initial_filter || {});
  var selectedTool = null;
  var lens = "occupancy";                           // "occupancy" (chars) | "tokens" (flow)
  var selectedGrowth = null;                        // selected session id for the re-billing curve
  var esc = function (s) { return String(s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
  var fmt = function (n) { return Math.round(n).toLocaleString(); };
  var human = function (n) { n = +n; if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1) + "B";
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "k"; return String(Math.round(n)); };
  var shortKey = function (k) { return k.indexOf("mcp:") === 0 && k.indexOf("/") > 0
    ? k.split("/").slice(1).join("/") : (k.indexOf("builtin:") === 0 ? k.slice(8) : k); };
  var el = function (id) { return document.getElementById(id); };
  var kindClass = function (kind) { return kind === "mcp_tool" ? "k-mcp"
    : kind === "resident" ? "k-res" : kind === "non_tool" ? "k-nontool"
    : kind === "unattributed" ? "k-unattr" : "k-builtin"; };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function addDays(day, n) { var d = new Date(day + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10); }
  function fmtDay(day) { var p = day.split("-"); return MON[+p[1] - 1] + " " + (+p[2]); }
  function fmtRange(a, b) { var ya = a.slice(0, 4), yb = b.slice(0, 4);
    return fmtDay(a) + (ya !== yb ? ", " + ya : "") + " – " + fmtDay(b) + ", " + yb; }

  function render() {
    var bd = aggregateBreakdown(BLOB, filter);
    var empty = bd.total === 0 && aggregateChains(BLOB, filter).length === 0;
    el("empty").style.display = empty ? "block" : "none";
    el("views").style.display = empty ? "none" : "block";
    if (empty) return;
    renderKpis(bd);
    renderBreakdown(bd);
    renderHeatmap();
    if (!selectedTool) {
      var top = aggregateHeatmap(BLOB, filter)[0];
      selectedTool = top ? top.key : null;
    }
    renderTrend();
    renderMode();
    renderChains();
  }

  // ---- lens switch (feature 003): show one lens or the other; both share the filter ----
  function renderActive() { if (lens === "tokens") renderTokens(); else render(); }
  function setLens(l) {
    lens = l;
    el("views").style.display = l === "occupancy" ? "" : "none";
    el("token-views").style.display = l === "tokens" ? "" : "none";
    [].slice.call(document.querySelectorAll("#lensswitch .lensbtn")).forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-lens") === l); });
    renderActive();
  }
  function setupLensSwitch() {
    [].slice.call(document.querySelectorAll("#lensswitch .lensbtn")).forEach(function (b) {
      b.addEventListener("click", function () { setLens(b.getAttribute("data-lens")); }); });
  }
  function moneyFmt(v, currency) {
    if (v === undefined || v === null) return "—";
    var s = (+v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return (currency === "USD" || !currency) ? "$" + s : s + " " + currency;
  }

  function renderKpis(bd) {
    var chains = aggregateChains(BLOB, filter);
    var topSave = chains.reduce(function (m, c) { return Math.max(m, c.est_saved); }, 0);
    var cmp = BLOB.compaction || {};
    var residentPct = bd.total ? (bd.resident / bd.total * 100) : 0;
    var tiles = [
      ["hero", "Context window", human(bd.total), UNIT, "filtered, main-thread"],
      ["", "Tools invoked", String(bd.toolsUsed), "", "distinct tools"],
      ["", "Resident overhead", residentPct.toFixed(0) + "%", "of window", "schemas+prompt · est"],
      ["cut", "Unused mounted", String(bd.unused.length), "", "in this window"],
      ["", "Recurring chains", String(chains.length), "", "data-dependent"],
      ["hero", "Top chain saving", human(topSave), UNIT, "if collapsed · est"]
    ];
    if (cmp.events) tiles.push(["", "Context retained",
      (cmp.retention_pct || 0).toFixed(0) + "%", "post-compaction", cmp.events + " compaction(s) · exact"]);
    el("kpis").innerHTML = tiles.map(function (t) {
      return "<div class='kpi " + t[0] + "'><p class='eyebrow'>" + esc(t[1]) + "</p>" +
        "<div class='v'>" + esc(t[2]) + " <span class='u'>" + esc(t[3]) + "</span></div>" +
        "<div class='sub'>" + esc(t[4]) + "</div></div>"; }).join("");
  }

  function renderBreakdown(bd) {
    var maxs = bd.rows.reduce(function (m, r) { return Math.max(m, r.size); }, 1);
    var body = bd.rows.map(function (r) {
      var est = r.is_estimate ? " <span class='chip est'>est</span>" : "";
      var w = maxs ? (r.size / maxs * 100) : 0;
      return "<div class='row'><span class='sw' style='background:var(--" + kindVar(r.kind) + ")'></span>" +
        "<span class='name'><span class='tkhelp' data-tip='" + esc(r.key) + "' data-sub='" + esc(kindHelp(r.kind)) + "'>" +
          esc(r.key) + "</span>" + est + "</span>" +
        "<span class='track'><span class='" + (r.is_estimate ? "hatch" : "") +
          "' style='width:" + w.toFixed(1) + "%;background:var(--" + kindVar(r.kind) + ")'></span></span>" +
        "<span class='n big'>" + fmt(r.size) + "</span><span class='n'>" + fmt(r.calls) + "</span>" +
        "<span class='n'>" + (r.share * 100).toFixed(1) + "%</span></div>"; }).join("");
    var unused = bd.unused.length
      ? "<p class='sidechain'>Mounted but unused in this window (" + bd.unused.length + "): " +
        bd.unused.slice(0, 12).map(function (k) { return "<code>" + esc(shortKey(k)) + "</code>"; }).join(" ") + "</p>"
      : "";
    el("view-spend").innerHTML = section("01", "Where the context goes",
      "Share of the filtered main-thread window, by size. Resident is a labeled estimate. "
      + "Hover any source for what it means.") +
      "<div class='rows'><div class='row rhead'><span></span><span class='name'>Source</span>" +
      "<span class='track'></span><span class='n'>Size</span><span class='n'>Calls</span><span class='n'>Share</span></div>" +
      body + "</div><div class='total-row'><span>total</span><b>" + fmt(bd.total) + " " + esc(UNIT) + "</b></div>" +
      "<p class='sidechain'>Sidechain (separate windows, excluded): <b>" + fmt(bd.sidechain.size) +
      " " + esc(UNIT) + "</b> · " + bd.sidechain.calls + " call(s).</p>" + unused;
  }
  function kindVar(kind) { return kind === "mcp_tool" ? "k-mcp" : kind === "resident" ? "estimate"
    : kind === "non_tool" ? "k-nontool" : kind === "unattributed" ? "k-unattr" : "k-builtin"; }
  function kindHelp(kind) { return {   // plain-language explanation shown on hover (feature 004 pattern)
    builtin: "A built-in Claude Code tool. Size is the characters of its call inputs plus the results it "
      + "returned, summed over the filtered window — exact, not estimated.",
    mcp_tool: "An MCP tool (server/tool). Size is the characters of its call inputs plus returned results; "
      + "MCP results are often the single largest source in a window.",
    resident: "System prompt + every mounted tool's schema — overhead that rides in the window and is "
      + "re-sent each turn. A labeled estimate, not an exact count (that's why it carries the est tag).",
    non_tool: "Your messages, the model's text and thinking, and attachments on the main thread — "
      + "everything that isn't a tool call or its result.",
    unattributed: "Tool calls we couldn't map to a specific built-in or MCP tool (for example, a CLI-wrapped "
      + "invocation). Kept as its own bucket rather than guessed."
  }[kind] || ""; }

  function renderHeatmap() {
    var cells = aggregateHeatmap(BLOB, filter);
    el("view-heatmap").innerHTML = section("02", "Tool heatmap",
      "Every invoked tool by call frequency (x) and volume (y), log–log. Warm = low survival "
      + "(<span class='chip est'>estimate</span>, all data); grey = unavailable.") + scatterSVG(cells) +
      "<div class='hlegend'><span class='item'><span class='d' style='background:var(--k-builtin)'></span>built-in</span>"
      + "<span class='item'><span class='d' style='background:var(--k-mcp)'></span>MCP</span></div>";
  }

  function renderTrend() {
    var tools = aggregateHeatmap(BLOB, filter).map(function (c) { return c.key; });
    var opts = tools.map(function (k) { return "<option value='" + esc(k) + "'" +
      (k === selectedTool ? " selected" : "") + ">" + esc(shortKey(k)) + "</option>"; }).join("");
    var series = aggregateTrend(BLOB, filter, selectedTool);
    el("view-trend").innerHTML = section("03", "Cost over time",
      "Average size <b>per call</b> over time for the selected tool — the metric a limit/offset "
      + "optimization moves. Not a raw sum, so a change in call frequency can't hide it.") +
      "<div class='ctl'><label>Tool <select id='toolsel'>" + opts + "</select></label></div>" +
      lineChart(series, "avg_per_call");
    var sel = el("toolsel");
    if (sel) sel.addEventListener("change", function () { selectedTool = sel.value; renderTrend(); });
  }

  function renderMode() {
    var segs = aggregateMode(BLOB, filter);
    var maxc = segs.reduce(function (m, s) { return Math.max(m, s.avg_per_call); }, 1);
    var maxs = segs.reduce(function (m, s) { return Math.max(m, s.avg_per_session); }, 1);
    var rows = segs.map(function (s) {
      return "<div class='moderow'><span class='mname'>" + esc(s.mode) + "</span>" +
        "<span class='mbar'><span style='width:" + (s.avg_per_call / maxc * 100).toFixed(0) + "%'></span></span>" +
        "<span class='n'>" + fmt(s.avg_per_call) + "/call</span>" +
        "<span class='mbar'><span class='alt' style='width:" + (s.avg_per_session / maxs * 100).toFixed(0) + "%'></span></span>" +
        "<span class='n'>" + fmt(s.avg_per_session) + "/session</span>" +
        "<span class='n muted'>" + s.sessions + " sess</span></div>"; }).join("");
    el("view-mode").innerHTML = section("04", "Cost by working mode",
      "Average context per call and per session, by mode. A session that changed mode counts "
      + "toward <b>each</b> mode it used, so per-mode session counts can overlap.") +
      "<div class='modeview'>" + rows + "</div>";
  }

  function renderChains() {
    var chains = aggregateChains(BLOB, filter);
    var cards = chains.length ? chains.map(function (c, i) {
      var pipe = c.steps.map(function (s, j) {
        return (j ? "<span class='conn'></span>" : "") + "<span class='node" + (s.fanout ? " fan" : "") + "'>" +
          esc(shortKey(s.signature)) + (s.fanout ? "<i class='fantag'>fan-out</i>" : "") + "</span>"; }).join("");
      var p = c.proposal;
      return "<div class='chain'><div class='chain-head'><span class='rank'>" + (i + 1) + "</span>" +
        "<p class='eyebrow' style='margin:0'>recurs " + c.recurrence + "×</p>" +
        "<div class='save'><div class='v'>" + human(c.est_saved) + " " + esc(UNIT) + "</div><div class='l'>est. saved/session</div></div></div>" +
        "<div class='pipe'>" + pipe + "</div>" +
        "<div class='metrics'><span>avg cost <b>" + fmt(c.avg_cost) + "</b></span><span>score <b>" + fmt(c.score) + "</b></span></div>" +
        "<div class='proposal'>💡 <span class='pname'>" + esc(p.suggested_name) + "</span> · in: <code>" +
        esc(p.inputs.join(", ")) + "</code> · out: <code>" + esc(p.output) + "</code></div></div>"; }).join("")
      : "<p class='muted'>No recurring data-dependent chains in this window.</p>";
    el("view-chains").innerHTML = section("05", "The through lines",
      "Recurring, data-dependent chains in the filtered window, ranked by estimated saving.") + cards;
  }

  // ================= token-usage lens (feature 003) =================
  // [key, label, css var, plain-language meaning] — the meaning is shown as hover help (feature 004)
  var TK_META = [
    ["input", "input", "k-builtin",
      "Fresh, uncached tokens you send this turn — new prompt content (usage.input_tokens)."],
    ["output", "output", "k-nontool",
      "Tokens the model generates back to you this turn (usage.output_tokens)."],
    ["cache_write", "cache-write", "estimate",
      "Context written into the prompt cache the first time — paid once when it's cached (cache_creation)."],
    ["cache_read", "cache-read", "thread-b",
      "Cached context re-sent and re-billed on EVERY turn (cache_read). A high share means you're mostly "
      + "paying to carry the same context forward, turn after turn, instead of /clear-ing and starting a "
      + "fresh, smaller task."]
  ];

  function renderTokens() {
    if (!TF) { el("empty").style.display = "block"; el("token-views").style.display = "none"; return; }
    var totals = flowTotals(BLOB, filter);
    var empty = totals.total === 0;
    el("empty").style.display = empty ? "block" : "none";
    el("token-views").style.display = empty ? "none" : "block";
    if (empty) return;
    renderTokenKpis(totals);
    renderTokenFlow(totals);
    renderTokenGrowth();
    renderTokenTrend();
    renderTokenCost();
  }

  function renderTokenKpis(totals) {
    var cov = TF.coverage || { sessions_total: 0, sessions_no_usage: 0 };
    var cost = costEstimate(BLOB);
    var tiles = [
      ["hero", "Total tokens", human(totals.total), "flow · exact", "input + output + cache, filtered"],
      ["hero", "Cache-read share", (totals.cache_read_share * 100).toFixed(1) + "%", "of tokens", "context re-billed each turn"],
      ["", "Cache-read", human(totals.cache_read), "tokens", "read back every turn"],
      ["", "Output", human(totals.output), "tokens", "generated · exact"]
    ];
    if (cost) tiles.push(["hero", "Est. cost", moneyFmt(cost.total, cost.currency), "estimate", "all sessions · " + cost.unit_label]);
    if (cov.sessions_no_usage > 0) tiles.push(["cut", "Partial coverage",
      cov.sessions_no_usage + "/" + cov.sessions_total, "sessions", "no usage data — excluded"]);
    el("token-kpis").innerHTML = tiles.map(function (t) {
      return "<div class='kpi " + t[0] + "'><p class='eyebrow'>" + esc(t[1]) + "</p>" +
        "<div class='v'>" + esc(t[2]) + " <span class='u'>" + esc(t[3]) + "</span></div>" +
        "<div class='sub'>" + esc(t[4]) + "</div></div>"; }).join("");
  }

  function renderTokenFlow(totals) {
    var maxv = Math.max(totals.input, totals.output, totals.cache_write, totals.cache_read, 1);
    var bars = TK_META.map(function (m) {
      var v = totals[m[0]], w = (v / maxv * 100).toFixed(1);
      var share = totals.total ? (v / totals.total * 100).toFixed(1) : "0.0";
      return "<div class='tkrow'><span class='sw' style='background:var(--" + m[2] + ")'></span>" +
        "<span class='name tkhelp' data-tip='" + esc(m[1]) + "' data-sub='" + esc(m[3]) + "'>" + esc(m[1]) + "</span>" +
        "<span class='tktrack'><span style='width:" + w + "%;background:var(--" + m[2] + ")'></span></span>" +
        "<span class='n big'>" + fmt(v) + "</span><span class='n'>" + share + "%</span></div>"; }).join("");
    // per-model breakdown (FR-009) — parts reconcile to the total above
    var bm = flowByModel(BLOB, filter);
    var models = Object.keys(bm).sort(function (a, b) { return bm[b].total - bm[a].total; });
    var mRows = models.map(function (mid) { var v = bm[mid];
      return "<tr><td class='l mdl'>" + esc(mid) + "</td><td>" + fmt(v.input) + "</td><td>" + fmt(v.output) +
        "</td><td>" + fmt(v.cache_write) + "</td><td>" + fmt(v.cache_read) + "</td><td class='big'>" + fmt(v.total) + "</td></tr>"; }).join("");
    var mSum = models.reduce(function (a, m) { return a + bm[m].total; }, 0);
    var mTable = "<table class='tktable'><thead><tr><th class='l'>model</th><th>input</th><th>output</th>" +
      "<th>cache-write</th><th>cache-read</th><th>total</th></tr></thead><tbody>" + mRows +
      "<tr class='sum'><td class='l'>all models</td><td></td><td></td><td></td><td></td><td>" + fmt(mSum) + "</td></tr></tbody></table>";
    // heaviest sessions in the window
    var sess = TF.sessions.filter(function (s) { return passesTokenSession(BLOB, filter, s); })
      .map(function (s) { var t = s.totals, tot = t.input + t.output + t.cache_write + t.cache_read;
        return { id: s.session, turns: s.turns, tot: tot, cr: tot ? t.cache_read / tot : 0 }; })
      .filter(function (s) { return s.tot > 0; })
      .sort(function (a, b) { return b.tot - a.tot; }).slice(0, 12);
    var sRows = sess.map(function (s) {
      return "<tr><td class='l mdl'>" + esc(s.id) + "</td><td>" + s.turns + "</td><td class='big'>" + fmt(s.tot) +
        "</td><td>" + (s.cr * 100).toFixed(0) + "%</td></tr>"; }).join("");
    var sTable = "<table class='tktable'><thead><tr><th class='l'>session</th><th>turns</th><th>tokens</th>" +
      "<th>cache-read</th></tr></thead><tbody>" + sRows + "</tbody></table>";
    var cov = TF.coverage || {};
    var note = cov.sessions_no_usage > 0
      ? "<p class='tknote'>Partial coverage: <b>" + cov.sessions_no_usage + "</b> of " + cov.sessions_total +
        " session(s) carried no usage data and are excluded — totals reflect the rest, not a complete bill.</p>" : "";
    var shareTip = "The share of all tokens that are cache-read: cached context re-sent and re-billed "
      + "every turn. The higher it is, the more you're paying to keep carrying context instead of "
      + "running /clear and starting a fresh, smaller task.";
    el("tview-flow").innerHTML = section("01", "Token flow by type",
      "Exact per-turn token spend, summed over the filtered window. <span class='chip exact'>exact</span> "
      + "reads from each turn's usage — not estimated. Cache-read is context <b>re-billed every turn</b>.") +
      "<div class='tkshare'><span class='big tkhelp' data-tip='cache-read share' data-sub='" + esc(shareTip) + "'>"
      + (totals.cache_read_share * 100).toFixed(1) + "%</span>" +
      "<span class='lbl'>of all tokens are <b>cache-read</b> — the resident window paid again on every turn ("
      + human(totals.cache_read) + " of " + human(totals.total) + " tokens)</span></div>" +
      // always-visible caption (never hover-gated): the headline cache-read lesson in plain language
      "<p class='tkcaption'>Cache-read is the context you <b>carry forward and pay for again on every "
      + "turn</b>. A high share means most of your spend is re-paying to keep context alive — so it's "
      + "often cheaper to <span class='mono'>/clear</span> and start a fresh, smaller task than to keep "
      + "one session growing. Hover any type below for what it means.</p>" +
      "<div class='rows'>" + bars + "</div>" +
      "<div class='panel-head' style='margin-top:22px'><h2 style='font-size:14px'>By model</h2></div>" +
      "<p class='lede'>Per-model split; the parts reconcile to the total above (FR-009).</p>" + mTable +
      "<div class='panel-head' style='margin-top:22px'><h2 style='font-size:14px'>By session</h2></div>" +
      "<p class='lede'>Heaviest sessions in the window, each with its cache-read share.</p>" + sTable + note;
  }

  function renderTokenGrowth() {
    var sess = TF.sessions.filter(function (s) { return passesTokenSession(BLOB, filter, s) && s.turns > 0; })
      .map(function (s) { var t = s.totals; return { id: s.session, tot: t.input + t.output + t.cache_write + t.cache_read }; })
      .sort(function (a, b) { return b.tot - a.tot; });
    if (!sess.length) { el("tview-growth").innerHTML = section("02", "Re-billing growth over a session",
      "How a session's cumulative token cost grows turn by turn.") +
      "<p class='muted'>No sessions with token usage in this window.</p>"; return; }
    if (!selectedGrowth || !sess.some(function (s) { return s.id === selectedGrowth; })) selectedGrowth = sess[0].id;
    var opts = sess.map(function (s) { return "<option value='" + esc(s.id) + "'" +
      (s.id === selectedGrowth ? " selected" : "") + ">" + esc(s.id) + " (" + human(s.tot) + ")</option>"; }).join("");
    el("tview-growth").innerHTML = section("02", "Re-billing growth over a session",
      "Cumulative tokens across a session's turns. The filled band is <b>cache-read</b> — the context "
      + "re-sent (and re-billed) every turn — which is what makes long sessions expensive.") +
      "<div class='ctl'><label>Session <select id='growthsel'>" + opts + "</select></label></div>" +
      growthChart(sessionGrowth(BLOB, selectedGrowth));
    var sel = el("growthsel");
    if (sel) sel.addEventListener("change", function () { selectedGrowth = sel.value; renderTokenGrowth(); });
  }

  function renderTokenTrend() {
    var series = flowByDay(BLOB, filter);
    var chart = lineChart(series, "total", { yTitle: "tokens →",
      subFn: function (p) { return fmt(p.total) + " tokens · cache-read " + (p.cache_read_share * 100).toFixed(0) + "%"; } });
    var deltas = markerDeltas(series, BLOB.interventions);
    var dhtml = deltas.length ? "<div class='tkdelta'>" + deltas.map(function (d) {
      var cls = d.pct > 0 ? "d-up" : "d-dn", arrow = d.pct > 0 ? "▲" : "▼";
      return "<span><b>" + esc(d.label) + "</b> (" + esc(d.date) + "): mean daily tokens <b>" + human(d.before) +
        "</b> → <b>" + human(d.after) + "</b> <span class='" + cls + "'>" + arrow + " " + Math.abs(d.pct).toFixed(0) + "%</span></span>"; }).join("") + "</div>" : "";
    el("tview-trend").innerHTML = section("03", "Token spend over time",
      "Total tokens per bucket, honoring the repo/time filter. Intervention markers show when you changed "
      + "how you work; the deltas below <b>read</b> the before/after change in mean daily tokens (SC-003).") + chart + dhtml;
  }

  function markerDeltas(series, interventions) {
    var mean = function (a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : 0; };
    return (interventions || []).map(function (iv) {
      var before = [], after = [];
      series.forEach(function (p) { (p.bucket < iv.date ? before : after).push(p.total); });
      var mb = mean(before), ma = mean(after);
      return { date: iv.date, label: iv.label, before: mb, after: ma,
               pct: mb ? (ma - mb) / mb * 100 : 0, hasBoth: before.length > 0 && after.length > 0 };
    }).filter(function (d) { return d.hasBoth; });
  }

  function renderTokenCost() {
    var cost = costEstimate(BLOB);
    if (!cost) { el("tview-cost").style.display = "none"; el("tview-cost").innerHTML = ""; return; }
    el("tview-cost").style.display = "";
    var cur = cost.currency;
    var models = Object.keys(cost.by_model).sort();
    var rows = models.map(function (mid) {
      var c = cost.by_model[mid];
      if (!c.priced) return "<tr><td class='l mdl'>" + esc(mid) +
        "</td><td class='l tkunpriced' colspan='5'>unpriced — not in prices.json (never guessed)</td></tr>";
      return "<tr><td class='l mdl'>" + esc(mid) + "</td><td>" + moneyFmt(c.input, cur) + "</td><td>" + moneyFmt(c.output, cur) +
        "</td><td>" + moneyFmt(c.cache_write, cur) + "</td><td>" + moneyFmt(c.cache_read, cur) + "</td><td class='big'>" + moneyFmt(c.total, cur) + "</td></tr>"; }).join("");
    var table = "<table class='tktable'><thead><tr><th class='l'>model</th><th>input</th><th>output</th>" +
      "<th>cache-write</th><th>cache-read</th><th>total</th></tr></thead><tbody>" + rows +
      "<tr class='sum'><td class='l'>estimated total</td><td></td><td></td><td></td><td></td><td>" + moneyFmt(cost.total, cur) + "</td></tr></tbody></table>";
    el("tview-cost").innerHTML = section("04", "Estimated cost",
      "<span class='chip est'>estimate</span> from your <span class='mono'>prices.json</span> — " + esc(cost.unit_label) +
      (cost.effective ? ", prices as of " + esc(cost.effective) : "") +
      ". Covers all collected sessions. Models absent from your price list are shown <b>unpriced</b>, never guessed.") + table;
  }

  function growthChart(growth) {
    if (!growth.length) return "<p class='muted'>No turns.</p>";
    var W = 720, H = 300, pad = 62;
    var last = growth[growth.length - 1];
    var maxTot = (last.cum_input + last.cum_output + last.cum_write + last.cum_read) || 1;
    var maxI = last.i || 1;
    var x = function (i) { return pad + (maxI ? i / maxI : 0) * (W - 2 * pad); };
    var y = function (v) { return H - pad - (v / maxTot) * (H - 2 * pad); };
    var TICKS = 4, grid = "";
    for (var t = 0; t <= TICKS; t++) { var gv = maxTot * t / TICKS, gy = y(gv);
      grid += "<line class='grid' x1='" + pad + "' y1='" + gy.toFixed(1) + "' x2='" + (W - pad) + "' y2='" + gy.toFixed(1) + "'/>" +
        "<text class='tickval' x='" + (pad - 8) + "' y='" + (gy + 3).toFixed(1) + "' text-anchor='end'>" + human(gv) + "</text>"; }
    var axis = "<line class='axis' x1='" + pad + "' y1='" + pad + "' x2='" + pad + "' y2='" + (H - pad) + "'/>" +
      "<line class='axis' x1='" + pad + "' y1='" + (H - pad) + "' x2='" + (W - pad) + "' y2='" + (H - pad) + "'/>";
    var readPts = [], totPts = [], dots = "";
    growth.forEach(function (g) {
      var tot = g.cum_input + g.cum_output + g.cum_write + g.cum_read;
      var cx = x(g.i), cyR = y(g.cum_read), cyT = y(tot);
      readPts.push(cx.toFixed(1) + "," + cyR.toFixed(1));
      totPts.push(cx.toFixed(1) + "," + cyT.toFixed(1));
      var sub = "cumulative total " + fmt(tot) + " · cache-read " + fmt(g.cum_read);
      dots += "<circle cx='" + cx.toFixed(1) + "' cy='" + cyT.toFixed(1) + "' r='11' fill='transparent' data-tip='turn " + g.i + "' data-sub='" + esc(sub) + "'/>"; });
    var area = pad + "," + (H - pad) + " " + readPts.join(" ") + " " + x(maxI).toFixed(1) + "," + (H - pad);
    return "<svg viewBox='0 0 " + W + " " + H + "' class='thl-scatter'>" + grid + axis +
      "<polygon class='tkarea' points='" + area + "'/>" +
      "<polyline class='tkline' points='" + readPts.join(" ") + "'/>" +
      "<polyline class='tktotal' points='" + totPts.join(" ") + "'/>" + dots +
      "<text class='axtitle' x='" + (W / 2) + "' y='" + (H - 6) + "' text-anchor='middle'>turn index →</text>" +
      "<text class='axtitle' x='13' y='" + (H / 2) + "' transform='rotate(-90 13 " + (H / 2) + ")' text-anchor='middle'>cumulative tokens →</text></svg>";
  }

  // ---- small chart builders ----
  function section(idx, title, lede) {
    return "<div class='panel-head'><span class='idx'>" + idx + "</span><h2>" + esc(title) + "</h2></div>" +
      "<p class='lede'>" + lede + "</p>";
  }
  function lineChart(series, key, opts) {
    if (!series.length) return "<p class='muted'>No data in this window.</p>";
    opts = opts || {};
    var yTitle = opts.yTitle || ("avg " + UNIT + "/call →");
    var subOf = opts.subFn || function (p) {
      return fmt(p[key]) + " " + UNIT + "/call · " + p.calls + " call" + (p.calls === 1 ? "" : "s"); };
    var W = 720, H = 300, pad = 62;
    var max = series.reduce(function (m, p) { return Math.max(m, p[key]); }, 1) || 1;
    var n = series.length;
    var x = function (i) { return pad + (n <= 1 ? 0.5 : i / (n - 1)) * (W - 2 * pad); };
    var y = function (v) { return H - pad - (v / max) * (H - 2 * pad); };
    // y-axis: gridlines + value ticks
    var TICKS = 4, grid = "";
    for (var t = 0; t <= TICKS; t++) {
      var gv = max * t / TICKS, gy = y(gv);
      grid += "<line class='grid' x1='" + pad + "' y1='" + gy.toFixed(1) + "' x2='" + (W - pad) + "' y2='" + gy.toFixed(1) + "'/>" +
        "<text class='tickval' x='" + (pad - 8) + "' y='" + (gy + 3).toFixed(1) + "' text-anchor='end'>" + human(gv) + "</text>";
    }
    var axis = "<line class='axis' x1='" + pad + "' y1='" + pad + "' x2='" + pad + "' y2='" + (H - pad) + "'/>" +
      "<line class='axis' x1='" + pad + "' y1='" + (H - pad) + "' x2='" + (W - pad) + "' y2='" + (H - pad) + "'/>";
    var pts = series.map(function (p, i) { return x(i).toFixed(1) + "," + y(p[key]).toFixed(1); });
    var dots = series.map(function (p, i) {
      var cx = x(i).toFixed(1), cy = y(p[key]).toFixed(1);
      var sub = subOf(p);
      return "<circle cx='" + cx + "' cy='" + cy + "' r='4' class='pt'/>" +
        "<circle cx='" + cx + "' cy='" + cy + "' r='13' fill='transparent' data-tip='" + esc(p.bucket) + "' data-sub='" + esc(sub) + "'/>" +
        "<text class='tick' x='" + cx + "' y='" + (H - pad + 16) + "' text-anchor='middle'>" + esc(p.bucket.slice(5)) + "</text>"; }).join("");
    var markers = (BLOB.interventions || []).map(function (iv) {
      // place marker between buckets by date
      var idx = -1; for (var i = 0; i < series.length; i++) { if (series[i].bucket <= iv.date) idx = i; }
      if (idx < 0) return "";
      var mx = x(Math.min(idx + 0.5, n - 1)).toFixed(1);
      return "<line class='marker' x1='" + mx + "' y1='" + pad + "' x2='" + mx + "' y2='" + (H - pad) + "'/>" +
        "<line x1='" + mx + "' y1='" + pad + "' x2='" + mx + "' y2='" + (H - pad) + "' stroke='transparent' stroke-width='12' data-tip='" + esc(iv.date) + "' data-sub='" + esc(iv.label) + "'/>"; }).join("");
    return "<svg viewBox='0 0 " + W + " " + H + "' class='thl-scatter'>" + grid + axis +
      "<polyline class='trendline' points='" + pts.join(" ") + "'/>" + markers + dots +
      "<text class='axtitle' x='13' y='" + (H / 2) + "' transform='rotate(-90 13 " + (H / 2) + ")' text-anchor='middle'>" + esc(yTitle) + "</text></svg>";
  }
  function scatterSVG(cells) {
    if (!cells.length) return "<p class='muted'>No tool calls.</p>";
    var W = 720, H = 380, pl = 62, pr = 22, pt = 18, pb = 48;
    var lg = function (v) { return Math.log10(v + 1); };
    var maxCalls = cells.reduce(function (m, c) { return Math.max(m, c.calls); }, 1);
    var maxSize = cells.reduce(function (m, c) { return Math.max(m, c.size); }, 1);
    var xmax = lg(maxCalls) || 1, ymax = lg(maxSize) || 1;
    var px = function (v) { return pl + lg(v) / xmax * (W - pl - pr); };
    var py = function (v) { return H - pb - lg(v) / ymax * (H - pt - pb); };
    // log-scale ticks at powers of ten
    function pow10(maxRaw) { var out = []; for (var p = 0; Math.pow(10, p) <= maxRaw * 1.05; p++) out.push(Math.pow(10, p)); return out.length ? out : [1]; }
    var grid = "";
    pow10(maxCalls).forEach(function (v) { var gx = px(v).toFixed(1);
      grid += "<line class='grid' x1='" + gx + "' y1='" + pt + "' x2='" + gx + "' y2='" + (H - pb) + "'/>" +
        "<text class='tickval' x='" + gx + "' y='" + (H - pb + 15) + "' text-anchor='middle'>" + human(v) + "</text>"; });
    pow10(maxSize).forEach(function (v) { var gy = py(v).toFixed(1);
      grid += "<line class='grid' x1='" + pl + "' y1='" + gy + "' x2='" + (W - pr) + "' y2='" + gy + "'/>" +
        "<text class='tickval' x='" + (pl - 8) + "' y='" + (+gy + 3).toFixed(1) + "' text-anchor='end'>" + human(v) + "</text>"; });
    var axis = "<line class='axis' x1='" + pl + "' y1='" + pt + "' x2='" + pl + "' y2='" + (H - pb) + "'/>" +
      "<line class='axis' x1='" + pl + "' y1='" + (H - pb) + "' x2='" + (W - pr) + "' y2='" + (H - pb) + "'/>";
    var dots = cells.map(function (c) {
      var r = 5 + 12 * (lg(c.size) / ymax);
      var cls = c.kind === "mcp_tool" ? "k-mcp" : c.kind === "unattributed" ? "k-unattr" : "k-builtin";
      var op = (c.survival === null) ? "" : " style='opacity:" + (0.45 + 0.5 * (1 - c.survival)).toFixed(2) + "'";
      var avg = c.calls ? Math.round(c.size / c.calls) : 0;
      var sub = c.calls + " calls · " + fmt(c.size) + " " + UNIT + " · avg " + fmt(avg) + "/call" +
        (c.survival === null ? "" : " · survival " + Math.round(c.survival * 100) + "%");
      return "<circle class='dot " + cls + "' cx='" + px(c.calls).toFixed(1) + "' cy='" + py(c.size).toFixed(1) +
        "' r='" + r.toFixed(1) + "'" + op + " data-tip='" + esc(shortKey(c.key)) + "' data-sub='" + esc(sub) + "'/>"; }).join("");
    var placed = [], labels = "";
    cells.slice(0, 8).forEach(function (c) {
      var cx = px(c.calls), cy = py(c.size);
      for (var k = 0; k < placed.length; k++) {          // greedy de-collision: drop overlapping labels (hover still shows them)
        if (Math.abs(placed[k][0] - cx) < 60 && Math.abs(placed[k][1] - cy) < 16) return;
      }
      placed.push([cx, cy]);
      var right = cx > W - 90;
      labels += "<text class='ptlabel' x='" + ((right ? cx - 9 : cx + 9)).toFixed(1) + "' y='" + (cy - 8).toFixed(1) +
        "' text-anchor='" + (right ? "end" : "start") + "'>" + esc(shortKey(c.key)) + "</text>"; });
    var midx = ((pl + W - pr) / 2), midy = ((pt + H - pb) / 2);
    return "<svg viewBox='0 0 " + W + " " + H + "' class='thl-scatter'>" + grid + axis + dots + labels +
      "<text class='axtitle' x='" + midx + "' y='" + (H - 6) + "' text-anchor='middle'>calls →</text>" +
      "<text class='axtitle' x='14' y='" + midy + "' transform='rotate(-90 14 " + midy + ")' text-anchor='middle'>" + esc(UNIT) + " returned →</text></svg>";
  }

  // ---- filter bar ----
  function buildFilterBar() {
    var projOpts = "<option value=''>All repos</option>" + BLOB.dims.projects.map(function (p) {
      return "<option value='" + esc(p) + "'" + (p === filter.project ? " selected" : "") + ">" +
        esc(p.split("/").slice(-2).join("/")) + "</option>"; }).join("");
    var days = BLOB.dims.days.filter(function (d) { return d !== "undated"; });
    var minD = days[0] || "", maxD = days[days.length - 1] || "";
    el("filterbar").innerHTML =
      "<label>Repo <select id='f-proj'>" + projOpts + "</select></label>" +
      "<label>From <input type='date' id='f-from' min='" + minD + "' max='" + maxD + "' value='" + (filter.from || "") + "'></label>" +
      "<label>To <input type='date' id='f-to' min='" + minD + "' max='" + maxD + "' value='" + (filter.to || "") + "'></label>" +
      "<span class='presets'>" +
        "<button type='button' class='preset' data-range='7'>Last 7d</button>" +
        "<button type='button' class='preset' data-range='30'>Last 30d</button>" +
        "<button type='button' class='preset' data-range='all'>All</button>" +
      "</span>" +
      "<button id='f-clear' class='toggle'>Clear</button>" +
      (minD ? "<div class='frange'>Data available: " + fmtRange(minD, maxD) + "</div>" : "");

    var projEl = el("f-proj"), fromEl = el("f-from"), toEl = el("f-to");
    var chips = [].slice.call(document.querySelectorAll("#filterbar .preset"));
    function clamp(v) { if (!v) return null; if (minD && v < minD) v = minD; if (maxD && v > maxD) v = maxD; return v; }
    function clearActive() { chips.forEach(function (c) { c.classList.remove("active"); }); }
    function syncInputs() { fromEl.value = filter.from || ""; toEl.value = filter.to || ""; }

    // clicking anywhere in the field opens the native calendar (not just the tiny icon)
    [fromEl, toEl].forEach(function (inp) {
      inp.addEventListener("click", function () { if (inp.showPicker) { try { inp.showPicker(); } catch (e) {} } }); });
    projEl.addEventListener("change", function (e) { filter.project = e.target.value || null; renderActive(); });
    fromEl.addEventListener("change", function (e) { filter.from = clamp(e.target.value); syncInputs(); clearActive(); renderActive(); });
    toEl.addEventListener("change", function (e) { filter.to = clamp(e.target.value); syncInputs(); clearActive(); renderActive(); });
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        var r = c.getAttribute("data-range");
        if (r === "all") { filter.from = null; filter.to = null; }  // all time = unbounded (incl. undated); same data as Clear, minus the repo reset
        else { filter.to = maxD || null; filter.from = maxD ? clamp(addDays(maxD, -(+r - 1))) : null; }
        syncInputs(); clearActive(); c.classList.add("active"); renderActive(); }); });
    el("f-clear").addEventListener("click", function () {
      filter = { project: null, from: null, to: null };
      projEl.value = ""; syncInputs(); clearActive(); renderActive(); });
  }

  // theme toggle + scroll thread (from 001)
  var root = document.documentElement;
  try { if (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches) root.setAttribute("data-theme", "light"); } catch (e) {}
  var tbtn = el("themeToggle");
  if (tbtn) tbtn.addEventListener("click", function () {
    var t = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    root.setAttribute("data-theme", t); tbtn.textContent = t === "light" ? "◐ dark" : "◑ light"; });
  var fill = el("scrollfill");
  if (fill) { var upd = function () { var h = document.documentElement, m = h.scrollHeight - h.clientHeight;
    fill.style.width = (m > 0 ? h.scrollTop / m * 100 : 0) + "%"; };
    document.addEventListener("scroll", function () { requestAnimationFrame(upd); }, { passive: true });
    window.addEventListener("resize", upd); upd(); }

  // chart hover tooltip: one shared element, delegated so it survives view re-renders
  var tip = document.createElement("div"); tip.className = "thl-tip"; document.body.appendChild(tip);
  function moveTip(x, y) {
    var r = tip.getBoundingClientRect();
    var nx = x + 14, ny = y + 16;
    if (nx + r.width > window.innerWidth - 8) nx = x - r.width - 14;
    if (ny + r.height > window.innerHeight - 8) ny = y - r.height - 16;
    tip.style.left = Math.max(8, nx) + "px"; tip.style.top = Math.max(8, ny) + "px";
  }
  document.addEventListener("mouseover", function (e) {
    var t = e.target.closest ? e.target.closest("[data-tip]") : null;
    if (!t) return;
    tip.textContent = ""; var b = document.createElement("b"); b.textContent = t.getAttribute("data-tip"); tip.appendChild(b);
    var s = t.getAttribute("data-sub");
    if (s) { var sp = document.createElement("span"); sp.className = "s"; sp.textContent = s; tip.appendChild(sp); }
    tip.classList.add("on"); moveTip(e.clientX, e.clientY);
  });
  document.addEventListener("mousemove", function (e) { if (tip.classList.contains("on")) moveTip(e.clientX, e.clientY); });
  document.addEventListener("mouseout", function (e) {
    if (e.target.closest && e.target.closest("[data-tip]")) tip.classList.remove("on"); });

  buildFilterBar();
  setupLensSwitch();
  render();
})();
