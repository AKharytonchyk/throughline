"""Optional dollar-cost ESTIMATE (feature 003, US4 / FR-010) — opt-in and isolated.

The token lens works fully when this module or ``prices.json`` is absent. Prices are
user-provided (never fetched — Local-Only) and every figure is a labeled estimate stating
its basis (effective date + unit). A model present in the data but absent from the price
list is reported **unpriced** (cost omitted), never guessed.
"""
from __future__ import annotations

from throughline.analysis.tokens import FLOW_KEYS


def estimate(by_model_totals: dict, price_list: dict | None) -> dict | None:
    """Build the ``cost`` blob object, or None when there is nothing to price.

    ``by_model_totals``: ``{modelId: {input, output, cache_write, cache_read}}`` summed over
    the dataset. ``price_list``: parsed ``prices.json`` (empty / missing ``models`` ⇒ None).
    """
    models = (price_list or {}).get("models") or {}
    if not price_list or not models:
        return None
    unit = price_list.get("unit", "per_million")
    per_million = unit != "per_token"
    currency = price_list.get("currency", "USD")
    effective = price_list.get("effective")
    denom = "million tokens" if per_million else "token"
    unit_label = f"{currency} per {denom}"

    by_model: dict[str, dict] = {}
    grand = 0.0
    for model, totals in by_model_totals.items():
        prices = models.get(model)
        if not prices:  # model seen in data but not in the price list → unpriced, never guessed
            by_model[model] = {"priced": False}
            continue
        entry: dict = {"priced": True}
        subtotal = 0.0
        for k in FLOW_KEYS:
            up = prices.get(k)
            if up is None:  # this token type is unpriced for this model
                continue
            toks = totals.get(k, 0)
            dollars = toks * up / 1_000_000 if per_million else toks * up
            entry[k] = dollars
            subtotal += dollars
        entry["total"] = subtotal
        grand += subtotal
        by_model[model] = entry

    return {
        "available": True,
        "effective": effective,
        "unit_label": unit_label,
        "currency": currency,
        "total": grand,
        "by_model": by_model,
    }


def unit_prices(price_list: dict | None) -> dict | None:
    """Per-model UNIT prices for scope-aware client-side dollarizing (feature 005).

    Unlike ``estimate`` (whole-dataset computed dollars), this exposes the raw per-model,
    per-type unit prices so the client can dollarize a *filtered* token saving. Same opt-in
    gate: empty/missing price list ⇒ None ⇒ no dollar figure anywhere. A missing token type
    for a model is simply omitted (that type is unpriced — never guessed).
    """
    models = (price_list or {}).get("models") or {}
    if not price_list or not models:
        return None
    unit = price_list.get("unit", "per_million")
    per_million = unit != "per_token"
    currency = price_list.get("currency", "USD")
    denom = "million tokens" if per_million else "token"
    return {
        "available": True,
        "currency": currency,
        "effective": price_list.get("effective"),
        "unit_label": f"{currency} per {denom}",
        "per_million": per_million,
        "by_model": {
            model: {k: prices[k] for k in FLOW_KEYS if isinstance(prices, dict) and prices.get(k) is not None}
            for model, prices in models.items()
        },
    }
