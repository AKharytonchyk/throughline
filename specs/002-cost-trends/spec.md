# Feature Specification: Cost Over Time — Experiment Tracker & Filters

**Feature Branch**: `002-cost-trends`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "I change how I work with Claude Code — add `offset`/`limit` to Read, switch from auto mode back to plan mode, etc. — and I want to see whether those changes actually reduced my context cost. Filter results by repo and time range, and see cost over time (especially per-tool cost per call, and cost by working mode)."

**Builds on**: Feature 001 (Throughline — Context Budget Analyzer). This increment adds a
time dimension and filtering to the existing local dashboard; it reuses the same collected
data and the same constitution constraints (local-only, read-only, estimates labeled,
self-contained, simple to run).

## Clarifications

### Session 2026-07-15

- Q: How should filtering (repo + time range) work? → A: Interactive/client-side — filters apply instantly in the open dashboard with no re-run. The tool embeds pre-aggregated per-session (and per-chain-occurrence) data at generation time; the browser re-aggregates the matching subset rather than re-running the Python analysis, so the analysis engine is neither duplicated nor re-executed per filter.
- Q: How should the time-trend buckets be sized? → A: Auto by span — daily for short histories (≤ ~2 weeks), weekly for longer.
- Q: For the plan-vs-auto mode comparison, which cost metric per mode? → A: Both — average context per session AND average content per call.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Did my per-call optimization work? (Priority: P1)

The developer changed how a tool is used — e.g. started passing `offset`/`limit` to `Read`
so it returns a slice instead of a whole file — and wants to see whether that shrank the
tool's context cost. They pick a tool and see its **average content returned per call** over
time, so a before/after drop is visible around the date they changed their habit.

**Why this priority**: This is the headline value of the increment and the reason it exists
— measuring the effect of the developer's own optimizations. On its own it answers "did my
change help?" and is a complete, viable slice.

**Independent Test**: With collected sessions spanning several weeks, open the dashboard,
pick a frequently-used tool (e.g. `Read`), and confirm a trend of **average size per call**
over time buckets is shown, distinct from a raw-total trend, such that a period where the
tool returned smaller results per call is visibly lower.

**Acceptance Scenarios**:

1. **Given** collected sessions across multiple dates, **When** the user selects a tool,
   **Then** the dashboard shows that tool's average content-returned-per-call across time
   buckets (e.g. by week), plus its call count per bucket.
2. **Given** a tool whose per-call size dropped after a date, **When** the user views its
   trend, **Then** the later buckets are visibly lower even if the call count rose (i.e.
   the metric is per-call average, not a raw sum that frequency could mask).
3. **Given** a tool used in only one time bucket, **When** its trend is shown, **Then** it
   renders as a single point without error.

---

### User Story 2 - Filter by repo and time range (Priority: P2)

The developer wants to narrow the whole analysis to a single project (repo) and/or a date
range, to isolate the sessions around a change they made.

**Why this priority**: Filtering is what makes the trend and the existing views usable for
an experiment — you compare like with like. It supports US1 and the existing views.

**Independent Test**: With sessions from multiple projects and dates, apply a repo filter
and a date-range filter and confirm every view (breakdown, heatmap, chains, trends) reflects
only the matching subset, and clearing the filter restores the full view.

**Acceptance Scenarios**:

1. **Given** sessions from several projects, **When** the user filters to one project,
   **Then** all views recompute over only that project's sessions.
2. **Given** sessions across a date span, **When** the user sets a from/to range, **Then**
   all views reflect only sessions within it.
3. **Given** an active filter, **When** the user clears it, **Then** the full dataset view
   returns.
4. **Given** a filter that matches no sessions, **When** applied, **Then** the dashboard
   states the empty result explicitly rather than showing stale or blank charts.

---

### User Story 3 - Is plan mode cheaper than auto? (Priority: P3)

The developer switches between Claude Code working modes (plan / auto / acceptEdits) and
wants to see whether a given mode costs less context, to justify their habit.

**Why this priority**: Directly answers the "I switched back to plan mode — did it help?"
experiment, using a signal already in the data (the recorded working mode). Valuable but
secondary to the general per-tool trend.

**Independent Test**: With sessions that used more than one working mode, open the dashboard
and confirm context cost is segmented by mode (plan / auto / acceptEdits / default), showing
per-mode averages so the modes can be compared.

**Acceptance Scenarios**:

1. **Given** sessions spanning multiple working modes, **When** the user opens the mode
   view, **Then** context cost is broken down by mode with a per-mode average (e.g. average
   context per session, or per call) so modes are comparable.
2. **Given** a session where the mode changed partway through, **When** costs are attributed,
   **Then** each tool call is counted under the mode that was active at that call's time.
3. **Given** only one mode is present in the data, **When** the mode view is shown, **Then**
   it displays that single mode without implying a comparison.

---

### User Story 4 - Mark when I made a change (Priority: P4)

The developer records a dated note — "added `offset`/`limit` to Read" — so the trends draw a
marker at that date, making before/after obvious at a glance.

**Why this priority**: A convenience that sharpens US1/US3; the trends are still readable
without it. Sequenced last.

**Independent Test**: Add a dated intervention note, open a trend that spans that date, and
confirm a labeled marker appears at the right position; with no notes, trends render
unchanged.

**Acceptance Scenarios**:

1. **Given** a recorded intervention with a date and label, **When** a trend spanning that
   date is shown, **Then** a labeled marker appears at that date.
2. **Given** no interventions recorded, **When** trends are shown, **Then** they render
   normally with no markers.

---

### Edge Cases

- **Sparse history**: a tool or mode present in only one bucket renders as a single point,
  not an error.
- **Gaps**: time buckets with no activity are shown as gaps/zero, not omitted in a way that
  distorts the timeline.
- **Missing timestamp**: a record without a usable timestamp falls back to the session's
  file modification time; if neither exists it is excluded and counted in an explicit
  "undated" note rather than dropped silently.
- **Mode boundaries**: calls before any recorded mode are attributed to "unknown" mode
  rather than guessed.
- **Session spanning modes**: its calls split across the modes that were active (FR-009);
  for the per-session-by-mode average it counts toward each mode it used (labeled), so
  per-mode session counts can overlap and need not sum to the session total.
- **Empty filter result**: an explicit empty state (see US2 scenario 4).
- **Single-session / single-day data**: trends degrade gracefully to whatever range exists.
- **Timezone**: bucketing uses the timestamps as recorded; the basis (e.g. UTC) is stated so
  bucket boundaries are unambiguous.

## Requirements *(mandatory)*

### Functional Requirements

**Time trends (User Story 1)**

- **FR-001**: The dashboard MUST present context cost over time, bucketed into time periods
  whose size is auto-selected by the data's span (daily for short histories ≤ ~2 weeks,
  weekly for longer), using the timestamps already captured with each tool call.
- **FR-002**: For a user-selected tool, the dashboard MUST show its **average content
  returned per call** per time bucket, alongside its call count per bucket, so a change in
  per-call size is visible independently of a change in call frequency.
- **FR-003**: The trend MUST distinguish per-call average from raw totals; a raw-total view
  MAY also be offered but MUST NOT be the only time metric (a frequency change must not be
  able to hide a per-call size change).
- **FR-004**: The dashboard MUST also show an overall context-cost-over-time trend (e.g. per
  session or per bucket) so the developer can see aggregate movement, not only per-tool.

**Filters (User Story 2)**

- **FR-005**: The user MUST be able to filter the analysis by repo (project) and by a time
  range (from/to), individually or together.
- **FR-006**: Applying or clearing a filter MUST update all views (context breakdown,
  heatmap, chains, and trends) **instantly in the open dashboard — client-side, without
  re-running or re-generating the tool** — to reflect exactly the matching subset of
  sessions.
- **FR-007**: When a filter matches no sessions, the dashboard MUST state the empty result
  explicitly rather than render stale or blank views (FR-010 of feature 001).

**Cost by working mode (User Story 3)**

- **FR-008**: The dashboard MUST segment context cost by Claude Code working mode
  (plan / auto / acceptEdits / default / unknown), using the working-mode signal recorded in
  the sessions.
- **FR-009**: Each tool call MUST be attributed to the working mode that was active at the
  time of that call (the most recent mode change at or before the call).
- **FR-010**: The mode view MUST present per-mode averages **both** per session and per
  call so modes can be compared on equal terms, not just raw totals. A session that used
  more than one mode counts toward **each** mode it used, so per-mode session figures may
  overlap and are not a partition of sessions; the view MUST label this so it is not
  misread.

**Intervention markers (User Story 4)**

- **FR-011**: The user MUST be able to record dated intervention notes (a date + short
  label), stored within the tool's own working directory.
- **FR-012**: Trends spanning a recorded intervention's date MUST display a labeled marker at
  that date; with no interventions, trends render unchanged.

**Cross-cutting (inherited constraints)**

- **FR-013**: This increment MUST use the already-collected session data and MUST NOT require
  a new collection step or change collection behavior.
- **FR-014**: All new figures MUST follow the correctness rule: exact measurements presented
  as exact, approximations labeled as estimates with method stated; the tool MUST NOT present
  a proxy as ground truth.
- **FR-015**: The feature MUST remain fully local — no network access — and the dashboard MUST
  remain a single self-contained artifact viewable without a server.
- **FR-016**: The feature MUST NOT introduce a long-running daemon; it operates within the
  existing one-command view.

### Key Entities *(include if data involved)*

- **Time Bucket**: a period (day or week) with aggregated metrics for the sessions/calls that
  fall in it.
- **Trend Point**: a metric at a bucket for a scope — `{bucket, scope (overall|tool),
  tool_key?, avg_per_call, total_size, call_count}`.
- **Mode Segment**: context cost attributed to a working mode — `{mode, total_size,
  call_count, avg_per_call, sessions}`.
- **Filter**: the active selection — `{project?, from?, to?}` — applied across all views.
- **Intervention**: a dated note — `{date, label}` — stored in the working directory.
- **(Reused from 001)**: Session, Tool Call (now used with its timestamp), Context Bucket,
  Tool, Chain.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a tool the developer optimized, they can open the dashboard and, within 2
  minutes, read that tool's **average size per call over time** and identify whether it
  dropped after the date they changed their habit. *(headline)*
- **SC-002**: Applying a repo filter and/or a time range updates every view to the matching
  subset; clearing it restores the full view; a no-match filter shows an explicit empty
  state.
- **SC-003**: Context cost is shown segmented by working mode with per-mode averages **both
  per session and per call**, so the developer can state which mode cost less context over
  the analyzed data.
- **SC-004**: The per-tool time trend uses a per-call average metric, verified by a case
  where call count rises while average-per-call falls and the trend shows the fall.
- **SC-005**: Every new figure is either exact (labeled exact) or a labeled estimate with a
  stated method; no approximation is presented as exact.
- **SC-006**: The feature makes zero network connections and needs no new collection run;
  the dashboard remains a single self-contained artifact opened without a server.
- **SC-007**: Applying/clearing a filter or switching the trend selection updates the
  dashboard **instantly, client-side, with no re-run or re-generation**, fast enough for
  fluid exploration.

## Assumptions

- The increment operates on data already gathered by feature 001's collection; no new capture
  is required (working mode, per-call timestamps, and project are already present in the
  collected sessions).
- Every tool call carries a usable timestamp (verified in the current data); the file
  modification time is a documented fallback for any record that lacks one.
- Working mode is taken from the mode signal recorded in the sessions, with values
  plan / auto / acceptEdits / default (and "unknown" before the first recorded mode).
- Time-bucket granularity is auto-selected by the data's span (resolved): daily for short
  spans (≤ ~2 weeks), weekly for longer.
- The primary trend metric is **average content per call** (size ÷ calls) per bucket, because
  a limit/offset optimization reduces size-per-call even when call count is unchanged or higher.
- Filtering is **interactive / client-side (resolved)**: the tool embeds pre-aggregated
  per-session (and per-chain-occurrence) data at generation time, and the browser
  re-aggregates the matching subset on the fly. The Python analysis (attribution, sizing,
  chain mining) runs **once** at generation, not per filter — so the engine is not
  duplicated in the browser and filtering stays instant. Chain *shapes* are mined once; the
  dashboard filters their pre-computed occurrences rather than re-mining.
- "Repo" means the Claude Code project a session ran in.
- Context amounts continue to be measured in the same size unit as feature 001 (characters),
  so trends and totals are comparable across increments.
- **Supersedes two feature-001 dashboard behaviors** (intentional, recorded here): (a) the
  breakdown shows resident cost as a single **aggregate** estimate bucket rather than 001's
  per-tool heuristic split — resident is ~1% of the window and was itself an estimate, and a
  per-tool split under arbitrary filters is disproportionate; mounted-but-unused is preserved
  via the mounted-tool key list. (b) 001's per-session drilldown (`report --session`, 001
  FR-030) is replaced by interactive **repo + time-range** filtering; selecting a single
  session by id is dropped as low value. These can be restored in a later increment if needed.

## Dependencies

- Depends on feature 001 (collection, parser, and the existing dashboard views) being present.
- Relies on the local Claude Code session data retaining per-call timestamps, a working-mode
  signal, and the project/repo association — all present in the data today.
