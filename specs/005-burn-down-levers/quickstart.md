# Quickstart / Validation: Burn-Down / Biggest Levers

Runnable checks that prove the feature end-to-end. Assumes a working checkout; no network.

## Prerequisites

- Python 3.11+ (stdlib only), Node.js (for the dev-only client aggregation tests).
- Collected sessions: `throughline collect` (or use the fixtures under `tests/fixtures/levers/`).

## Build & open

```bash
PYTHONPATH=src python3 -m throughline collect        # read-only copy of your sessions
PYTHONPATH=src python3 -m throughline report --open   # single self-contained dashboard.html
```

Switch to the **Token usage** lens → **01 — Biggest levers** is the first section.

## Scenario 1 — Ranked levers with per-day token savings (US1 / SC-001, SC-004)

1. Open the burn-down section with data containing an unused mounted tool, a recurring chain, and
   a long session.
2. **Expect**: a ranked list; each lever shows a `title`, a plain-language `action`, a
   `tokens/day` figure (human-scaled), and an `est` chip; hovering shows the `method`.
3. **Expect**: the top row has the largest `tokens/day`; the order is strictly descending.

## Scenario 2 — Opt-in dollars (US2 / SC-003)

```bash
# with NO prices.json present:
PYTHONPATH=src python3 -m throughline report
#   -> burn-down shows token savings only; NO "$" anywhere.

# add a per-model price list, then rebuild:
cp specs/003-token-usage-cost/contracts/price-list.schema.json /tmp/ref.json  # shape reference
$EDITOR ~/.throughline/prices.json                                            # user-provided prices
PYTHONPATH=src python3 -m throughline report
#   -> each lever and the aggregate show "$ /day" with the price basis;
#      any in-scope model absent from prices.json is named as excluded (never guessed).
```

## Scenario 3 — Scope-aware recomputation (US3)

1. Change the **Repo** filter, then the **From/To** range.
2. **Expect**: the levers, their `tokens/day` (and `$/day`), and the basis line
   (`active_days` / `turns_per_day`) recompute immediately, with no page reload and no re-run.
3. With a window of `< 3` active days, **expect** a small-sample note on the basis.

## Scenario 4 — Aggregate with overlap caveat (US4 / SC-006)

- **Expect** a single "if you act on these" figure (tokens/day, and `$/day` when priced) at the
  top of the section, rendered with an explicit statement that per-lever savings may overlap and
  are not guaranteed to sum.

## Scenario 5 — No significant levers (SC-005 / FR-009)

- Filter to a scope with no unused tools, no recurring chains, and only short sessions.
- **Expect**: an explicit "no significant levers found in this window" message — **not** a blank
  panel and **not** fabricated/zero-value rows.

## Automated checks

```bash
# Python: blob additions + golden reconciliation of the per-tool resident split
PYTHONPATH=src:tests python3 -m unittest test_levers_blob -v   # (or: unittest discover -s tests)

# Client: pure aggregateLevers (ranking, per-day math, dollarize, empty state)
node --test tests/burndown.test.mjs

# Regression: existing suites still green
PYTHONPATH=src python3 -m unittest discover -s tests
node --test tests/app_aggregate.test.mjs tests/token_flow.test.mjs
```

**Pass criteria**: all six success criteria (SC-001..SC-006) observable in the dashboard; the
golden reconciliation passes; no `$` appears without a price list; the two new blob fields match
[embedded-levers.schema.json](./contracts/embedded-levers.schema.json); no network access and no
writes outside the working directory occur during any step.
