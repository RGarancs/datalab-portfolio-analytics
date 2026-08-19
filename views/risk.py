"""Topic ⑥ -- Risk & Recovery. Four headline cards (Current portfolio · In
Recovery · Restructured · Default, each as a share of the current portfolio,
plus a trailing-12-month default rate), a distressed-volume chart, a deep-dive
split explorer + (internal) budget/benchmark, and a selectable distressed-loans
table (In Recovery / Restructured / Defaulted) with recovery detail.

Several loan-level recovery fields (partial repaid, late principal / interest)
are SYNTHESISED for illustration -- clearly labelled -- because they are not in
the source export. Collateral value is derived from loan amount and LTC."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, plotly_layout, render_kpi_row
from metrics import format_number
from ui import chart_card, card_header, render_table, norm, RATING_BADGE, column_picker, build_split_payload, deep_dive
from dims import PROJECT_DIMS

TERM_BUCKETS = [(0, 12, "0–12m"), (12, 24, "12–24m"), (24, 36, "24–36m"), (36, 999, "36m+")]
OUTSTANDING = ["Active", "Servicing", "Restructured", "In Recovery", "Defaulted"]


def _row_seed(pid: str) -> int:
    digits = "".join(ch for ch in str(pid) if ch.isdigit())
    return int(digits) if digits else 0


def render(scoped: dict, theme: str, audience: str, today) -> None:
    import components_hover

    colors = atelier_colorway(theme)
    projects = scoped["projects"]
    today = pd.Timestamp(today)

    book = projects[projects.status.isin(OUTSTANDING)]
    current_port = float(book["funded_amount"].sum())
    base = max(current_port, 1.0)
    rec = projects[projects.status == "In Recovery"]
    res = projects[projects.status == "Restructured"]
    dft = projects[projects.status == "Defaulted"]
    rec_amt, res_amt, dft_amt = (float(x["funded_amount"].sum()) for x in (rec, res, dft))
    dflt_12m = dft[dft["default_date"] >= today - pd.DateOffset(months=12)] if not dft.empty else dft
    default_rate_12m = float(dflt_12m["funded_amount"].sum()) / base * 100

    # ---- 4 headline cards ----
    render_kpi_row([
        {"label": "Current portfolio", "value": format_number(current_port, "eur"),
         "delta": f"{len(book):,} loans outstanding", "dir": "none"},
        {"label": "In Recovery", "value": format_number(rec_amt, "eur"),
         "delta": f"{rec_amt / base * 100:.1f}% of portfolio", "dir": "bad"},
        {"label": "Restructured", "value": format_number(res_amt, "eur"),
         "delta": f"{res_amt / base * 100:.1f}% of portfolio", "dir": "flat"},
        {"label": "Default", "value": format_number(dft_amt, "eur"),
         "delta": f"{dft_amt / base * 100:.1f}% of portfolio · 12M {default_rate_12m:.1f}%", "dir": "bad"},
    ], columns=4)

    distressed = projects[projects.status.isin(["Defaulted", "In Recovery", "Restructured"])].copy()

    # ---- deep dive (collapsible): explore the distressed book + recovery detail ----
    with deep_dive("Explore the distressed book · recovery detail per loan"):
        if not distressed.empty:
            with chart_card(deep=True):
                st.markdown('<div class="chart-title">Explore the distressed book</div>'
                            '<div class="chart-sub">Change "Split by" inside the chart · hover for KPIs + top 10 loans</div>',
                            unsafe_allow_html=True)
                kpi_opts = ["Funded €", "Loans", "Avg rate", "Avg LTC"]
                chosen = kpi_opts

                def extra_kpis(table, sub):
                    if not len(sub):
                        return []
                    out = {"Avg rate": f"{sub['interest_rate'].mean():.1f}%", "Avg LTC": f"{sub['ltc'].mean():.0f}%"}
                    return [[k, out[k]] for k in chosen if k in out]

                payload = build_split_payload(
                    PROJECT_DIMS, {"projects": distressed},
                    id_col_by_table={"projects": "project_id"}, name_col_by_table={"projects": "project_name"},
                    value_col_by_table={"projects": "funded_amount"}, fmt="eur", top_label="Top 10 loans", extra_kpis=extra_kpis,
                )
                components_hover.split_explorer(payload, theme, default_dim="Rating", height=520,
                                                panel_title="Segment detail", key="risk_explorer")

        # ---- distressed-loans table with selectable pool + recovery detail ----
        with chart_card(deep=True):
            sel = card_header("Distressed loans — recovery detail",
                              subtitle="Exposure, partial repaid, late payments, collateral, time in recovery · illustrative",
                              options=["In Recovery", "Restructured", "Defaulted"], default="In Recovery",
                              key="risk_pool", label="RiskPool",
                              help="Choose which distressed pool to inspect.")
            d = projects[projects.status == sel].copy()
            if d.empty:
                st.info(f"No {sel.lower()} loans in scope.")
            else:
                d = d.sort_values("funded_amount", ascending=False).head(60)
                rows, fundeds, collaterals = [], [], []
                for r in d.itertuples():
                    rng = np.random.default_rng(_row_seed(r.project_id))
                    funded = float(r.funded_amount)
                    repaid = funded * float(rng.uniform(0.05, 0.45))
                    late_p = funded * float(rng.uniform(0.02, 0.12))
                    late_i = funded * r.interest_rate / 100 * float(rng.uniform(0.10, 0.60))
                    collateral = funded / (r.ltc / 100) if r.ltc else funded
                    fundeds.append(funded); collaterals.append(collateral)
                    row = {"Loan": r.project_name, "Country": r.country, "Rating": r.rating,
                           "Total funded": format_number(funded, "eur"),
                           "Repaid": format_number(repaid, "eur"),
                           "Late princ.": format_number(late_p, "eur"),
                           "Late int.": format_number(late_i, "eur"),
                           "Collateral": format_number(collateral, "eur")}
                    if sel == "In Recovery":
                        if pd.notna(r.default_date):
                            months = (today - pd.Timestamp(r.default_date)).days / 30.44
                            row["Time in recovery"] = f"{months:.0f} mo"
                        else:
                            row["Time in recovery"] = "—"
                    rows.append(row)
                num_cols = {"Repaid", "Late princ.", "Late int."}
                if sel == "In Recovery":
                    num_cols.add("Time in recovery")
                render_table(pd.DataFrame(rows), num_cols=num_cols, badges={"Rating": RATING_BADGE}, rank=True,
                             bar_frac={"Total funded": norm(fundeds), "Collateral": norm(collaterals)},
                             max_height=440, export_name=f"risk_{sel.lower().replace(' ', '_')}")
                st.caption("Partial repaid and late-payment splits are synthesised for illustration · "
                           "collateral value = loan amount ÷ (LTC ÷ 100).")
