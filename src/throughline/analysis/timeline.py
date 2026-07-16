"""Time helpers for the cost-over-time trend (feature 002, research.md D4).

The cube's finest time grain is the **day** (UTC). Week bucketing is pure summation of days,
and the display granularity is chosen by the span (daily for short histories, weekly for
longer) — these Python helpers are the golden reference for the client's identical logic.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta


def day_of(timestamp: str | None) -> str | None:
    """UTC `YYYY-MM-DD` from an ISO-8601 timestamp; None if unparseable/missing."""
    if not timestamp:
        return None
    ts = timestamp.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        # tolerate fractional seconds / trailing junk by trimming to seconds
        try:
            dt = datetime.fromisoformat(ts[:19])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def week_of(day: str) -> str:
    """The Monday (ISO week start) for a `YYYY-MM-DD` day, as `YYYY-MM-DD`."""
    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def span_days(days: list[str]) -> int:
    """Inclusive number of days spanned by a set of `YYYY-MM-DD` values."""
    if not days:
        return 0
    ds = sorted(days)
    a = datetime.strptime(ds[0], "%Y-%m-%d")
    b = datetime.strptime(ds[-1], "%Y-%m-%d")
    return (b - a).days + 1


def choose_granularity(days: list[str], daily_max_span: int = 14) -> str:
    """'day' for a short span (<= daily_max_span days), else 'week' (research.md D4)."""
    return "day" if span_days(days) <= daily_max_span else "week"


def bucket_of(day: str, granularity: str) -> str:
    return day if granularity == "day" else week_of(day)
