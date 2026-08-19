"""Section ⑨ -- Further analytics: concentration (HHI), expected loss,
realised-vs-expected recovery, funding velocity, investor retention/repeat/churn,
weighted-average life, a combined cash-flow forecast, maturity ladder, yield-vs-risk,
and a concentration detail table. All illustrative on synthetic data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, plotly_layout, gradient_bars, PALETTES
from metrics import format_number
from ui import chart_card, card_header, render_table, norm

PD_BY_RATING = {"A": 0.01, "B": 0.03, "C": 0.06, "D": 0.10, "E": 0.16}
LGD = 0.55
OUTSTANDING = ["Servicing", "Active", "Restructured", "In Recovery"]
CONC_DIMS = {"Borrower": "client_id", "Country": "country", "Type": "project_type", "Project": "group_id"}
AXES = {"LTC": ("ltc", "LTC %"), "Term": ("term_months", "Term (months)"), "Rating→PD": ("_pd", "PD (rating)")}


def _rating_colors(theme):
    p = PALETTES[theme]
    return {"A": p["pos"], "B": p["voice"], "C": p["gold"], "D": "#c98a2c", "E": p["neg"]}


def render(scoped: dict, theme: str, audience: str, today) -> None:
    projects = scoped["projects"]
    if projects.empty:
        st.info("No projects match the current filters.")
        return
    colors = atelier_colorway(theme)
    today = pd.Timestamp(today)
    funded = projects[projects.funded_amount > 0]
    outstanding_book = projects[projects.status.isin(OUTSTANDING)]
    investors, investments = scoped["investors"], scoped["investments"]

    st.caption("Further views — all on synthetic data.")

    # ---- Concentration ----
    with chart_card():
        dim_label = card_header("Concentration risk", subtitle="HHI + top-10 share",
                                options=list(CONC_DIMS.keys()), default="Borrower", key="conc_dim", label="ConcDim",
                                help="Herfindahl index + top-10 share by the chosen dimension.")
        col = CONC_DIMS[dim_label]
        g = funded.groupby(col)["funded_amount"].sum().sort_values(ascending=False)
        total = float(g.sum()) or 1.0
        shares = g / total
        hhi = float((shares ** 2).sum() * 10000)
        top10 = float(shares.head(10).sum() * 100)
        verdict = "well diversified" if hhi < 1000 else "moderately concentrated" if hhi < 2500 else "highly concentrated"
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.metric("HHI (0–10,000)", f"{hhi:,.0f}", help="Sum of squared shares ×10,000. <1,000 diversified.")
            st.metric("Top-10 share", f"{top10:.1f}%")
            st.caption(f"By {dim_label.lower()}: **{verdict}**.")
            conc_type = st.segmented_control("Chart type", ["Bars", "Donut"], default="Bars",
                                             key="conc_ctype", help="Switch the top-10 chart between bars and a donut.")
        with c2:
            topn = g.head(10)
            if conc_type == "Donut":
                fig = go.Figure(go.Pie(labels=topn.index.astype(str), values=topn.values, hole=0.6, sort=False,
                                       marker=dict(colors=[colors[i % len(colors)] for i in range(len(topn))]),
                                       textinfo="label+percent", automargin=True, textfont=dict(size=11)))
            else:
                fig = go.Figure(go.Bar(x=(topn / total * 100).values, y=topn.index.astype(str), orientation="h",
                                       marker_color=colors[0], text=[f"{v/total*100:.1f}%" for v in topn.values],
                                       textposition="outside", cliponaxis=False, textfont=dict(size=11)))
                fig.update_xaxes(showticklabels=False); fig.update_yaxes(autorange="reversed"); gradient_bars(fig)
            fig.update_layout(**plotly_layout(theme, height=340, showlegend=False))
            st.plotly_chart(fig, theme=None)

    # ---- Expected loss (internal / investor only) ----
    if audience != "Public Website":
        with chart_card():
            card_header("Expected loss", subtitle="EL = PD(rating) × LGD × outstanding · illustrative")
            ob = outstanding_book.copy()
            ob["pd"] = ob["rating"].map(PD_BY_RATING).fillna(0.08)
            ob["el"] = ob["pd"] * LGD * ob["funded_amount"]
            ead = float(ob["funded_amount"].sum()) or 1.0
            by_rating = ob.groupby("rating")["el"].sum().reindex(list("ABCDE")).fillna(0)
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.metric("Expected loss (12m)", format_number(float(ob["el"].sum()), "eur"))
                st.metric("EL / outstanding", f"{ob['el'].sum()/ead*100:.2f}%")
                st.caption(f"Assumes LGD = {LGD:.0%} for illustration.")
            with c2:
                rc = _rating_colors(theme)
                fig = go.Figure(go.Bar(x=by_rating.index, y=by_rating.values,
                                       marker_color=[rc.get(r, colors[0]) for r in by_rating.index],
                                       text=[format_number(v, "eur") for v in by_rating.values],
                                       textposition="outside", cliponaxis=False, textfont=dict(size=11)))
                fig.update_layout(**plotly_layout(theme, height=300, showlegend=False)); fig.update_yaxes(showticklabels=False); gradient_bars(fig)
                st.plotly_chart(fig, theme=None)

    # ---- Realised vs expected recovery on defaults ----
    with chart_card():
        card_header("Recovery — realised vs expected", subtitle="On defaulted / in-recovery loans · illustrative")
        distressed = projects[projects.status.isin(["Defaulted", "In Recovery"])].copy()
        if distressed.empty:
            st.info("No distressed loans in scope.")
        else:
            rng = np.random.default_rng(7)
            distressed = distressed.sort_values("project_id")
            distressed["expected_rec"] = 0.90  # target recovery rate
            distressed["realised_rec"] = np.clip(rng.normal(0.91, 0.10, len(distressed)), 0.3, 1.0)
            w = distressed["funded_amount"]
            exp_rate = float(np.average(distressed["expected_rec"], weights=w)) * 100
            real_rate = float(np.average(distressed["realised_rec"], weights=w)) * 100
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.metric("Realised recovery", f"{real_rate:.1f}%", delta=f"{real_rate-exp_rate:+.1f} pp vs expected")
                st.metric("Recovered principal", format_number(float((distressed['realised_rec']*w).sum()), "eur"))
            with c2:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=["Expected", "Realised"], y=[exp_rate, real_rate],
                                     marker_color=[colors[2], colors[4]],
                                     text=[f"{exp_rate:.1f}%", f"{real_rate:.1f}%"], textposition="outside", cliponaxis=False))
                fig.update_layout(**plotly_layout(theme, height=280, showlegend=False)); gradient_bars(fig)
                st.plotly_chart(fig, theme=None)

    # ---- Funding velocity (days listing -> funded) ----
    with chart_card():
        vby = card_header("Funding velocity", subtitle="Days from listing to fully funded",
                          options=["Rating", "Type", "Category"], default="Rating", key="velo_by", label="VeloBy",
                          help="How fast loans fill, by rating / project type / loan category.")
        vf = funded[funded["funding_end_date"].notna()].copy()
        if vf.empty:
            st.info("No funded loans with a close date in scope.")
        else:
            vf["days"] = (vf["funding_end_date"] - vf["start_date"]).dt.days.clip(lower=0)
            dim = {"Rating": "rating", "Type": "project_type", "Category": "loan_category"}[vby]
            gv = vf.groupby(dim)["days"].mean().sort_values()
            st.metric("Avg. days to fund", f"{vf['days'].mean():.0f} days")
            fig = go.Figure(go.Bar(x=gv.index.astype(str), y=gv.values, marker_color=colors[0],
                                   text=[f"{v:.0f}d" for v in gv.values], textposition="outside", cliponaxis=False))
            fig.update_layout(**plotly_layout(theme, height=300, showlegend=False)); gradient_bars(fig)
            st.plotly_chart(fig, theme=None)

    # ---- Investor retention / repeat / churn ----
    with chart_card():
        card_header("Investor retention", subtitle="Repeat-rate, churn (inactive >90d), cohort activity")
        if investments.empty or investors.empty:
            st.info("No investor activity in scope.")
        else:
            per_inv = investments.groupby("investor_id")["investment_id"].count()
            repeat_rate = float((per_inv >= 2).mean() * 100)
            churn = float((investors["last_login"] < today - pd.Timedelta(days=90)).mean() * 100)
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.metric("Repeat investor rate", f"{repeat_rate:.1f}%", help="Share of investors with ≥2 investments.")
                st.metric("Churn (inactive >90d)", f"{churn:.1f}%")
                st.metric("Avg. investments / investor", f"{per_inv.mean():.1f}")
            with c2:
                inv = investors.copy()
                inv["cohort"] = inv["registration_date"].dt.year
                inv["active90"] = inv["last_login"] >= today - pd.Timedelta(days=90)
                coh = inv.groupby("cohort")["active90"].mean() * 100
                fig = go.Figure(go.Bar(x=coh.index.astype(str), y=coh.values, marker_color=colors[0],
                                       text=[f"{v:.0f}%" for v in coh.values], textposition="outside", cliponaxis=False))
                fig.update_layout(**plotly_layout(theme, height=280, showlegend=False)); gradient_bars(fig)
                fig.update_yaxes(title_text="% active (last 90d)")
                st.plotly_chart(fig, theme=None)

    # ---- Weighted-average life / duration ----
    with chart_card():
        card_header("Weighted-average life", subtitle="Principal-weighted months to maturity (outstanding book)")
        ob = outstanding_book[outstanding_book["maturity_date"] > today].copy()
        if ob.empty:
            st.info("No outstanding loans with a future maturity in scope.")
        else:
            ob["ttm"] = (ob["maturity_date"] - today).dt.days / 30.44
            wal = float(np.average(ob["ttm"], weights=ob["funded_amount"]))
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.metric("Weighted-avg. life", f"{wal:.1f} months")
                st.metric("Outstanding (future mat.)", format_number(float(ob["funded_amount"].sum()), "eur"))
            with c2:
                bins = [0, 3, 6, 12, 24, 999]; labs = ["<3m", "3–6m", "6–12m", "12–24m", "24m+"]
                ob["b"] = pd.cut(ob["ttm"], bins=bins, labels=labs, include_lowest=True)
                bb = ob.groupby("b", observed=True)["funded_amount"].sum()
                fig = go.Figure(go.Bar(x=bb.index.astype(str), y=bb.values, marker_color=colors[2],
                                       text=[format_number(v, "eur") for v in bb.values], textposition="outside", cliponaxis=False))
                fig.update_layout(**plotly_layout(theme, height=280, showlegend=False)); fig.update_yaxes(showticklabels=False); gradient_bars(fig)
                st.plotly_chart(fig, theme=None)

    # ---- Combined cash-flow forecast ----
    with chart_card():
        card_header("Cash-flow forecast", subtitle="Repayment inflows vs new-funding outflows · next 12 months · illustrative")
        ob = outstanding_book[outstanding_book["maturity_date"] > today].copy()
        horizon = pd.date_range(today.to_period("M").to_timestamp() + pd.DateOffset(months=1), periods=12, freq="MS")
        inflow = pd.Series(0.0, index=horizon)
        if not ob.empty:
            ob["gross"] = ob["funded_amount"] * (1 + ob["interest_rate"] / 100 * ob["term_months"] / 12)
            ob["mm"] = ob["maturity_date"].dt.to_period("M").dt.to_timestamp()
            g = ob.groupby("mm")["gross"].sum()
            inflow = g.reindex(horizon, fill_value=0)
        open_book = projects[projects.status.isin(["Available", "Servicing"])]
        requirement = float((open_book["funding_target"] - open_book["funded_amount"]).clip(lower=0).sum())
        outflow = pd.Series(0.0, index=horizon)
        outflow.iloc[:6] = requirement / 6.0   # deploy pipeline requirement over 6 months
        net = inflow.values - outflow.values
        fig = go.Figure()
        fig.add_trace(go.Bar(x=horizon, y=inflow.values, name="Repayment inflows", marker_color=colors[4]))
        fig.add_trace(go.Bar(x=horizon, y=-outflow.values, name="Funding outflows", marker_color=colors[3]))
        fig.add_trace(go.Scatter(x=horizon, y=net, name="Net", line=dict(color=colors[1], width=3)))
        fig.update_layout(barmode="relative", **plotly_layout(theme, height=340)); gradient_bars(fig)
        st.plotly_chart(fig, theme=None)

    # ---- Maturity ladder ----
    with chart_card():
        horizon_label = card_header("Maturity ladder", subtitle="Principal maturing per month",
                                    options=["12m", "18m", "24m"], default="18m", key="ladder_h", label="Horizon",
                                    help="How far ahead to show scheduled principal repayments.")
        months = {"12m": 12, "18m": 18, "24m": 24}[horizon_label]
        fut = outstanding_book[outstanding_book.maturity_date > today].copy()
        if fut.empty:
            st.info("No upcoming maturities in scope.")
        else:
            fut["m"] = fut["maturity_date"].dt.to_period("M").dt.to_timestamp()
            ladder = fut.groupby("m")["funded_amount"].sum().sort_index()
            ladder = ladder[ladder.index <= today.to_period("M").to_timestamp() + pd.DateOffset(months=months)]
            fig = go.Figure(go.Bar(x=ladder.index, y=ladder.values, marker_color=colors[2]))
            fig.update_layout(**plotly_layout(theme, height=300, showlegend=False)); gradient_bars(fig)
            st.plotly_chart(fig, theme=None)

    # ---- Yield vs risk ----
    with chart_card():
        xlabel = card_header("Yield vs risk", subtitle="Interest rate vs risk · bubble = funded € · colour = rating",
                             options=list(AXES.keys()), default="LTC", key="scatter_x", label="ScatterX",
                             help="Choose the risk axis: LTC, term, or rating-implied PD.")
        if funded.empty:
            st.info("No funded projects in scope.")
        else:
            fd = funded.copy(); fd["_pd"] = fd["rating"].map(PD_BY_RATING).fillna(0.08) * 100
            xcol, xtitle = AXES[xlabel]; rc = _rating_colors(theme)
            fig = go.Figure()
            for r in list("ABCDE"):
                d = fd[fd.rating == r]
                if d.empty:
                    continue
                fig.add_trace(go.Scatter(x=d[xcol], y=d["interest_rate"], mode="markers", name=f"Rating {r}",
                                         marker=dict(size=(d["funded_amount"] / d["funded_amount"].max() * 26 + 6),
                                                     color=rc.get(r, colors[0]), opacity=0.75, line=dict(width=0)),
                                         hovertext=d["project_name"]))
            lay = plotly_layout(theme, height=380); lay["hovermode"] = "closest"
            fig.update_layout(**lay); fig.update_xaxes(title_text=xtitle); fig.update_yaxes(title_text="Interest rate %")
            st.plotly_chart(fig, theme=None)

    # ---- end table: concentration detail ----
    with chart_card():
        card_header("Concentration detail", subtitle=f"Top 10 by {dim_label.lower()} · share + cumulative %")
        topn = g.head(10); cum = 0.0; rows, fvals = [], []
        for name, v in topn.items():
            share = v / total * 100; cum += share; fvals.append(float(v))
            rows.append({dim_label: str(name), "Funded": format_number(float(v), "eur"),
                         "Share": f"{share:.1f}%", "Cumulative": f"{cum:.1f}%"})
        rest_v = float(total - topn.sum())
        if rest_v > 0:
            fvals.append(0)
            rows.append({dim_label: f"Other ({g.shape[0]-len(topn)})", "Funded": format_number(rest_v, "eur"),
                         "Share": f"{rest_v/total*100:.1f}%", "Cumulative": "100.0%"})
        render_table(pd.DataFrame(rows), num_cols={"Share", "Cumulative"}, bar_frac={"Funded": norm(fvals)}, rank=True)
