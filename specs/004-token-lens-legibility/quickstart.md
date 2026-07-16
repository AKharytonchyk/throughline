# Quickstart / Validation: Token-Lens Legibility

Proves the explain layer works and that nothing else changed. Display-only; no new pure functions.

## Regression (proves the blob + occupancy lens are unchanged — SC-003)

```bash
PYTHONPATH=src python3 -m unittest discover -s tests           # all stdlib unittests stay green
node --test tests/token_flow.test.mjs tests/app_aggregate.test.mjs   # client aggregators unchanged
```

## Browser check (SC-001, SC-002)

`file://` is blocked for the browser tooling, so serve the generated dashboard locally:

```bash
throughline report --out /tmp/thl/dash.html      # or reuse an existing dashboard.html
python3 -m http.server 8931 --bind 127.0.0.1     # from the directory containing dash.html
```

Then, in the browser, switch to the **Token usage** lens and confirm:

1. **Always-visible caption (SC-001)** — under the cache-read share callout, a one-line plain-language
   caption states the cache-read lesson. It is visible **without** hovering (verify it appears in a
   static screenshot of the view).
2. **Discoverable tooltips (SC-002)** — the four token-type labels (input / output / cache-write /
   cache-read) and the cache-read share each show a dotted-underline / help-cursor affordance; hovering
   any of them reveals a plain-language explanation. Cache-read's explanation states it is context
   re-sent/re-billed every turn and why a high share is expensive.
3. **No hover-only meaning (SC-002)** — with tooltips ignored (as in a screenshot), the type identities
   (the literal labels) and the cache-read lesson (the caption) are still readable.

## Offline / constitution checks

- The generated HTML makes no network requests (no CDN/external assets); the explain copy is static text.
- Output stays under the working directory; transcripts are untouched.
- The occupancy lens is unchanged and still the default.
