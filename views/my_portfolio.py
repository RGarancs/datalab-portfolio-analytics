"""👤 My Portfolio -- pick an investor and see their holdings, net-of-fees return,
expected income, allocation, and positions (with data bars)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, status_colorway, plotly_layout, render_kpi_row, gradient_bars
from metrics import format_number, PLATFORM_FEE
from ui import chart_card, card_header, render_table, norm, RATING_BADGE, deep_dive


def render(scoped: dict, theme: str, audience: str) -> None:
    investors, investments, projects = scoped["investors"], scoped["investments"], scoped["projects"]
    colors = atelier_colorway(theme)
    if investments.empty or investors.empty:
        st.info("No investor positions in scope.")
        return

    # default to the largest investor by invested capital
    totals = investments.groupby("investor_id")["amount"].sum().sort_values(ascending=False)
    names = investors.set_index("investor_id")["name"]
    options = [i for i in totals.index if i in names.index][:200]

    with chart_card():
        hl, hr = st.columns([0.62, 0.38], vertical_alignment="center")
        with hl:
            st.markdown('<div class="chart-title">My portfolio</div>'
                        '<div class="chart-sub">Pick an investor to see their book (demo · synthetic)</div>',
                        unsafe_allow_html=True)
        with hr:
            inv_id = st.selectbox("Investor", options, format_func=lambda i: f"{names.get(i, i)}",
                                  key="myportfolio_investor", label_visibility="collapsed")

    me = investors[investors.investor_id == inv_id].iloc[0]
    pos = investments[investments.investor_id == inv_id].merge(
        projects[["project_id", "project_name", "loan_category", "status", "rating", "interest_rate",
                  "term_months", "maturity_date"]], on="project_id", how="left")
    invested = float(pos["amount"].sum())
    n_pos = int(pos["project_id"].nunique())
    aroi = float((pos["interest_rate"] * pos["amount"]).sum() / max(pos["amount"].sum(), 1)) * (1 - PLATFORM_FEE)
    exp_income = invested * aroi / 100
    avg_term = float((pos["term_months"] * pos["amount"]).sum() / max(pos["amount"].sum(), 1))
    active_val = float(pos.loc[pos.status.isin(["Active", "Servicing", "Restructured", "In Recovery"]), "amount"].sum())

    render_kpi_row([
        {"label": "Invested", "value": format_number(invested, "eur"), "delta": None, "dir": "none"},
        {"label": "Available wallet", "value": format_number(float(me["wallet_balance"]), "eur"), "delta": None, "dir": "none"},
        {"label": "Avg. loan term", "value": format_number(avg_term, "months"), "delta": None, "dir": "none"},
        {"label": "Est. annual income", "value": format_number(exp_income, "eur"), "delta": None, "dir": "none"},
    ], columns=4)

    c1, c2 = st.columns(2)
    with c1:
        with chart_card():
            top_l, top_r = st.columns([0.5, 0.5], vertical_alignment="center")
            with top_l:
                mode = st.segmented_control("Split", ["Status", "Rating", "Category"], default="Status",
                                            key="myport_alloc", label_visibility="collapsed",
                                            help="Break the portfolio down by status, rating or category.") or "Status"
            with top_r:
                ctype = st.segmented_control("Chart type", ["Donut", "Bars"], default="Donut",
                                             key="myport_ctype", label_visibility="collapsed") or "Donut"
            st.markdown('<div class="chart-title">Allocation</div><div class="chart-sub">Share of invested €</div>',
                       unsafe_allow_html=True)
            dim = {"Status": "status", "Rating": "rating", "Category": "loan_category"}[mode]
            alloc = pos.groupby(dim)["amount"].sum().sort_values(ascending=False)
            cmap = status_colorway(theme) if dim == "status" else None
            marker = dict(colors=[cmap.get(s, "#888") for s in alloc.index]) if cmap else dict(
                colors=[colors[i % len(colors)] for i in range(len(alloc))])
            if ctype == "Donut":
                fig = go.Figure(go.Pie(labels=alloc.index.astype(str), values=alloc.values, hole=0.62,
                                       marker=marker, textinfo="label+percent", sort=False, automargin=True, textfont=dict(size=12)))
            else:
                bar_colors = marker["colors"]
                fig = go.Figure(go.Bar(x=alloc.index.astype(str), y=alloc.values, marker_color=bar_colors,
                                       text=[format_number(v, "eur") for v in alloc.values],
                                       textposition="outside", cliponaxis=False))
                fig.update_yaxes(showticklabels=False); gradient_bars(fig)
            fig.update_layout(**plotly_layout(theme, height=300, showlegend=False))
            st.plotly_chart(fig, theme=None)
    with c2:
        with chart_card():
            card_header("Position status", subtitle="Active vs returned vs distressed")
            st.metric("Active capital", format_number(active_val, "eur"))
            st.metric("Returned", format_number(float(pos.loc[pos.status == "Repaid", "amount"].sum()), "eur"))
            st.metric("Positions", f"{n_pos:,}")

    with deep_dive("Every stake this investor holds"):
        with chart_card(deep=True):
            card_header("Positions", subtitle="Every stake this investor holds")
            pv = pos.sort_values("amount", ascending=False).copy()
            rows = [{"Project": r.project_name, "Category": r.loan_category, "Rating": r.rating, "Status": r.status,
                     "Invested": format_number(r.amount, "eur"), "Rate": f"{r.interest_rate:.1f}%",
                     "Maturity": pd.Timestamp(r.maturity_date).strftime("%Y-%m") if pd.notna(r.maturity_date) else "—"}
                    for r in pv.itertuples()]
            render_table(pd.DataFrame(rows), num_cols={"Rate"}, badges={"Rating": RATING_BADGE}, rank=True,
                         bar_frac={"Invested": norm(pv["amount"].tolist())}, export_name="my_portfolio_positions")
