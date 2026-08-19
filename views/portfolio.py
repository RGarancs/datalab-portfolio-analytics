"""Topic ① -- Outstanding per portfolio (by status, Bars/Donut), a split explorer
(in-chart "Split by" + hover panel) for the outstanding book, new-volume trend,
and an end status table with data bars + % of total."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import status_colorway, atelier_colorway, plotly_layout, gradient_bars
from metrics import format_number
from ui import chart_card, card_header, render_legend, render_table, norm, column_picker, build_split_payload, deep_dive
from dims import PROJECT_DIMS

def _on_newvol_click() -> None:
    try:
        state = st.session_state.get("newvol_chart")
        pts = state["selection"]["points"] if state else []
        st.session_state["newvol_selected_period"] = str(pts[0]["x"]) if pts else None
    except Exception:
        pass


OUTSTANDING = ["Active", "Available", "Servicing", "Restructured", "In Recovery"]


def render(projects: pd.DataFrame, theme: str, audience: str, split_col: str | None = None) -> None:
    import components_hover

    book = projects[projects.status.isin(OUTSTANDING)]
    if book.empty:
        st.info("No projects match the current filters.")
        return
    scolors = status_colorway(theme)
    present = [s for s in OUTSTANDING if s in book.status.unique()]
    grp = (book.groupby("status").agg(amount=("funded_amount", "sum"), count=("project_id", "count"))
           .reindex(present).fillna(0))
    grp["pct"] = (grp["amount"] / grp["amount"].sum() * 100) if grp["amount"].sum() else 0.0

    with chart_card():
        c_t, c_type, c_unit = st.columns([0.46, 0.28, 0.26], vertical_alignment="center")
        with c_t:
            st.markdown('<div class="chart-title">Book by status</div>'
                        '<div class="chart-sub">Current outstanding book</div>',
                        unsafe_allow_html=True)
        with c_type:
            ctype = st.segmented_control("Chart type", ["Donut", "Bars"], default="Donut",
                                         key="portfolio_ctype", label_visibility="collapsed") or "Donut"
        with c_unit:
            unit = st.segmented_control("Unit", ["€", "#", "%"], default="€", key="portfolio_view_by",
                                        label_visibility="collapsed") or "€"
        values = {"€": grp["amount"], "#": grp["count"], "%": grp["pct"]}[unit]
        col1, col2 = st.columns([1.1, 1], vertical_alignment="center")
        with col1:
            if ctype == "Donut":
                fig = go.Figure(data=[go.Pie(labels=grp.index, values=values, hole=0.64,
                                             marker=dict(colors=[scolors.get(s, "#888") for s in grp.index]),
                                             textinfo="label+percent", sort=False, automargin=True, textfont=dict(size=12),
                                             domain=dict(x=[0.04, 0.96], y=[0.06, 0.94]))])
            else:
                fig = go.Figure(go.Bar(x=grp.index.astype(str), y=values, marker_color=[scolors.get(s, "#888") for s in grp.index],
                                       text=[format_number(v, "eur" if unit == "€" else ("pct" if unit == "%" else "int")) for v in values],
                                       textposition="outside", cliponaxis=False))
                fig.update_yaxes(showticklabels=False)
                gradient_bars(fig)
            fig.update_layout(**plotly_layout(theme, height=360, showlegend=False))
            if ctype == "Donut":
                fig.update_layout(margin=dict(t=24, b=24, l=10, r=10))
            st.plotly_chart(fig, theme=None)
        with col2:
            render_legend([(scolors.get(s, "#888"), s,
                            f'{format_number(grp.loc[s, "amount"], "eur")} · {int(grp.loc[s, "count"])} loans · {grp.loc[s, "pct"]:.1f}%')
                           for s in present])

    # ---- split explorer: outstanding book by any dimension, in-chart switch + hover ----
    with chart_card():
        st.markdown('<div class="chart-title">Explore the outstanding book</div>'
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
            PROJECT_DIMS, {"projects": book},
            id_col_by_table={"projects": "project_id"}, name_col_by_table={"projects": "project_name"},
            value_col_by_table={"projects": "funded_amount"}, fmt="eur", top_label="Top 10 loans", extra_kpis=extra_kpis,
        )
        default_dim = split_col and next((lbl for lbl, (t, c) in PROJECT_DIMS.items() if c == split_col), None)
        components_hover.split_explorer(payload, theme, default_dim=default_dim, height=520,
                                        panel_title="Segment detail", key="outstanding_explorer")

    # ---- deep dive (collapsible): new volume, status split & detail ----
    with deep_dive("New volume, status split & detail"):
        if len(projects):
            with chart_card(deep=True):
                view = card_header("New volume added to book", subtitle="Monthly (12m) · Weekly (52w) · Daily (90d) · Cumulative",
                                   options=["Monthly", "Weekly", "Daily", "Cumulative"], default="Monthly",
                                   key="portfolio_newvol", label="NewVol",
                                   help="Click a bar to see that period's status split below.")
                max_d = projects.start_date.max()
                if view in ("Monthly", "Cumulative"):
                    window = projects[projects.start_date >= max_d - pd.DateOffset(months=12)]
                    period_code, bucket_step = "M", pd.DateOffset(months=1)
                elif view == "Weekly":
                    window = projects[projects.start_date >= max_d - pd.Timedelta(weeks=52)]
                    period_code, bucket_step = "W", pd.Timedelta(weeks=1)
                else:  # Daily
                    window = projects[projects.start_date >= max_d - pd.Timedelta(days=90)]
                    period_code, bucket_step = "D", pd.Timedelta(days=1)

                window = window.copy()
                window["bucket"] = window["start_date"].dt.to_period(period_code).dt.to_timestamp()
                by_bucket = window.groupby("bucket")["funded_amount"].sum().sort_index()
                y = by_bucket.cumsum().values if view == "Cumulative" else by_bucket.values
                fig3 = go.Figure(go.Bar(x=by_bucket.index, y=y, marker_color=atelier_colorway(theme)[0]))
                fig3.update_layout(**plotly_layout(theme, height=260, showlegend=False))
                gradient_bars(fig3)
                st.plotly_chart(fig3, theme=None, key="newvol_chart", on_select=_on_newvol_click, selection_mode="points")

                sel = st.session_state.get("newvol_selected_period")
                if view != "Cumulative" and sel:
                    try:
                        b_start = pd.Timestamp(sel)
                        b_end = b_start + bucket_step
                        period_df = projects[(projects.start_date >= b_start) & (projects.start_date < b_end)]
                    except Exception:
                        period_df = projects.iloc[0:0]
                    st.markdown(f'<div class="chart-sub">Click a bar to inspect that period · '
                                f'showing <b>{b_start.date() if sel else "—"}</b> ({len(period_df)} loans)</div>',
                                unsafe_allow_html=True)
                    if period_df.empty:
                        st.info("No new loans started in that period.")
                    else:
                        pscolors = status_colorway(theme)
                        pgrp = period_df.groupby("status").agg(amount=("funded_amount", "sum"), count=("project_id", "count"))
                        pgrand = float(pgrp["amount"].sum()) or 1.0
                        render_table(
                            pd.DataFrame([{"Status": s, "Funded": format_number(r["amount"], "eur"),
                                           "% period": f"{r['amount']/pgrand*100:.1f}%", "Loans": f"{int(r['count']):,}"}
                                          for s, r in pgrp.iterrows()]),
                            num_cols={"Loans"}, bar_frac={"Funded": norm(pgrp["amount"].tolist()),
                                                           "% period": [v / pgrand for v in pgrp["amount"].tolist()]},
                            export_name="outstanding_period_split",
                        )
                elif view != "Cumulative":
                    st.caption("Click a bar above to see that period's status split here.")

        # ---- end table: status detail with data bars + % total ----
        with chart_card(deep=True):
            card_header("Status detail", subtitle="Euro exposure, loan count, share of book")
            grand = float(grp["amount"].sum()) or 1.0
            rows = [{"Status": s, "Funded": format_number(grp.loc[s, "amount"], "eur"),
                     "% total": f"{grp.loc[s, 'pct']:.1f}%", "Loans": f"{int(grp.loc[s, 'count']):,}"} for s in present]
            rows.append({"Status": "TOTAL", "Funded": format_number(grand, "eur"), "% total": "100.0%",
                         "Loans": f"{int(grp['count'].sum()):,}"})
            render_table(pd.DataFrame(rows), num_cols={"Loans"},
                         bar_frac={"Funded": norm(list(grp["amount"].values) + [0]),
                                   "% total": [v / grand for v in grp["amount"].values] + [1.0]},
                         export_name="outstanding_status_detail")
