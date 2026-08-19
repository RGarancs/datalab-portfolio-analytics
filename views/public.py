"""Public trimmed layout -- the calm, credibility-first view for prospects:
~6 hero numbers, 3 charts (funded volume · status · LTC), and a glossary.
No tabs, no jargon-dense analytics."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, status_colorway, plotly_layout, render_kpi_row, gradient_bars, PALETTES
from metrics import compute_stock, format_number
from ui import chart_card, card_header

GLOSSARY = {
    "Net AROI": "Annualised return on investment, weighted by funded principal, **net of platform fees**.",
    "Default": "A loan is in default when its agreement is terminated after a material breach (e.g. serious payment delay).",
    "Servicing": "Principal recovered from a defaulted loan, typically by enforcing the property collateral.",
    "LTC": "Loan-to-value — the loan amount as a percentage of the property's appraised value at origination.",
    "Net of fees": "Returns are reported after platform fees, weighted by funded principal — no gross headline numbers.",
    "In progress": "Active loans currently paying interest on schedule.",
}


def render(scoped: dict, theme: str, today) -> None:
    projects = scoped["projects"]
    st_all = compute_stock(scoped, pd.Timestamp(today))
    colors = atelier_colorway(theme)

    repaid = projects[projects.status == "Repaid"]
    # ---- hero numbers ----
    render_kpi_row([
        ("Total funded", format_number(st_all["total_funded"], "eur")),
        ("Interest paid (net)", format_number(st_all["interest_paid"], "eur")),
        ("Loans fully repaid", f"{len(repaid):,}"),
        ("Avg. loan term", format_number(st_all["avg_loan_term"], "months")),
    ], columns=4)
    render_kpi_row([
        ("Outstanding portfolio", format_number(st_all["outstanding"], "eur")),
        ("12-month default rate", f"{st_all['default_rate_12m']:.1f}%"),
        ("Avg. LTC", f"{st_all['avg_ltv']:.0f}%"),
        ("Investors", f"{st_all['n_investors']:,}"),
    ], columns=4)

    # ---- chart 1: funded volume over time (teal growth story) ----
    with chart_card():
        card_header("Funded volume over time", subtitle="Cumulative €, since inception")
        funded = projects[projects.status != "Available"].copy()
        m = funded.groupby(funded["start_date"].dt.to_period("M").dt.to_timestamp())["funded_amount"].sum().cumsum()
        fig = go.Figure(go.Scatter(x=m.index, y=m.values, mode="lines",
                                   line=dict(color=colors[0], width=3), fill="tozeroy",
                                   fillcolor="rgba(92,92,252,.10)"))
        fig.update_layout(**plotly_layout(theme, height=320, showlegend=False))
        st.plotly_chart(fig, theme=None)

    c1, c2 = st.columns(2)
    with c1:
        with chart_card():
            card_header("Where every euro sits", subtitle="Portfolio status")
            sc = status_colorway(theme)
            book = projects[projects.status != "Available"]
            g = book.groupby("status")["funded_amount"].sum().sort_values(ascending=False)
            fig = go.Figure(go.Pie(labels=g.index, values=g.values, hole=0.64,
                                   marker=dict(colors=[sc.get(s, "#888") for s in g.index]),
                                   textinfo="label+percent", sort=False, automargin=True, textfont=dict(size=12)))
            fig.update_layout(**plotly_layout(theme, height=300, showlegend=False))
            st.plotly_chart(fig, theme=None)
    with c2:
        with chart_card():
            card_header("LTC distribution", subtitle="Real-estate loans, by LTC band")
            order = ["<50%", "50–65%", "65–75%", "75%+"]
            g = projects.groupby("ltc_band")["funded_amount"].sum().reindex(order).fillna(0)
            fig = go.Figure(go.Bar(x=g.index.astype(str), y=g.values, marker_color=colors[0],
                                   text=[format_number(v, "eur") for v in g.values],
                                   textposition="outside", cliponaxis=False))
            fig.update_layout(**plotly_layout(theme, height=300, showlegend=False))
            fig.update_yaxes(showticklabels=False); gradient_bars(fig)
            st.plotly_chart(fig, theme=None)

    with st.expander("Methodology & glossary"):
        st.markdown("All figures are **synthetic** — this is a demonstration, not a live platform. Returns are reported **net of platform fees**, "
                    "weighted by funded principal. Past performance does not guarantee future returns; capital is at risk.")
        for term, desc in GLOSSARY.items():
            st.markdown(f"**{term}** — {desc}")
