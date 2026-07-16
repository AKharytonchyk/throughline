# Feature Specification: Token-Lens Legibility

**Feature Branch**: `004-token-lens-legibility`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Make the token terms self-explanatory — an always-visible plain-language caption for the cache-read lesson plus discoverable hover tooltips on the token types. (Repository linking dropped: the top-bar repo filter already answers 'which repo', so session rows stay as they are.)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand what the token terms mean (Priority: P1)

A user new to the cache-read concept opens the token flow view. The numbers are correct but the
terms (input / output / cache-write / cache-read, and the cache-read share) are jargon. They want
the view to teach — in plain language — what each token type is and, especially, why a high
cache-read share is expensive: it is resident context re-sent and re-billed on every turn. The
headline lesson must be readable without any interaction; deeper per-term detail may be revealed on
hover.

**Why this priority**: The lens exists to surface an insight most users don't know. If the terms
aren't explained, the numbers are just jargon and the insight is lost. This is the whole of the
feature.

**Independent Test**: Open the token flow view; confirm a plain-language caption stating the
cache-read lesson is visible without hovering; confirm each of the four token types and the
cache-read share carry a discoverable explanation revealed on hover; confirm no key figure's
meaning exists *only* on hover.

**Acceptance Scenarios**:

1. **Given** the token flow view, **When** it renders, **Then** a one-line plain-language caption
   explaining the cache-read share is visible without any hover or click.
2. **Given** any of the four token types (input, output, cache-write, cache-read), **When** the user
   hovers its label, **Then** a plain-language explanation of that type appears.
3. **Given** the cache-read type or share, **When** the user reads its explanation, **Then** the
   explanation states that cache-read is context re-sent/re-billed each turn and that a high share
   means paying to carry context forward instead of starting fresh.
4. **Given** an element that has a hover explanation, **When** the view is rendered, **Then** that
   element shows a visible affordance indicating it is explainable (so the tooltip is discoverable).
5. **Given** a static screenshot or a touch device with no hover, **When** the user reads the view,
   **Then** the headline cache-read lesson is still conveyed (it is not hover-only).

---

### Edge Cases

- **Touch / no-hover / print**: tooltips are unavailable, but every key figure's meaning is still
  available from always-visible text.
- **Empty window**: when the filtered window has no token data, the explanatory text does not render
  (the existing empty state shows) — no errors.
- **Very high or 0% cache-read share**: the caption/explanation reads sensibly at both extremes
  (0% is not framed as "expensive"; a dominant share is).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The token flow view MUST show an always-visible, one-line, plain-language caption
  stating the cache-read lesson (that cache-read is context re-billed every turn and a high share
  means re-paying to carry context instead of starting fresh).
- **FR-002**: Each of the four token types (input, output, cache-write, cache-read) MUST have a
  plain-language explanation available on hover.
- **FR-003**: The cache-read share MUST have a plain-language explanation available on hover that
  states why a high share is expensive.
- **FR-004**: Every element that carries a hover explanation MUST present a visible affordance
  indicating it is explainable (discoverability).
- **FR-005**: No key figure's meaning may exist ONLY on hover — each explained figure MUST also have
  its meaning conveyed by always-visible text somewhere in the view (accessibility for screenshots,
  print, and touch).
- **FR-006**: The explanations MUST be accurate and consistent with the tool's honesty discipline —
  describing what each token figure is (exact reads), never implying a figure is something it is not.
- **FR-007**: This feature MUST NOT add new collected data, new parsing, new embedded-blob fields, or
  any change to the occupancy (chars) lens or the token-flow numbers; it reuses the existing
  token-flow data and the existing hover-tooltip mechanism.

### Key Entities *(include if feature involves data)*

- **Token type**: one of input / output / cache-write / cache-read — each gains a plain-language
  description shown in the UI (text only, not stored data). No new stored fields anywhere.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The headline cache-read lesson is readable in a static screenshot of the token flow
  view (verified with the tool's own screenshot check), i.e. it is not hover-gated.
- **SC-002**: All four token types and the cache-read share have a discoverable explanation, and each
  explained figure's meaning is also present in always-visible text (0 hover-only figures).
- **SC-003**: The occupancy (chars) lens and the token-flow numbers are unchanged by this feature
  (existing golden/aggregation tests still pass; no new blob fields).

## Assumptions

- The existing shared hover-tooltip mechanism (title + sub-text) is sufficient for the per-term
  explanations; no new interaction system is introduced.
- Repository attribution is intentionally **out of scope**: the top-bar repository filter already
  answers "which repo," so per-session repository display is not added and session rows are left
  as they are.
- The explanation copy is authored for a single technical user (the tool's audience); it does not
  require localization.
