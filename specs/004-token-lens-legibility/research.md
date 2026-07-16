# Phase 0 Research: Token-Lens Legibility

All decisions are grounded in the existing feature-003 client (`report/app.js`) and shell
(`report/render.py`). No `NEEDS CLARIFICATION` remain. This feature adds no data and no analysis —
it explains, in plain language, the token terms the lens already shows.

*(Repository linking was considered and dropped — the top-bar repository filter already answers
"which repo," so per-session repository display is not added and session rows are left as they are.
No repo/placeholder/truncation work remains.)*

---

## D1 — Explanation layers (always-visible + hover)

**Decision**: Two layers. (a) An **always-visible** one-line caption element under the cache-read
share callout stating the headline lesson in plain language. (b) **Hover** detail via the existing
delegated `data-tip`/`data-sub` tooltip on each of the four token-type labels and on the cache-read
share. The token-type labels themselves are literal words (input / output / cache-write / cache-read),
so each figure's identity is always visible; the tooltip adds the "why," and cache-read's "why" also
lives in the always-visible caption — so nothing meaningful is hover-only (FR-005, SC-002).

**Rationale**: Directly implements the user story and its accessibility clause. Reusing the shared
tooltip avoids a second interaction system (Simplicity).

**Alternatives considered**: Tooltip-only explanations — rejected (invisible in screenshots/print/touch,
violates FR-005). A separate help modal/popover — rejected (new interaction surface, over-built).

---

## D2 — Discoverability affordance

**Decision**: A `.tkhelp` class (dotted underline + `cursor: help`) on every element that carries a
hover explanation, defined in `render.py` CSS (a `.tkhelp` stub already exists there). The delegated
`[data-tip]` handler already fires for any element, so `.tkhelp` only needs to signal "hover me."

**Rationale**: A tooltip nobody hovers is wasted (FR-004). The dotted underline is a conventional,
low-noise "explainable" cue consistent with the dashboard's restraint.

**Alternatives considered**: A `?` glyph per term — rejected (visually noisier across four inline
labels). No affordance — rejected (fails discoverability / FR-004).

---

## D3 — Copy accuracy & extremes

**Decision**: Author concise, accurate copy for each type: input = fresh uncached prompt tokens this
turn; output = tokens generated back; cache-write = context written to the prompt cache the first
time (paid once); cache-read = cached context re-sent and re-billed every turn. The always-visible
caption frames cache-read as "context carried forward and paid for again each turn; a high share
means re-paying to keep context instead of `/clear`-ing and starting fresh." Copy must read sensibly
at extremes — a 0% share is not framed as "expensive."

**Rationale**: FR-006 (honesty) — the tokens are exact reads; the copy describes what each figure is
without implying it is something else. The caption's framing is the lens's core teaching point.

**Alternatives considered**: A single generic "these are token counts" blurb — rejected (loses the
cache-read insight, which is the point). Static examples with fabricated numbers — rejected (could be
mistaken for the user's own data).

---

## D4 — Verification approach (no invented pure functions)

**Decision**: This is DOM/copy work with no new pure logic, so **no new unit tests or pure functions
are invented**. Verification is: (1) the existing Python + `node --test` suites stay green — proving
the embedded blob and the occupancy lens are unchanged (SC-003); (2) a browser/screenshot check with
Playwright served over a local `http.server` (since `file://` is blocked) confirming the always-visible
caption is legible in the screenshot (SC-001) and that the four types + share expose discoverable hover
tooltips (SC-002).

**Rationale**: Honors the technical direction ("do not invent pure functions just to have a test") and
the constitution's Simplicity/Goal-Driven principles.

**Alternatives considered**: Extracting the copy strings into a node-tested table — rejected as
test-for-test's-sake for static text; it is covered by the visible caption + tooltips in the browser check.

---

## Resolved unknowns summary

- Explanation layering + accessibility: always-visible caption + reused tooltips, no hover-only (D1).
- Affordance: `.tkhelp` dotted underline / help cursor (D2).
- Copy accuracy + extremes: exact-read framing, sensible at 0% and dominant share (D3).
- Verification: existing suites green + Playwright screenshot; no new pure functions (D4).
