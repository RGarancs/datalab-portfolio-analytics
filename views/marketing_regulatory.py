"""Sections ⑦ & ⑧ -- Marketing & Regulatory (rendered as collapsible sections).

Headers only in the original brief; the sub-metrics below are
illustrative -- swap in the real KPI list once Marketing/Compliance define it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, plotly_layout, render_kpi_row
from ui import chart_card, card_header, render_table


def render_marketing(scoped: dict, theme: str, audience: str, today) -> None:
    colors = atelier_colorway(theme)
    rng = np.random.default_rng(11)
    days = pd.date_range(pd.Timestamp(today) - pd.DateOffset(months=6), today, freq="D")
    sessions = np.clip(np.cumsum(rng.normal(0, 40, len(days))) + 900, 200, None)

    render_kpi_row([
        ("Website Sessions / mo", f"{int(sessions[-30:].sum()):,}"),
        ("Visit → Registration", f"{rng.uniform(2, 5):.1f}%"),
        ("Cost / New Investor", f"€{rng.uniform(35, 90):.0f}"),
        ("Activation rate", f"{rng.uniform(40, 70):.1f}%"),
    ], columns=4)

    view = card_header("Website sessions", subtitle="Last 6 months · illustrative",
                       options=["Daily", "Weekly"], default="Daily", key="mkt_grain", label="MktGrain")
    s = pd.Series(sessions, index=days)
    if view == "Weekly":
        s = s.resample("W").mean()
    with chart_card():
        st.caption("Illustrative web traffic, synthetic.")
        fig = go.Figure(go.Scatter(x=s.index, y=s.values, line=dict(color=colors[0], width=2),
                                   fill="tozeroy", fillcolor="rgba(92,92,252,.08)"))
        fig.update_layout(**plotly_layout(theme, height=280, showlegend=False))
        st.plotly_chart(fig, theme=None)

    funnel = pd.DataFrame({
        "Stage": ["Visitors", "Sign-ups", "KYC done", "Funded wallet", "First investment"],
        "Count": [120000, 8600, 7200, 5400, 4100],
    })
    funnel["Conversion"] = (funnel["Count"] / funnel["Count"].iloc[0] * 100).map(lambda v: f"{v:.1f}%")
    funnel["Count"] = funnel["Count"].map(lambda v: f"{v:,}")
    st.markdown("###### Acquisition funnel (illustrative)")
    render_table(funnel, num_cols={"Count", "Conversion"})


def render_regulatory(scoped: dict, theme: str, audience: str, today) -> None:
    rng = np.random.default_rng(13)
    render_kpi_row([
        ("KYC Completion Rate", f"{rng.uniform(88, 99):.1f}%"),
        ("Open AML Flags", f"{int(rng.integers(0, 12))}"),
        ("Upcoming Filings", f"{int(rng.integers(1, 6))}"),
        ("Complaint SLA breaches", f"{int(rng.integers(0, 4))}"),
    ], columns=4)
    reg = pd.DataFrame({
        "Requirement": ["Quarterly regulator report", "AML transaction review", "Investor suitability audit",
                        "Capital adequacy statement", "GDPR data-retention review"],
        "Owner": ["Compliance", "Compliance", "Risk", "Finance", "Legal"],
        "Due": ["2026-07-31", "2026-07-20", "2026-08-15", "2026-09-30", "2026-08-01"],
        "Status": ["On track", "Due soon", "On track", "Not started", "On track"],
    })
    st.markdown("###### Regulatory calendar (illustrative)")
    render_table(reg)
    st.caption("Typical lending-platform regulatory KPIs: KYC/AML completion, upcoming filings, complaint SLA "
               "breaches, capital adequacy. Confirm which apply before wiring real data.")
