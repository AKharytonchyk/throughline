# Feature Specification: Burn-Down / Biggest Levers

**Feature Branch**: `005-burn-down-levers`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Burn-down / biggest-levers panel — a ranked, dollarized action list that unifies signals throughline already computes (mounted-but-unused MCP tools and their resident/schema cost, collapsible tool chains, and session-length re-billing) into one view: 'your biggest levers to cut daily context burn,' each with a projected per-day tokens (and opt-in dollars) saved, sorted by impact. It bridges the space lens with the flow lens. Advisory only. Local, stdlib-only, single dashboard. Every projected saving labeled an estimate with its method."

## Overview

Throughline today shows the *pieces* of context waste in separate places: the breakdown lists mounted-but-never-called MCP tools (unmount candidates), the sequential-patterns view ranks collapsible tool chains, and the token lens shows resident context being re-billed as `cache_read` on every turn. What it does **not** do is answer the one question a power user staring at a heavy daily bill actually asks: **"What are my biggest levers to cut this, ranked, and how much would each save per day?"**

This feature adds a single **burn-down** view: a ranked, method-labeled list of reduction **levers**, each synthesized from a signal Throughline already computes, each carrying a **projected per-day token saving** (and, opt-in, a projected dollar saving), sorted by impact — plus an aggregate "if you act on these" figure.

The view's job is to **bridge the two existing lenses**. The occupancy (space) lens knows what is *resident* in the window (schemas, unused tools) in characters; the token (flow) lens knows that resident content is re-sent as `cache_read` **every turn**. On observed real data the daily bill is dominated by cache-read (~96.5%), so the bill is driven far more by `resident_size × turns` than by any one new request. This view converts the space signals into the flow unit — tokens re-billed per day — so a lever's projected saving maps to what actually moves the bill.

It is **advisory only**. It names what to unmount, collapse, or shorten; it never performs the change, never installs or enforces spending caps, and never alters Claude Code behavior (constitution Principles III and IV). Every projected saving is an **estimate labeled with its method** (Principle V); the underlying resident and chain figures are already estimates and that labeling is inherited, not laundered into a false exact.

This feature needs **no new collection** — it reuses feature 001's breakdown and chain signals, feature 002's repo/time-range filters and intervention markers, and feature 003's per-turn token counts and opt-in `prices.json`. Sub-agent-specific levers, cap enforcement, and any MCP proxying are out of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ranked levers by projected daily token saving (Priority: P1)

As a power user burning a heavy daily context budget, I open the burn-down view and see a **ranked list of levers** — each one a concrete reduction opportunity (unmount these unused tools; collapse this recurring chain; shorten sessions that run long) — with a **projected per-day token saving**, sorted largest-first, so I know exactly where to start and what it is worth.

**Why this priority**: This is the core of the feature and the minimum viable increment. It needs no new collection — the underlying signals already exist — and it turns three scattered views into one prioritized, actionable answer to "where do I cut first."

**Independent Test**: With existing collected sessions, open the view and confirm a list of levers appears, each with a projected per-day token saving, sorted descending by that saving, each carrying a plain-language description of the change and an estimate label with its method.

**Acceptance Scenarios**:

1. **Given** collected sessions containing at least one unused mounted tool, one recurring collapsible chain, and long sessions, **When** the user opens the burn-down view, **Then** a ranked list of levers is shown, each with a projected per-day token saving, ordered from largest to smallest saving.
2. **Given** any lever in the list, **When** the user inspects it, **Then** it shows a plain-language description of the recommended change and is labeled an **estimate** stating the method used to derive its saving.
3. **Given** the list is shown, **When** the user reads the top entry, **Then** it is the lever with the largest projected per-day token saving.

---

### User Story 2 - Opt-in dollar savings (Priority: P2)

As a user who has configured a price list, I want each lever (and the aggregate) to also show a **projected per-day dollar saving**, clearly labeled an estimate stating its price basis, so I can put an approximate money figure on each cut — while never seeing a guessed dollar amount when I have configured no prices.

**Why this priority**: Dollars are the most motivating framing for the "caps are coming" audience, but they are strictly optional and must never be presented as authoritative. It reuses feature 003's opt-in `prices.json`, so it is a thin layer on top of US1.

**Independent Test**: With a per-model price list configured, confirm each lever shows a projected `$/day` saving labeled an estimate with its price basis; with no price list, confirm no dollar figure appears anywhere in the view and token savings still show.

**Acceptance Scenarios**:

1. **Given** a configured per-model price list, **When** the user views the burn-down list, **Then** each lever and the aggregate show a projected per-day dollar saving labeled an estimate stating the price basis.
2. **Given** no price list configured, **When** the user views the burn-down list, **Then** no dollar figure appears anywhere and each lever still shows its projected token saving.
3. **Given** a model present in the data has no configured price, **When** dollar savings are shown, **Then** that model's contribution to the dollar figure is omitted and labeled unpriced — never guessed.

---

### User Story 3 - Scope-aware recomputation (Priority: P3)

As a user narrowing my analysis, I want the levers and their per-day savings to **honor the existing repo and time-range filters**, recomputing the per-day rates for the selected window, so the recommendations reflect the project and period I care about.

**Why this priority**: Reuses feature 002's filters and makes the view trustworthy across projects and time windows, but it refines US1 rather than being independently essential.

**Independent Test**: With sessions spanning several days and multiple repos, change the repo and time-range filter and confirm the levers list and its per-day savings recompute for the filtered scope.

**Acceptance Scenarios**:

1. **Given** sessions across multiple repos, **When** the user filters to one repo, **Then** the levers and per-day savings reflect only that repo's data.
2. **Given** a selected time range, **When** the view computes per-day savings, **Then** the per-day rate is derived from the active days within that range, and the basis is stated.

---

### User Story 4 - Aggregate "if you act on these" figure (Priority: P4)

As a user, I want a single headline **aggregate projected daily saving** for acting on the shown levers, with an explicit caveat that per-lever savings can overlap and are not guaranteed to sum, so I get one motivating number without being misled into thinking the savings are strictly additive.

**Why this priority**: A single number is the strongest motivator, but it is a summary of US1/US2 and must be presented honestly about overlap, so it is lowest priority and depends on the others.

**Independent Test**: Confirm an aggregate projected daily saving is shown above/with the list, accompanied by an explicit statement that per-lever savings may overlap and are not additively guaranteed.

**Acceptance Scenarios**:

1. **Given** a list of levers, **When** the user views the aggregate, **Then** a single projected per-day saving (tokens, and dollars if priced) is shown with an explicit overlap/non-additive caveat.

---

### Edge Cases

- **No significant levers** (no unused tools, no recurring collapsible chains, no long sessions): the view states plainly that no significant levers were found — it MUST NOT fabricate opportunities or show zero-value levers as if actionable.
- **Overlapping levers** (e.g., a collapsible chain that also involves a rarely-used tool): savings are reported **per lever** and the aggregate carries a non-additive caveat; the tool MUST NOT claim the per-lever savings sum exactly.
- **Estimate provenance**: the resident/schema figure a lever is built on is itself a labeled estimate (feature 001); the lever's saving inherits and states that, and MUST NOT be presented as exact.
- **Model has no configured price**: its dollar contribution is omitted and labeled unpriced; token savings are unaffected.
- **Very short filtered window** (e.g., a single active day): the per-day rate is still derived but the small-sample basis is stated so the user can calibrate trust.
- **Sessions with missing usage fields**: excluded from the per-day token-rate basis and flagged, rather than silently distorting the rate.
- **Very large savings** (millions to billions of tokens/day): figures remain readable via human-scaled units (k / M / B).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST present a **ranked list of reduction levers** for the filtered scope, sorted by **projected per-day token saving**, largest first.
- **FR-002**: Levers MUST be derived **only from signals Throughline already computes** — mounted-but-unused MCP tools (unmount candidates) and their resident/schema cost, collapsible recurring tool chains, and session-length re-billing — with **no new data collection**.
- **FR-003**: Each lever MUST show a **projected per-day token saving**, **labeled an estimate**, and MUST state the **method** used to derive it.
- **FR-004**: Each lever MUST carry a **plain-language advisory description** of the recommended change (what to unmount, which chain to collapse, which sessions run long). The tool MUST NOT perform or enforce the change.
- **FR-005**: Projected savings MUST be expressed in the **flow unit (tokens re-billed per day)**, bridging the space signal (resident characters) to flow via a **stated conversion method** (resident content re-sent as `cache_read` per turn × turns per day).
- **FR-006**: The tool MUST present an **optional projected per-day dollar saving** per lever and in aggregate, derived from the existing user-configurable **`prices.json`**; it MUST be opt-in and empty by default (tokens only), labeled an estimate stating its price basis, and any model with no configured price MUST have its dollar contribution omitted and labeled — never guessed.
- **FR-007**: The tool MUST present an **aggregate projected daily saving** across the shown levers and MUST state explicitly that per-lever savings **may overlap and are not guaranteed additive**.
- **FR-008**: The levers and their per-day savings MUST honor the existing **repo and time-range filters**, recomputing the per-day rate from the **active days within the filtered window**, and MUST state that basis.
- **FR-009**: When **no significant levers** are found, the tool MUST say so explicitly rather than fabricate opportunities.
- **FR-010**: The tool MUST NOT install, enforce, or recommend installing **spending caps**, and MUST NOT change Claude Code behavior in any way (constitution Principles III and IV) — the view is advisory only.
- **FR-011**: All burn-down analysis MUST run **locally with no network access**, and every output MUST remain within the tool's working directory (Principles I and II).
- **FR-012**: The tool MUST treat all Claude Code transcripts as **read-only** inputs (Principle III).
- **FR-013**: The burn-down view MUST be delivered through the tool's existing **single self-contained dashboard** (single command, no new long-running process, no network or external asset).
- **FR-014**: **Every** displayed figure MUST carry an explicit **exact-or-estimate label**; all projected savings are estimates and MUST state their method (Principle V). No unlabeled approximation may appear.

*Out of scope for this feature:* sub-agent-specific levers and the main-vs-sub-agent split (its own later feature), enforcing or installing spending caps, proxying or intercepting MCP traffic, and implementing the recommended tool consolidations.

### Key Entities *(include if feature involves data)*

- **Lever**: one reduction opportunity — its **type** (unused-tool / collapsible-chain / session-length), the underlying signal it is derived from, its **projected per-day token saving** (estimate + stated method), an **optional projected per-day dollar saving**, and a **plain-language advisory action**.
- **Burn-down summary**: the ranked set of levers for the filtered scope, plus the **aggregate projected daily saving** and its non-additive/overlap caveat.
- **Per-day rate basis**: the turns-per-day (and/or sessions-per-day) derived from the **active days in the filtered window**, used to convert resident/per-turn cost into a daily saving; carries a small-sample flag when the window is short.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any filtered scope, the user can read a **ranked list of levers**, each with a projected per-day token saving, sorted descending — and can identify the single biggest lever at a glance.
- **SC-002**: **Every** projected saving carries an explicit **estimate label and stated method**; no unlabeled approximation appears anywhere in the view.
- **SC-003**: With a price list configured, each lever and the aggregate show a projected **per-day dollar saving** labeled an estimate; with **no** price list configured, **no** dollar figure appears anywhere while token savings still show.
- **SC-004**: The ordering is correct and verifiable — the top lever is the one with the **largest projected per-day token saving**.
- **SC-005**: When no significant levers exist, the view **states that explicitly** and shows no fabricated or zero-value opportunities.
- **SC-006**: The aggregate projected daily saving is shown **with an explicit overlap/non-additive caveat**, so the user is never misled that per-lever savings sum exactly.

## Assumptions

- **No new collection**: every lever is synthesized from data Throughline already collects and already analyzes (breakdown/unmount candidates, chains, per-turn token usage). This feature adds synthesis and presentation, not new inputs.
- **Space→flow conversion**: a resident item's per-day token cost is estimated as its resident token size re-sent as `cache_read` per turn × the turns-per-day observed in the filtered window. This is a **labeled estimate**; the method is stated in the output.
- **Per-day basis**: per-day rates are averaged over **active days** (days with sessions) in the filtered window, not calendar days, so idle days do not deflate the rate; the basis is stated, with a small-sample flag for very short windows.
- **Session-length lever threshold**: "long" sessions are identified by a threshold (reused/derived from existing config where available); the advisory is to clear/compact sooner. The tool advises only — it never triggers compaction or otherwise acts on the session.
- **Overlap is real and disclosed**: levers can address overlapping token spend (e.g., a chain involving a rarely-used tool), so per-lever savings are not treated as additive and the aggregate says so.
- **Reuse of prior features**: repo/time-range filters and intervention markers come from feature 002; token counts and the opt-in `prices.json` come from feature 003; resident and chain estimates come from feature 001 — this feature does not reintroduce them.
- **Additive, not a replacement**: the burn-down view is a new panel reachable from the existing dashboard; it does not change, replace, or supersede the occupancy or token lenses.
- **Constitution compliance**: implementation stays local-only, read-only toward Claude Code, standard-library-only, advisory (no behavior change, no cap enforcement), and delivered as the existing single self-contained dashboard with no network or external assets.
