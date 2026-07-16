# Phase 1 Data Model: Token-Lens Legibility

**No new stored data.** This feature adds no fields to the embedded blob, no parser output, and no
analysis. It is display-only text layered on the existing feature-003 `token_flow` section.

The only "entities" are UI copy strings (authored, static, not derived from user data):

## Token-type description (UI copy)

For each of the four token types the token flow view already renders, an authored plain-language
description shown as hover detail (`data-sub`) with the type name as the tooltip title (`data-tip`).

| Type | Title (data-tip) | Meaning (data-sub, plain language) |
|------|------------------|-------------------------------------|
| `input` | input | Fresh, uncached tokens you send this turn (new prompt content). |
| `output` | output | Tokens the model generates back to you this turn. |
| `cache_write` | cache-write | Context written into the prompt cache the first time — paid once when cached. |
| `cache_read` | cache-read | Cached context re-sent and **re-billed every turn**; a high share means you're mostly paying to carry the same context forward instead of `/clear`-ing and starting a fresh, smaller task. |

## Cache-read share caption (always-visible UI copy)

A one-line, always-visible caption rendered under the existing cache-read share callout, stating the
headline lesson in plain language (the same insight as the cache-read row above, but never
hover-gated). Also carries a hover explanation of "share" for the deeper layer.

## Notes

- These strings live in `report/app.js` (rendered) / `report/render.py` (styling); they are content,
  not stored data, and reference no user-specific values.
- Accuracy constraint (FR-006): each description states what the figure **is** (an exact read of
  `usage`), never implying it is an estimate or something else.
