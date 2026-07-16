# Quickstart / Validation: Token Usage & Cost

Runnable checks that prove the token lens works end-to-end. Assumes sessions are already collected (`throughline collect`). See [data-model.md](./data-model.md) and [contracts/](./contracts/) for shapes.

## Prerequisites

- Python 3.11+ (repo runs on 3.14), standard library only.
- Node (dev-only) for the client aggregation tests.
- Collected transcripts under `~/.throughline/transcripts` (or use the token fixtures under `tests/fixtures/tokens/`).

## Generate & open

```bash
throughline report --open      # builds ~/.throughline/out/dashboard.html and opens it
```

Then in the dashboard:

1. **Lens switch** — switch from **Context window (chars)** to **Token usage**. *Expected:* the two lenses show different views and different units; nothing is merged. (SC-005)
2. **Token flow by type** — see input / output / cache-write / cache-read and the **cache-read share** of the total; every figure labeled *exact*. *Expected on real data:* cache-read dominates. (US1, FR-002/004/005)
3. **Re-billing growth** — pick a session; see cumulative tokens rise across its turns, cache-read emphasized. (US2, FR-006)
4. **Over-time trend** — see per-day (or per-week) token totals; apply the repo/time filter and confirm the trend and intervention markers respond. (US3, FR-007/008)
5. **By-model** — confirm totals split by model and the parts sum to the whole. (FR-009)

## Cost estimate (opt-in)

```bash
# with NO price list present:
#   -> no dollar figure appears anywhere in the token lens.   (US4, FR-010)

# add a price list, then regenerate:
$EDITOR ~/.throughline/prices.json     # see contracts/price-list.schema.json (example inside)
throughline report --open
```

*Expected:* a dollar estimate appears, **labeled an estimate** with its price basis (effective date + unit). Any model present in the data but missing from `prices.json` is shown as **unpriced**, not guessed. Remove `prices.json` and regenerate → dollar figures disappear entirely, token views still work.

## Automated tests

```bash
# Python (stdlib unittest) — includes the reconciliation GOLDEN test
PYTHONPATH=src python3 -m unittest discover -s tests

# the reconciliation golden test specifically (SC-002)
PYTHONPATH=src python3 -m unittest tests.test_tokens -v

# client aggregation pure functions (dev-only)
node --test tests/token_flow.test.mjs
```

**Golden reconciliation (SC-002)** — the key check: for every session, the four token-type totals equal the sum of that session's per-turn `usage`, with **zero discrepancy**; and the per-model split sums back to the session totals (FR-009).

## Offline / constitution checks

- Generate with the network disabled → succeeds (Local-Only). No request is made for prices; they come only from `prices.json`.
- Confirm all output stays under the working directory; transcripts are read only.
- Confirm the occupancy lens (features 001/002) is unchanged and still the default.
