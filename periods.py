"""periods.py -- reporting-window logic.

    Snapshot -- all-time cumulative, as of today (default point-in-time view)
    MTD      -- last 30 days (rolling, NOT calendar month-to-date)
    QTD      -- last 90 days (rolling)
    YTD      -- year-to-date (calendar, Jan 1 -> today)
    12MR     -- trailing 12 months (rolling)
    Custom   -- whatever the date picker says

`previous_window` returns the immediately-preceding comparable window so KPI
cards can show a period-over-period delta:
    MTD  -> the 30 days before this one   (t-60 .. t-30)
    QTD  -> the 90 days before this one   (t-180 .. t-90)
    YTD  -> the same period a year ago
    12MR -> the prior 12 months
    Custom -> the equally-long window immediately before.
"""
from __future__ import annotations

import pandas as pd

PERIODS = ["Snapshot", "MTD", "QTD", "YTD", "12MR", "Custom"]
PERIODS_WITH_DELTA = {"MTD", "QTD", "YTD", "12MR", "Custom"}

_ROLLING_DAYS = {"MTD": 30, "QTD": 90}
_NAMES = {"MTD": "Last 30 days", "QTD": "Last 90 days", "YTD": "Year-to-date",
          "12MR": "Trailing 12 months", "Custom": "Custom range", "Snapshot": "All-time"}


def resolve_window(period: str, today, data_min, custom=None) -> tuple[pd.Timestamp, pd.Timestamp]:
    today = pd.Timestamp(today).normalize()
    if period in _ROLLING_DAYS:
        start = today - pd.Timedelta(days=_ROLLING_DAYS[period])
    elif period == "YTD":
        start = today.replace(month=1, day=1)
    elif period == "12MR":
        start = today - pd.DateOffset(months=12)
    elif period == "Custom" and custom is not None:
        s, e = custom
        return pd.Timestamp(s).normalize(), pd.Timestamp(e).normalize()
    else:  # Snapshot / all-time
        start = data_min
    return pd.Timestamp(start).normalize(), today


def previous_window(period: str, start, end):
    """Comparable prior window; (None, None) when a delta doesn't make sense."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if period in _ROLLING_DAYS:
        d = _ROLLING_DAYS[period]
        return start - pd.Timedelta(days=d), start
    if period == "YTD":
        return start - pd.DateOffset(years=1), end - pd.DateOffset(years=1)
    if period == "12MR":
        return start - pd.DateOffset(months=12), start
    if period == "Custom":
        length = end - start
        return start - length, start
    return None, None


def window_label(period: str, start, end) -> str:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if period == "Snapshot":
        return f"All-time · as of {end.date()}"
    return f"{_NAMES.get(period, period)} · {start.date()} → {end.date()}"


def comparison_label(period: str, prev_start, prev_end) -> str:
    if prev_start is None or prev_end is None:
        return "no comparison (all-time snapshot)"
    return f"{pd.Timestamp(prev_start).date()} → {pd.Timestamp(prev_end).date()}"
