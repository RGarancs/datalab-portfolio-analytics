"""Topic ② -- Cumulative numbers + snapshot cluster. Cumulative line view, or a
Year/Quarter/Month combo chart (funded bars + repaid/defaulted lines). The end
table is a real drill-down matrix: Year -> Quarter -> Month -> Week -> Day,
each level totalled, expand with the "+" on any row."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, plotly_layout, render_kpi_row, gradient_bars, PALETTES, section_header
from metrics import kpi_items, format_number
from ui import chart_card, card_header, render_table, norm, deep_dive

SNAPSHOT_KEYS = ["avg_return", "default_rate_12m", "n_investors", "avg_investment", "avg_ltv", "n_projects"]
GRAN_CODE = {"Per-year": "Y", "Per-quarter": "Q", "Per-month": "M"}


def _cumulative(df, date_col, value_col, index):
    if df.empty:
        return pd.Series(0.0, index=index)
    monthed = df[date_col].dt.to_period("M").dt.to_timestamp()
    return df.groupby(monthed)[value_col].sum().reindex(index, fill_value=0).cumsum()


def _add_gross(repaid: pd.DataFrame) -> pd.DataFrame:
    r = repaid.copy()
    if not r.empty:
        r["gross"] = r["funded_amount"] * (1 + r["interest_rate"] / 100 * r["term_months"] / 12)
    return r


def render(scoped: dict, theme: str, audience: str, today, kpis: dict, window, period: str) -> None:
    projects = scoped["projects"]
    if projects.empty:
        st.info("No projects match the current filters.")
        return

    funded = projects
    repaid = _add_gross(projects[projects.status == "Repaid"])
    defaulted = projects[projects.status == "Defaulted"]
    c = atelier_colorway(theme)

    with chart_card():
        mode = card_header("Cumulative originated vs repaid vs defaulted",
                           subtitle="Since inception · shaded band = selected window",
                           options=["Cumulative", "Per-year", "Per-quarter", "Per-month"], default="Cumulative",
                           key="cum_mode", label="CumMode",
                           help="Running cumulative lines, or a combo chart (funded bars + repaid/defaulted lines) "
                                "by year, quarter or month.")
        if mode == "Cumulative":
            start_month = projects["start_date"].min().to_period("M").to_timestamp()
            index = pd.date_range(start_month, pd.Timestamp(today).to_period("M").to_timestamp(), freq="MS")
            funded_cum = _cumulative(funded, "start_date", "funded_amount", index)
            repaid_cum = _cumulative(repaid, "maturity_date", "funded_amount", index) if not repaid.empty else pd.Series(0.0, index=index)
            defaulted_cum = _cumulative(defaulted, "default_date", "funded_amount", index)
            current_cum = (funded_cum - repaid_cum - defaulted_cum).clip(lower=0)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=index, y=funded_cum.values, name="Originated", line=dict(color=c[0], width=3)))
            fig.add_trace(go.Scatter(x=index, y=current_cum.values, name="Loan book (outstanding)", line=dict(color=c[1], width=3)))
            fig.add_trace(go.Scatter(x=index, y=repaid_cum.values, name="Repaid principal", line=dict(color=c[4], width=3)))
            fig.add_trace(go.Scatter(x=index, y=defaulted_cum.values, name="Defaulted", line=dict(color=c[3], width=2, dash="dot")))
            if period != "Snapshot" and window is not None:
                ws, we = window
                fig.add_vrect(x0=ws, x1=we, fillcolor=PALETTES[theme]["gold"], opacity=0.12, line_width=0)
            fig.update_layout(**plotly_layout(theme, height=390, showlegend=True))
        else:
            code = GRAN_CODE[mode]
            fb = funded.groupby(funded["start_date"].dt.to_period(code))["funded_amount"].sum()
            rb = repaid.groupby(repaid["maturity_date"].dt.to_period(code))["funded_amount"].sum() if not repaid.empty else pd.Series(dtype=float)
            db = defaulted.groupby(defaulted["default_date"].dt.to_period(code))["funded_amount"].sum() if not defaulted.empty else pd.Series(dtype=float)
            all_idx = sorted(set(fb.index) | set(rb.index) | set(db.index))
            fb, rb, db = fb.reindex(all_idx, fill_value=0), rb.reindex(all_idx, fill_value=0), db.reindex(all_idx, fill_value=0)
            # running outstanding book at each period end (= cumulative funded - repaid - defaulted)
            current_line = (fb.cumsum() - rb.cumsum() - db.cumsum()).clip(lower=0)
            xlabels = [str(p) for p in all_idx]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=xlabels, y=fb.values, name="Originated", marker_color=c[0],
                                 text=[format_number(v, "eur") for v in fb.values], textposition="outside", cliponaxis=False))
            fig.add_trace(go.Scatter(x=xlabels, y=current_line.values, name="Loan book (outstanding)",
                                     mode="lines+markers", line=dict(color=c[1], width=3), marker=dict(size=7)))
            fig.add_trace(go.Scatter(x=xlabels, y=rb.values, name="Repaid principal", mode="lines+markers",
                                     line=dict(color=c[4], width=3), marker=dict(size=7)))
            fig.add_trace(go.Scatter(x=xlabels, y=db.values, name="Defaulted", mode="lines+markers",
                                     line=dict(color=c[3], width=2, dash="dot"), marker=dict(size=6)))
            gradient_bars(fig)
            fig.update_layout(**plotly_layout(theme, height=390, showlegend=True))
        st.plotly_chart(fig, theme=None)

    st.markdown("###### Snapshot")
    items, _ = kpi_items(kpis, SNAPSHOT_KEYS, audience)
    render_kpi_row(items, columns=min(3, len(items)) or 1)

    # ---- deep dive (collapsible): funded / repaid / defaulted by period ----
    with deep_dive("Originated vs repaid vs defaulted by origination period"):
        with chart_card(deep=True):
            gran = card_header("By origination period", subtitle="Originated, repaid, defaulted, default rate",
                               options=["By year", "By quarter", "By month"], default="By year",
                               key="cum_table_gran", label="CumTableGran",
                               help="Group the table by year, by quarter (2024Q1) or by month (2024-01).")
            tcode = {"By year": "Y", "By quarter": "Q", "By month": "M"}[gran]
            f_by = funded.groupby(funded["start_date"].dt.to_period(tcode))["funded_amount"].sum()
            r_by = repaid.groupby(repaid["start_date"].dt.to_period(tcode))["funded_amount"].sum() if not repaid.empty else pd.Series(dtype=float)
            d_by = defaulted.groupby(defaulted["start_date"].dt.to_period(tcode))["funded_amount"].sum() if not defaulted.empty else pd.Series(dtype=float)
            periods_idx = sorted(set(f_by.index) | set(r_by.index) | set(d_by.index))
            rows, fvals = [], []
            for pr in periods_idx:
                fv = float(f_by.get(pr, 0)); dv = float(d_by.get(pr, 0))
                fvals.append(fv)
                rows.append({"Period": str(pr), "Originated": format_number(fv, "eur"),
                             "Repaid": format_number(float(r_by.get(pr, 0)), "eur"),
                             "Defaulted": format_number(dv, "eur"),
                             "Default %": f"{(dv/fv*100 if fv else 0):.1f}%"})
            render_table(pd.DataFrame(rows), num_cols={"Repaid", "Defaulted", "Default %"},
                         bar_frac={"Originated": norm(fvals)}, max_height=430, export_name="cumulative_by_period")
