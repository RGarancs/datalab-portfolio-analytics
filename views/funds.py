"""Topic ④ -- Available funds: net deposits (cumulative / monthly / rolling-30d,
each with a proper damped-trend forecast), pipeline requirement, a repayment
composition chart over TIME (stacked columns), and an open-pipeline table that
scrolls within its card to reveal the top 100 by remaining requirement."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, plotly_layout, gradient_bars, render_kpi_row, section_header, PALETTES
from metrics import format_number
from ui import chart_card, card_header, render_table, norm, RATING_BADGE, deep_dive


def _holt_damped_forecast(y: np.ndarray, periods: int, alpha: float = 0.45, beta: float = 0.25,
                          phi: float = 0.97) -> np.ndarray:
    """Holt's linear trend method with a damped trend (Gardner & McKenzie) --
    tracks the recent trend instead of repeating a flat average, and tapers
    off for longer horizons instead of diverging in a straight line forever.
    Standard, dependency-free short-term forecasting method."""
    y = np.asarray(y, dtype=float)
    if len(y) == 0:
        return np.zeros(periods)
    if len(y) < 2:
        return np.full(periods, float(y[-1]))
    level, trend = float(y[0]), float(y[1] - y[0])
    for i in range(1, len(y)):
        last_level = level
        level = alpha * y[i] + (1 - alpha) * (level + phi * trend)
        trend = beta * (level - last_level) + (1 - beta) * phi * trend
    out, cum_phi, p = [], 0.0, 1.0
    for _ in range(periods):
        p *= phi
        cum_phi += p
        out.append(level + cum_phi * trend)
    return np.array(out)


def render(scoped: dict, theme: str, audience: str, today, base=None) -> None:
    tx, projects = scoped["transactions"], scoped["projects"]
    # repayment schedule is a whole-book view -> use the as-of book, not the time window
    rep_projects = base["projects"] if base is not None else projects
    colors = atelier_colorway(theme)
    today = pd.Timestamp(today)

    net_series = pd.Series(dtype=float)
    monthly_net = pd.Series(dtype=float)
    if not tx.empty:
        t = tx.copy(); t["month"] = t["date"].dt.to_period("M").dt.to_timestamp()
        monthly_net = t.groupby("month")["amount"].sum()
        idx = pd.date_range(monthly_net.index.min(), today.to_period("M").to_timestamp(), freq="MS")
        monthly_net = monthly_net.reindex(idx, fill_value=0)
        net_series = monthly_net.cumsum()

    open_book = projects[projects.status.isin(["Available", "Servicing"])]
    requirement = float((open_book["funding_target"] - open_book["funded_amount"]).clip(lower=0).sum())
    avg_price = (float(np.average(open_book["interest_rate"], weights=open_book["funded_amount"].clip(lower=1)))
                 if len(open_book) else 0.0)

    with chart_card():
        view = card_header("Net deposits", subtitle="Investor wallet funding · every view includes a forecast",
                           options=["Cumulative", "Monthly", "Rolling 30d"], default="Cumulative",
                           key="funds_view", label="FundsView",
                           help="Cumulative balance, monthly net flow, or the last 90 days daily -- each with a "
                                "damped-trend forecast (Holt's linear method) rather than a flat repeated average.")
        if tx.empty:
            st.info("Not enough wallet activity in range.")
        elif view == "Rolling 30d":
            daily = tx.copy(); daily["d"] = daily["date"].dt.normalize()
            dnet = daily.groupby("d")["amount"].sum()
            didx = pd.date_range(today - pd.Timedelta(days=89), today, freq="D")
            dnet = dnet.reindex(didx, fill_value=0)
            train = dnet.tail(45).values  # 45-day training window for a steadier trend estimate
            fut_vals = _holt_damped_forecast(train, 15)
            fut_idx = pd.date_range(today + pd.Timedelta(days=1), periods=15, freq="D")
            plot_idx = dnet.tail(30)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=plot_idx.index, y=plot_idx.values, name="Daily net (last 30d)", marker_color=colors[0]))
            fig.add_trace(go.Scatter(x=[plot_idx.index[-1], *fut_idx], y=[plot_idx.values[-1], *fut_vals],
                                     name="Forecast (damped trend)", line=dict(color=colors[1], width=2, dash="dash"),
                                     mode="lines+markers", marker=dict(size=5)))
            fig.update_layout(**plotly_layout(theme, height=340))
            gradient_bars(fig)
            st.plotly_chart(fig, theme=None)
            st.caption(f"Trained on the last 45 days · forecasting the next 15 days · "
                       f"next-day estimate {format_number(float(fut_vals[0]), 'eur')}.")
        elif view == "Monthly":
            fut_vals = _holt_damped_forecast(monthly_net.tail(9).values, 4) if len(monthly_net) >= 2 else np.zeros(4)
            fut_idx = pd.date_range(monthly_net.index.max() + pd.DateOffset(months=1), periods=4, freq="MS")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly_net.index, y=monthly_net.values, name="Monthly net", marker_color=colors[0]))
            fig.add_trace(go.Bar(x=fut_idx, y=fut_vals, name="Forecast (damped trend)", marker_color=colors[1],
                                 marker_pattern_shape="/", opacity=0.75))
            fig.update_layout(**plotly_layout(theme, height=350)); gradient_bars(fig)
            st.plotly_chart(fig, theme=None)
        else:  # Cumulative
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=net_series.index, y=net_series.values, name="Net deposits",
                                     line=dict(color=colors[0], width=3)))
            if len(monthly_net) >= 2:
                fut_flow = _holt_damped_forecast(monthly_net.tail(9).values, 6)
                fut_idx = pd.date_range(net_series.index.max() + pd.DateOffset(months=1), periods=6, freq="MS")
                fut_level = net_series.iloc[-1] + np.cumsum(fut_flow)
                fig.add_trace(go.Scatter(x=[net_series.index[-1], *fut_idx], y=[net_series.iloc[-1], *fut_level],
                                         name="Forecast (damped trend)", line=dict(color=colors[1], width=2, dash="dash")))
            fig.update_layout(**plotly_layout(theme, height=350))
            st.plotly_chart(fig, theme=None)

    render_kpi_row([
        ("Net Deposits (available)", format_number(net_series.iloc[-1] if len(net_series) else 0.0, "eur")),
        ("Pipeline Requirement", format_number(requirement, "eur")),
        ("Avg. Price / Interest (open)", format_number(avg_price, "pct")),
        ("Open loans", f"{len(open_book):,}"),
    ], columns=4)

    # ---- repayment composition over time: history -> TODAY -> scheduled future ----
    OUTSTANDING = ["Active", "Servicing", "Restructured", "In Recovery"]
    book = rep_projects[rep_projects["maturity_date"].notna()
                        & rep_projects.status.isin(["Repaid"] + OUTSTANDING)].copy()
    if len(book):
        with chart_card():
            card_header("Repayment composition — history & schedule",
                        subtitle="Principal vs interest by month · last 12 months realised (left of Today) + scheduled future (right) · illustrative")
            book["principal"] = book["funded_amount"]
            book["interest"] = book["funded_amount"] * book["interest_rate"] / 100 * book["term_months"] / 12
            book["month"] = book["maturity_date"].dt.to_period("M").dt.to_timestamp()
            today_m = today.to_period("M").to_timestamp()
            hist_from = (today - pd.DateOffset(months=12)).to_period("M").to_timestamp()  # last 12 months of history
            hist = book[(book["month"] <= today_m) & (book["month"] >= hist_from)].groupby("month")[["principal", "interest"]].sum().sort_index()
            fut = book[book["month"] > today_m].groupby("month")[["principal", "interest"]].sum().sort_index()
            fig = go.Figure()
            if len(hist):
                fig.add_trace(go.Bar(x=hist.index, y=hist["principal"], name="Principal (realised)", marker_color=colors[2]))
                fig.add_trace(go.Bar(x=hist.index, y=hist["interest"], name="Interest (realised)", marker_color=colors[1]))
            if len(fut):
                fig.add_trace(go.Bar(x=fut.index, y=fut["principal"], name="Principal (scheduled)",
                                     marker_color=colors[2], marker_pattern_shape="/", opacity=0.7))
                fig.add_trace(go.Bar(x=fut.index, y=fut["interest"], name="Interest (scheduled)",
                                     marker_color=colors[1], marker_pattern_shape="/", opacity=0.7))
            fig.update_layout(barmode="stack", **plotly_layout(theme, height=320))
            fig.add_vline(x=today_m, line_width=2, line_dash="dash", line_color=PALETTES[theme]["gold"])
            fig.add_annotation(x=today_m, y=1.0, yref="paper", text="Today", showarrow=False,
                               font=dict(color=PALETTES[theme]["gold"], size=12), yanchor="bottom")
            st.plotly_chart(fig, theme=None)

    # ---- deep dive (collapsible): open pipeline ----
    with deep_dive("Every open loan still raising · remaining requirement"):
        with chart_card(deep=True):
            card_header("Open pipeline", subtitle="Loans still raising · remaining requirement · scroll for more")
            if open_book.empty:
                st.info("No open (Available / Servicing) loans in scope.")
            else:
                ob = open_book.copy()
                ob["req"] = (ob["funding_target"] - ob["funded_amount"]).clip(lower=0)
                ob["pct"] = (ob["funded_amount"] / ob["funding_target"].clip(lower=1) * 100).clip(0, 100)
                obr = ob.sort_values("req", ascending=False).head(100)
                rows = [{"Project": r.project_name, "Country": r.country, "Rating": r.rating,
                         "Target": format_number(r.funding_target, "eur"), "Funded %": f"{r.pct:.0f}%",
                         "Requirement": format_number(r.req, "eur"), "Rate": f"{r.interest_rate:.1f}%"} for r in obr.itertuples()]
                render_table(pd.DataFrame(rows), num_cols={"Target", "Rate"}, badges={"Rating": RATING_BADGE},
                             bar_frac={"Requirement": norm(obr["req"].tolist()), "Funded %": [v / 100 for v in obr["pct"].tolist()]},
                             max_height=430, rank=True, export_name="funds_open_pipeline")
                st.caption(f"Showing top {len(obr)} of {len(ob):,} open loans by remaining requirement.")
