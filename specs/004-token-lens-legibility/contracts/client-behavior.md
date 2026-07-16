# Client Behavior Contract (addendum): Token-Lens Legibility

Extends feature 003's `contracts/client-behavior.md`. Behavior only; no blob shape changes. Traces to
FR-### / SC-### in this feature's spec.

## Explain layer in the token flow view (FR-001..FR-006)

- The **Token flow by type** view (`renderTokenFlow` in `app.js`) renders, directly under the
  cache-read share callout, an **always-visible** one-line caption stating the cache-read lesson in
  plain language (FR-001). This text is present in the DOM without any hover/click (SC-001).
- Each of the four token-type labels (input / output / cache-write / cache-read) and the cache-read
  share carry `data-tip` (title) + `data-sub` (plain-language explanation) consumed by the **existing**
  delegated hover tooltip — no new tooltip system is introduced (FR-002, FR-003).
- Every element carrying a hover explanation also carries the `.tkhelp` class (dotted underline +
  `cursor: help`) so the tooltip is discoverable (FR-004).
- No key figure's meaning is hover-only (FR-005): the type labels are literal words (always visible),
  and the cache-read "why" is in the always-visible caption as well as the tooltip. Zero hover-only
  figures (SC-002).
- Copy is accurate to the honesty discipline (FR-006): tokens are described as exact reads of `usage`.

## Unchanged (FR-007 / SC-003)

- The embedded blob shape is unchanged; `flowTotals` / `flowByModel` / `flowByDay` / `sessionGrowth` /
  `costEstimate` and all occupancy aggregators are untouched.
- The "By session" table and the growth-curve session selector are unchanged (repository linking is
  out of scope; the top-bar repo filter covers "which repo").
- The occupancy (chars) lens is untouched and remains the default lens.
