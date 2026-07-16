# Feature Specification: Token Usage & Cost

**Feature Branch**: `003-token-usage-cost`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Token usage & cost — a second analysis lens, separate from the existing context-window (occupancy) view."

## Overview

Throughline today answers **"what occupies my context window"** in characters — a *space / occupancy* measure that is attributable per tool. It does not answer **"what did this work actually cost in tokens"** — a *flow / cumulative* measure. These are different concerns, in different units, at different granularity, and this feature adds the second concern as a distinct lens **alongside** the existing one — never merged into it.

The concern is pressing for agentic workflows. Observed on real local data: total token flow across sessions was billions of tokens while context windows were only a few million characters, and the large majority of all tokens was **cache-read** — the context window re-billed on every turn. A big resident footprint (schemas, system prompt) is cheap in space (counted once) but expensive in flow (re-sent every turn), which the occupancy lens structurally under-weights.

Agents and sub-agents amplify this: each sub-agent runs as its own session that re-pays its whole context tax. **Deep sub-agent token attribution — the main-vs-sub-agent split and the amplification factor — is split into feature 004**, which also owns the research to gather and link the separate sub-agent transcripts. This feature (003) establishes the token lens on the sessions Throughline already collects; the token cost of *launching* sub-agents already appears here as ordinary main-thread turns (the dispatch prompt plus the returned result), so 003 still shows what agent-launching costs the main window.

## Clarifications

### Session 2026-07-16

- Q: Should sub-agent token attribution (main-vs-sub-agent split, amplification, per-type) be part of this feature, or split out? → A: Split into a follow-on **feature 004**; 003 covers only the stories that need no new collection. Feature 004 also owns the shared "gather & link sub-agent transcripts" research.
- Q: Include the optional dollar-cost estimate in this feature? → A: Yes — include now, **opt-in and empty by default** (no dollar figure unless the user configures a price list).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Token flow by type (Priority: P1)

As a developer, I open the token-usage lens and see, for the filtered scope, my exact token spend broken down by type — **input**, **output**, **cache-write** (first-time context), and **cache-read** (re-billed context) — per session and in total, so I can see where my tokens actually go and how much of my spend is context being re-processed rather than new work.

**Why this priority**: This is the core of the new concern and the minimum viable increment. It needs no new data collection — the counts already exist in the sessions Throughline collects today — and it immediately reveals the dominant, previously-invisible cost (cache-read re-billing).

**Independent Test**: With existing collected sessions, open the lens and confirm the four token-type figures are shown per session and in aggregate, sum correctly, and are labeled exact. Delivers value on its own.

**Acceptance Scenarios**:

1. **Given** collected sessions with recorded usage, **When** the user opens the token-usage lens, **Then** total tokens are shown split into input / output / cache-write / cache-read, and the cache-read share of the total is stated.
2. **Given** a single session, **When** the user inspects its token figures, **Then** the four type totals reconcile exactly to that session's recorded per-turn usage.
3. **Given** the user is on the token lens, **When** they switch to the context-window (chars) lens and back, **Then** the two are presented separately and never share units or a merged total.

---

### User Story 2 - Re-billing growth over a session (Priority: P2)

As a developer, I want to see how cumulative token usage grows across a session's turns, so I can understand that context is re-billed every turn and that long sessions and large resident footprints cost proportionally more the longer the session runs.

**Why this priority**: It turns the cache-read number from US1 into an intuition about *why* — the growth curve — and needs no new collection. Valuable but secondary to simply seeing the totals.

**Independent Test**: For a chosen session, confirm a cumulative-tokens-over-turns progression is shown and that it increases monotonically with turns.

**Acceptance Scenarios**:

1. **Given** a session with many turns, **When** the user views its growth curve, **Then** cumulative tokens are shown increasing across turns.
2. **Given** two sessions of very different length, **When** compared, **Then** the longer session's re-billing (cumulative cache-read) is visibly larger.

---

### User Story 3 - Token spend over time (Priority: P3)

As a developer, I want to see token spend over time (by day and/or week) for the filtered scope, with my intervention markers, so I can tell whether a change I made (switching to plan mode, using fewer sub-agents, adding limits to reads) actually reduced my token cost.

**Why this priority**: Complements feature 002's per-call character trend with a token-cost trend. Needs no new collection, but is a refinement on top of the core totals.

**Independent Test**: With sessions spanning several days, confirm a per-day (or per-week) token trend is shown, honors the repo/time-range filters, and displays intervention markers.

**Acceptance Scenarios**:

1. **Given** sessions across multiple days, **When** the user views the token trend, **Then** token spend is plotted per time bucket for the filtered scope.
2. **Given** a recorded intervention date, **When** the user views the trend, **Then** the intervention appears as a marker and the user can compare spend before and after it.

---

### User Story 4 - Optional dollar-cost estimate (Priority: P4)

As a developer, I want an optional, clearly-labeled dollar estimate of my token spend, computed from a price list I control, so I can put an approximate cost figure on a run — while understanding it is an estimate, not a bill.

**Why this priority**: Useful framing but strictly optional; prices change and are user/plan specific, so it is the lowest priority and must never be presented as authoritative. It is opt-in and shows nothing until the user configures prices.

**Independent Test**: With a per-model price list configured, confirm a dollar estimate is shown, labeled as an estimate with its method and prices; with no prices configured, confirm no dollar figure is shown (never guessed).

**Acceptance Scenarios**:

1. **Given** a configured per-model price list, **When** the user enables the cost estimate, **Then** an estimated dollar figure is shown, labeled as an estimate stating the price basis.
2. **Given** no price configured for a model present in the data, **When** the cost estimate is shown, **Then** that model's cost is omitted and labeled as unpriced — not guessed.
3. **Given** no price list configured at all, **When** the user views the token lens, **Then** no dollar figure appears anywhere.

---

### Edge Cases

- **Turns or sessions with missing usage fields** (e.g., older transcripts): missing fields count as zero; a session with no usage at all is flagged rather than silently contributing nothing.
- **Multiple models within one session**: tokens attributed per model; type totals still reconcile to recorded usage.
- **No caching present** (cache-read = 0, e.g. early turns): the breakdown still renders correctly with a zero cache-read share.
- **Very large counts** (millions to billions of tokens): figures remain readable via human-scaled units (k / M / B).
- **A per-tool token figure is requested**: it is impossible to attribute exactly (usage is per turn, not per tool); any per-tool token number shown is labeled an estimate with its method, or omitted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST present token usage as a **distinct lens, separate from the context-window (characters) views**, and MUST let the user switch between the two lenses. The two MUST NOT be merged or share a combined total or units.
- **FR-002**: The tool MUST report token counts broken down into four types: **input**, **output**, **cache-write** (first-time cached context), and **cache-read** (re-billed context), sourced from each turn's recorded usage.
- **FR-003**: The tool MUST report token figures **per session** and **aggregated** across the filtered scope.
- **FR-004**: Token counts taken from recorded usage MUST be labeled **exact** (they are not estimates).
- **FR-005**: The tool MUST surface the **cache-read share** of total tokens, so the user can see how much of their spend is context re-processing versus new work.
- **FR-006**: The tool MUST show how **cumulative token usage grows across a session's turns**, making per-turn re-billing visible.
- **FR-007**: The tool MUST show **token usage over time** (per day and/or week) for the filtered scope.
- **FR-008**: The token-usage views MUST honor the existing **repo and time-range filters** and display the existing **intervention markers**.
- **FR-009**: The tool MUST attribute token usage **by model** (the model identifier recorded in the data), since pricing and behavior differ by model.
- **FR-010**: The tool MUST present an **optional dollar-cost estimate**; it MUST be opt-in, empty by default, derived from a **user-configurable per-model price list**, and **labeled as an estimate** stating its method and price basis. It MUST NOT be presented as exact, and a model with no configured price MUST have its cost omitted and labeled, never guessed.
- **FR-011**: The tool MUST NOT present any **per-tool** token figure as exact (usage is recorded per turn, not per tool). Any per-tool token approximation, if shown at all, MUST be labeled an estimate with its stated method.
- **FR-012**: All token-usage analysis MUST run **locally with no network access**, and every output MUST remain within the tool's working directory.
- **FR-013**: The tool MUST treat all Claude Code transcripts as **read-only** inputs, copying before processing as needed.
- **FR-014**: The token-usage lens MUST be available through the tool's existing **single-command, single self-contained artifact** (no new long-running process, no network or external asset).

*Out of scope for this feature (moved to feature 004):* distinguishing main-session vs sub-agent tokens, the sub-agent amplification factor, per-sub-agent-type attribution, and any collection/linking of the separate sub-agent transcripts.

### Key Entities *(include if feature involves data)*

- **Turn usage**: the token counts recorded for one assistant turn — input, output, cache-write, cache-read — plus the model identifier and timestamp; belongs to a session.
- **Session token summary**: per-session totals by token type and by model, and the number of turns.
- **Model**: an identifier appearing in the data; optionally carries user-configured unit prices used only for the cost estimate.
- **Price list (configuration)**: user-editable per-model unit prices (by token type) and an effective date, used solely to compute the optional labeled dollar estimate; empty by default.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any filtered scope, the user can read the **percentage of total tokens spent on cache-read** versus input/output/cache-write, and the four shares sum to 100%.
- **SC-002**: For every session, the four token-type totals **reconcile exactly** to that session's recorded per-turn usage (a golden check passes with zero discrepancy).
- **SC-003**: The user can compare token spend between two time periods (e.g., the weeks before and after an intervention) and read the **percentage change**.
- **SC-004**: **Every** displayed token or cost figure carries an explicit **exact-or-estimate label**; no unlabeled approximation appears anywhere in the output.
- **SC-005**: The token lens and the context-window lens are **never shown merged or in the same units**, and the user can move between them from the dashboard.

## Assumptions

- Token flow (all four types) requires **no new collection** — the counts already exist in the per-turn usage of sessions Throughline collects today; only the three currently-unused types (input, output, cache-read) need to be surfaced alongside the one already read (cache-write).
- **Sub-agent token attribution is out of scope** (feature 004): the main-vs-sub-agent split, amplification factor, and per-sub-agent-type breakdown, plus the research to locate and link the separate sub-agent transcripts. In 003 the token cost of launching sub-agents still appears within the main session's totals as ordinary turns.
- Raw token-flow counts are **unweighted actual token counts** (cache-read is counted at its true token count). Relative billing weights between token types apply **only** to the optional dollar-cost estimate, via the price list.
- This feature **reuses feature 002's** repo/time-range filters and intervention markers rather than introducing new filtering.
- The dollar-cost **price list ships empty (or as a clearly-marked example)** and is user-editable; with no prices set, no dollar figure is shown.
- This lens is **additive**: it does not change, replace, or supersede the existing context-window (chars) views (features 001 and 002); it is a parallel view reachable by a lens switch.
- Consistent with the constitution, the implementation stays **local-only, read-only toward Claude Code, standard-library-only, and delivered as the existing single self-contained dashboard** with no network or external assets.
