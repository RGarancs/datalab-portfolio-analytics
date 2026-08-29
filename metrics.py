"""metrics.py -- KPI catalog, stock/flow computation, and number formatting.

Two kinds of KPI:
    * stock  -- a balance "as of" a date (loan book, # customers, portfolio
                yield). Delta = value today minus value at the start of the
                window (how much the balance moved over the period).
    * flow   -- an amount that accrues within a window (originated this period,
                new customers, deposits in). Delta = this window vs the previous
                equal-length window.

All computations run on the dimension-filtered ("scoped") tables, so sidebar
filters + the Split/Focus controls cascade into every card automatically.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COST_OF_FUNDS = 0.35  # share of gross loan interest paid away as deposit interest & funding cost

ALL = {"Internal", "Investor-Facing", "Public Website"}
INT_INV = {"Internal", "Investor-Facing"}
OUTSTANDING_STATUSES = ["In payment", "In risk mitigation", "Collateralized", "Sold to reinsurance"]

# key -> label, kind, fmt, higher_is_better, audiences
CATALOG: dict[str, dict] = {
    "outstanding":       dict(label="Loan Book (outstanding)", kind="stock", fmt="eur", hib=True,  audiences=ALL),
    "total_funded":      dict(label="Originated (cumulative)",kind="stock", fmt="eur", hib=True,  audiences=ALL),
    "funded_period":     dict(label="Originated (period)",    kind="flow",  fmt="eur", hib=True,  audiences=ALL),
    "avg_return":        dict(label="Portfolio Yield",        kind="stock", fmt="pct", hib=True,  audiences=ALL),
    "avg_loan_term":     dict(label="Avg. Loan Term",          kind="stock", fmt="months", hib=True, audiences=ALL),
    "interest_paid":     dict(label="Net Interest Income",    kind="stock", fmt="eur", hib=True,  audiences=ALL),
    "platform_fees":     dict(label="Cost of Funds",          kind="stock", fmt="eur", hib=True,  audiences=INT_INV),
    "default_rate_12m":  dict(label="12M Default Rate",        kind="stock", fmt="pct", hib=False, audiences=INT_INV),
    "n_investors":       dict(label="Total Customers",        kind="stock", fmt="int", hib=True,  audiences=ALL),
    "new_investors":     dict(label="New Customers (period)", kind="flow",  fmt="int", hib=True,  audiences=ALL),
    "avg_investment":    dict(label="Avg. Disbursement (period)", kind="flow", fmt="eur", hib=True,  audiences=INT_INV),
    "deposits_period":   dict(label="Deposits In (period)",   kind="flow",  fmt="eur", hib=True,  audiences=INT_INV),
    "net_deposits_period": dict(label="Net Deposit Flow (period)",kind="flow",  fmt="eur", hib=True,  audiences=INT_INV),
    "avg_ltv":           dict(label="Avg. LTV (secured)",     kind="stock", fmt="pct", hib=False, audiences=INT_INV),
    "n_projects":        dict(label="Total Loans",            kind="stock", fmt="int", hib=True,  audiences=ALL),
}

DEFAULT_KPIS = ["outstanding", "total_funded", "funded_period", "avg_return",
                "default_rate_12m", "n_investors", "new_investors", "avg_loan_term"]

# 4 relevant KPIs per tab (Overview uses the 8 selectable cards)
TAB_KPIS = {
    "portfolio": ["outstanding", "n_projects", "avg_return", "avg_ltv"],
    "cumulative": ["total_funded", "avg_loan_term", "interest_paid", "avg_return"],
    "activity": ["deposits_period", "net_deposits_period", "new_investors", "avg_loan_term"],
    "funds": ["net_deposits_period", "deposits_period", "funded_period", "avg_investment"],
    "projects": ["n_projects", "outstanding", "avg_return", "avg_ltv"],
    "risk": ["default_rate_12m", "outstanding", "avg_ltv", "n_projects"],
    "marketing": ["n_investors", "new_investors", "avg_investment", "total_funded"],
    "analytics": ["outstanding", "default_rate_12m", "avg_ltv", "n_projects"],
}


# ----------------------------------------------------------------------------
# formatting
# ----------------------------------------------------------------------------
def format_number(value: float, fmt: str) -> str:
    v = float(value or 0)
    if fmt in ("eur", "eur_compact"):
        a, sign = abs(v), ("-" if v < 0 else "")
        if a >= 1e9:
            return f"{sign}€{a/1e9:.1f}B"
        if a >= 1e6:
            return f"{sign}€{a/1e6:.1f}M"
        if a >= 1e3:
            return f"{sign}€{a/1e3:.0f}K"
        return f"{sign}€{a:,.0f}"
    if fmt == "eur_full":
        return f"€{v:,.0f}"
    if fmt == "pct":
        return f"{v:.1f}%"
    if fmt == "months":
        return f"{v:.0f} mo"
    if fmt == "int":
        return f"{int(round(v)):,}"
    return str(value)


# legacy alias -- earlier view modules import `format_value`
format_value = format_number


def format_delta(delta: float, fmt: str, base: float | None) -> tuple[str, str]:
    """Return (text, direction). Colour semantics decided by caller."""
    sign = "+" if delta >= 0 else "−"  # proper minus
    body = format_number(abs(delta), fmt)
    if base:
        pct = delta / base * 100
        return f"{sign}{body} · {pct:+.1f}%", ("up" if delta > 0 else "down" if delta < 0 else "flat")
    return f"{sign}{body}", ("up" if delta > 0 else "down" if delta < 0 else "flat")


def _weighted(values: pd.Series, weights: pd.Series) -> float:
    w = weights.clip(lower=0)
    if len(values) == 0 or float(w.sum()) == 0:
        return 0.0
    return float(np.average(values, weights=w))


# ----------------------------------------------------------------------------
# stock & flow
# ----------------------------------------------------------------------------
def compute_stock(scoped: dict, as_of: pd.Timestamp) -> dict:
    as_of = pd.Timestamp(as_of)
    projects, investors = scoped["projects"], scoped["investors"]

    p = projects[projects["start_date"] <= as_of]
    funded = p[p["funded_amount"] > 0]
    outstanding_mask = (p["maturity_date"].isna() | (p["maturity_date"] > as_of)) & (p["funded_amount"] > 0)
    outstanding = p.loc[outstanding_mask, "funded_amount"].sum()

    w0 = as_of - pd.DateOffset(months=12)
    matured = projects[
        projects["status"].isin(["Repaid", "Defaulted"]) & projects["maturity_date"].between(w0, as_of)
    ]
    matured_total = float(matured["funded_amount"].sum())
    default_rate = (
        float(matured.loc[matured["status"] == "Defaulted", "funded_amount"].sum()) / matured_total * 100
        if matured_total else 0.0
    )

    # returns: gross interest on repaid loans, platform fee, net to investors, net AROI
    repaid = p[p["status"] == "Repaid"]
    gross_interest = float((repaid["funded_amount"] * repaid["interest_rate"] / 100
                            * repaid["term_months"] / 12).sum())
    platform_fees = gross_interest * COST_OF_FUNDS
    interest_paid = gross_interest - platform_fees
    aroi_net = _weighted(funded["interest_rate"], funded["funded_amount"]) * (1 - COST_OF_FUNDS)

    return {
        "outstanding": float(outstanding),
        "total_funded": float(funded["funded_amount"].sum()),
        "avg_return": _weighted(funded["interest_rate"], funded["funded_amount"]),
        "avg_loan_term": _weighted(funded["term_months"], funded["funded_amount"]),
        "aroi_net": aroi_net,
        "interest_paid": interest_paid,
        "platform_fees": platform_fees,
        "avg_ltv": _weighted(p.loc[p["ltc"].notna(), "ltc"],
                             p.loc[p["ltc"].notna(), "funded_amount"].clip(lower=1)),
        "n_projects": int(p["project_id"].nunique()),
        "n_investors": int(investors.loc[investors["registration_date"] <= as_of, "investor_id"].nunique()),
        "default_rate_12m": default_rate,
    }


def compute_flows(scoped: dict, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    projects, investors = scoped["projects"], scoped["investors"]
    investments, transactions = scoped["investments"], scoped["transactions"]

    funded_period = projects.loc[projects["start_date"].between(start, end), "funded_amount"].sum()
    new_investors = investors.loc[investors["registration_date"].between(start, end), "investor_id"].nunique()
    ivp = investments[investments["invested_date"].between(start, end)]
    avg_investment = float(ivp["amount"].mean()) if len(ivp) else 0.0
    txp = transactions[transactions["date"].between(start, end)]
    deposits = txp.loc[txp["type"] == "Deposit", "amount"].sum()
    net_deposits = txp["amount"].sum()

    return {
        "funded_period": float(funded_period),
        "new_investors": int(new_investors),
        "avg_investment": avg_investment,
        "deposits_period": float(deposits),
        "net_deposits_period": float(net_deposits),
    }


def build_kpis(scoped: dict, window_start, as_of, prev_start, prev_end, show_delta: bool) -> dict:
    stock_now = compute_stock(scoped, as_of)
    stock_start = compute_stock(scoped, window_start) if show_delta else None
    flow_now = compute_flows(scoped, window_start, as_of)
    flow_prev = compute_flows(scoped, prev_start, prev_end) if (show_delta and prev_start is not None) else None

    kpis = {}
    for key, meta in CATALOG.items():
        if meta["kind"] == "stock":
            value = stock_now[key]
            base = stock_start[key] if stock_start else None
        else:
            value = flow_now[key]
            base = flow_prev[key] if flow_prev else None
        delta = (value - base) if (show_delta and base is not None) else None
        kpis[key] = {**meta, "key": key, "value": value, "base": base, "delta": delta}
    return kpis


def kpi_items(kpis: dict, keys: list[str], audience: str, sparks: dict | None = None) -> tuple[list[dict], list[str]]:
    """Turn selected KPI keys into render-ready card dicts + list of hidden labels.
    `sparks` (optional) attaches a mini trend series per KPI key."""
    items, hidden = [], []
    for key in keys:
        k = kpis.get(key)
        if not k:
            continue
        if audience not in k["audiences"]:
            hidden.append(k["label"])
            continue
        item = {"key": key, "label": k["label"], "value": format_number(k["value"], k["fmt"]),
                "delta": None, "dir": "none"}
        if k["delta"] is not None:
            text, sign = format_delta(k["delta"], k["fmt"], k["base"])
            item["delta"] = text
            if sign == "flat":
                item["dir"] = "flat"
            else:
                good = (sign == "up") == k["hib"]
                item["dir"] = "good" if good else "bad"
        if sparks and sparks.get(key):
            item["spark"] = sparks[key]
        items.append(item)
    return items, hidden


def tab_kpi_items(kpis: dict, tab: str, audience: str, sparks: dict | None = None) -> list[dict]:
    """The 4 tab-relevant KPI cards, audience-filtered."""
    items, _ = kpi_items(kpis, TAB_KPIS.get(tab, []), audience, sparks)
    return items


AUDIENCE_WORD = {"Internal": "Internal", "Investor-Facing": "Investor", "Public Website": "Public"}


def pipeline_counts(investors, as_of) -> dict:
    """Customer funnel as of a date: Onboarded -> KYC verified -> With deposit account."""
    reg = investors[investors["registration_date"] <= pd.Timestamp(as_of)]
    return {
        "Onboarded": int(len(reg)),
        "KYC verified": int(reg["identified"].sum()) if "identified" in reg.columns else int(len(reg)),
        "With deposit account": int(reg["active"].sum()) if "active" in reg.columns else int(len(reg)),
    }


def loan_pipeline_counts(projects: pd.DataFrame, as_of, by: str = "Loans") -> dict:
    """Loan-book funnel as of a date: originated / in payment / distressed."""
    df = projects[projects["start_date"] <= pd.Timestamp(as_of)]
    distressed = ["In risk mitigation", "Collateralized", "Sold to reinsurance", "Defaulted"]
    return {
        "Originated": int(len(df)),
        "In payment": int((df["status"] == "In payment").sum()),
        "Distressed": int(df["status"].isin(distressed).sum()),
        "avg_size": float(df["funded_amount"].mean()) if len(df) else 0.0,
    }


def build_sparklines(scoped: dict, as_of, months: int = 12) -> dict:
    """12-month trend series per KPI key, for the mini sparklines on cards."""
    as_of = pd.Timestamp(as_of)
    m0 = (as_of.to_period("M").to_timestamp() - pd.DateOffset(months=months - 1))
    idx = pd.date_range(m0, as_of.to_period("M").to_timestamp(), freq="MS")
    p = scoped["projects"]; investors = scoped["investors"]
    investments, tx = scoped["investments"], scoped["transactions"]
    funded = p[p["funded_amount"] > 0]

    def monthly(df, datecol, valcol, how="sum"):
        if df.empty:
            return pd.Series(0.0, index=idx)
        g = df.groupby(df[datecol].dt.to_period("M").dt.to_timestamp())[valcol]
        s = (g.sum() if how == "sum" else g.mean())
        return s.reindex(idx, fill_value=0) if how == "sum" else s.reindex(idx).ffill().fillna(0)

    def cumulative(df, datecol, valcol):
        if df.empty:
            return pd.Series(0.0, index=idx)
        s = df.groupby(df[datecol].dt.to_period("M").dt.to_timestamp())[valcol].sum().cumsum()
        return s.reindex(idx, method="ffill").fillna(0)

    def cum_count(df, datecol):
        if df.empty:
            return pd.Series(0.0, index=idx)
        s = df.groupby(df[datecol].dt.to_period("M").dt.to_timestamp()).size().cumsum()
        return s.reindex(idx, method="ffill").fillna(0)

    def cum_weighted(valcol):
        out = []
        for m in idx:
            sub = funded[funded["start_date"] <= m]
            out.append(float(np.average(sub[valcol], weights=sub["funded_amount"].clip(lower=1))) if len(sub) else 0.0)
        return out

    total_funded = cumulative(funded, "start_date", "funded_amount")
    out = {
        "total_funded": total_funded.tolist(),
        "outstanding": total_funded.tolist(),
        "funded_period": monthly(funded, "start_date", "funded_amount").tolist(),
        "n_investors": cum_count(investors, "registration_date").tolist(),
        "new_investors": monthly(investors, "registration_date", "investor_id", "sum").tolist()
        if not investors.empty else [0] * len(idx),
        "avg_investment": monthly(investments, "invested_date", "amount", "mean").tolist(),
        "avg_return": cum_weighted("interest_rate"),
        "avg_loan_term": cum_weighted("term_months"),
        "avg_ltv": cum_weighted("ltc"),
        "n_projects": cum_count(p, "start_date").tolist(),
    }
    if not tx.empty:
        out["deposits_period"] = monthly(tx[tx["type"] == "Deposit"], "date", "amount").tolist()
        out["net_deposits_period"] = monthly(tx, "date", "amount").tolist()
    # new_investors via count of registrations per month
    if not investors.empty:
        reg = investors.groupby(investors["registration_date"].dt.to_period("M").dt.to_timestamp()).size().reindex(idx, fill_value=0)
        out["new_investors"] = reg.tolist()
    return out
