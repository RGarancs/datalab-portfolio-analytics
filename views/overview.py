"""Overview tab -- investor pipeline boxes, and the unified split explorer:
one chart with an in-chart "Split by" dropdown (client-side, no rerun),
Bars/Donut toggle, and a hover panel showing selectable KPIs + a top-10 list.
A plain click-to-focus chart + summary table follow."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import atelier_colorway, plotly_layout, render_kpi_row, gradient_bars
from metrics import format_number, pipeline_counts, project_pipeline_counts
from ui import chart_card, card_header, render_legend, render_table, norm, column_picker, build_split_payload
from dims import SPLIT_DIMS


def _on_bar_click() -> None:
    try:
        state = st.session_state.get("overview_split_chart")
        pts = state["selection"]["points"] if state else []
        st.session_state["focus_value"] = str(pts[0]["x"]) if pts else "All"
    except Exception:
        pass


def render_pipeline(investors: pd.DataFrame, investments: pd.DataFrame, as_of, theme: str) -> None:
    """Registered → Identified → Active funnel + avg investment, with a growth toggle."""
    with chart_card():
        mode = card_header("Investor pipeline", subtitle="Registered → Identified (KYC) → Active (funded wallet)",
                           options=["vs last day", "vs last month", "vs 12M"], default="vs last month",
                           key="pipeline_growth", label="PipeGrowth", help="Reference period for the growth delta.")
        as_of = pd.Timestamp(as_of)
        ref_date = {"vs last day": as_of - pd.Timedelta(days=1),
                    "vs last month": as_of - pd.DateOffset(months=1),
                    "vs 12M": as_of - pd.DateOffset(months=12)}[mode]
        now = pipeline_counts(investors, as_of)
        ref = pipeline_counts(investors, ref_date)
        iv = investments[investments["invested_date"] <= as_of]
        avg_inv = float(iv["amount"].mean()) if len(iv) else 0.0

        items = []
        for k in ["Registered", "Identified", "Active"]:
            d = now[k] - ref[k]
            pct = (d / ref[k] * 100) if ref[k] else 0.0
            items.append({"label": k, "value": f"{now[k]:,}",
                          "delta": f"{'+' if d >= 0 else '−'}{abs(d):,} · {pct:+.1f}%",
                          "dir": "good" if d > 0 else "flat" if d == 0 else "bad"})
        items.append({"label": "Avg. investment", "value": format_number(avg_inv, "eur"), "delta": None, "dir": "none"})
        render_kpi_row(items, columns=4)


def render_project_pipeline(projects: pd.DataFrame, as_of, theme: str) -> None:
    """Total → Active → Servicing project funnel + avg project size, with the same
    growth-reference toggle (top-right) as the investor pipeline above it."""
    with chart_card():
        mode = card_header("Project pipeline", subtitle="Total → Active → Servicing funds",
                           options=["vs last day", "vs last month", "vs 12M"], default="vs last month",
                           key="proj_pipeline_growth", label="ProjGrowth",
                           help="Reference period for the growth delta.")
        as_of = pd.Timestamp(as_of)
        ref_date = {"vs last day": as_of - pd.Timedelta(days=1),
                    "vs last month": as_of - pd.DateOffset(months=1),
                    "vs 12M": as_of - pd.DateOffset(months=12)}[mode]
        now = project_pipeline_counts(projects, as_of, "Stages")
        ref = project_pipeline_counts(projects, ref_date, "Stages")

        items = []
        for k in ["Total", "Active", "Servicing"]:
            d = now[k] - ref[k]
            pct = (d / ref[k] * 100) if ref[k] else 0.0
            items.append({"label": f"{k} projects", "value": f"{now[k]:,}",
                          "delta": f"{'+' if d >= 0 else '−'}{abs(d):,} · {pct:+.1f}%",
                          "dir": "good" if d > 0 else "flat" if d == 0 else "bad"})
        items.append({"label": "Avg. project size", "value": format_number(now["avg_size"], "eur"),
                      "delta": None, "dir": "none"})
        render_kpi_row(items, columns=4)


def render(scoped: dict, theme: str, audience: str, split_label: str, split_col: str, split_table: str) -> None:
    """Plain (server-rendered) split chart used for click-to-focus, plus the
    split summary table. The rich hover version lives in render_hover_explorer.
    The "Split by" selector here is the SAME dimension used everywhere else in
    the app (sidebar included) -- changing it here updates it everywhere, so
    click-to-focus always matches what's on screen."""
    colors = atelier_colorway(theme)
    all_labels = list(SPLIT_DIMS.keys())

    with chart_card():
        c_t, c_split, c_type, c_unit = st.columns([0.36, 0.28, 0.18, 0.18], vertical_alignment="center")
        with c_t:
            st.markdown('<div class="chart-title">Portfolio split — click to focus</div>'
                        '<div class="chart-sub">Change "Split by" here · click a bar to focus</div>',
                        unsafe_allow_html=True)
        with c_split:
            chosen_label = st.selectbox("Split by", all_labels, index=all_labels.index(split_label),
                                        key="overview_split_widget", label_visibility="collapsed",
                                        help="Change the x-axis here — this updates the Split-by used app-wide.")
        with c_type:
            ctype = st.segmented_control("Chart type", ["Bars", "Donut"], default="Bars",
                                         key="overview_ctype", label_visibility="collapsed") or "Bars"
        with c_unit:
            unit = st.segmented_control("Unit", ["€", "#"], default="€",
                                        key="overview_unit", label_visibility="collapsed") or "€"

        if chosen_label != split_label:
            st.session_state["_pending_split_label"] = chosen_label
            st.rerun()

        split_table, split_col = SPLIT_DIMS[split_label]
        df = scoped[split_table]
        if df.empty:
            st.info("No data matches the current filters.")
            return

        if split_table == "projects":
            grp = df.groupby(split_col).agg(amount=("funded_amount", "sum"), count=("project_id", "count"))
            series = grp["amount"] if unit == "€" else grp["count"]
        else:
            grp = df.groupby(split_col).agg(count=("investor_id", "count"))
            series = grp["count"]
        series = series.sort_values(ascending=False)
        fmt = "eur" if (unit == "€" and split_table == "projects") else "int"
        labels = [format_number(v, fmt) for v in series.values]

        col1, col2 = st.columns([1.4, 1], vertical_alignment="center")
        with col1:
            if ctype == "Donut":
                fig = go.Figure(go.Pie(labels=series.index.astype(str), values=series.values, hole=0.62,
                                       marker=dict(colors=[colors[i % len(colors)] for i in range(len(series))]),
                                       textinfo="label+percent", sort=False, automargin=True, textfont=dict(size=12),
                                       domain=dict(x=[0.04, 0.96], y=[0.06, 0.94])))
                fig.update_layout(**plotly_layout(theme, height=380, showlegend=False))
                fig.update_layout(margin=dict(t=26, b=26, l=10, r=10))
            else:
                fig = go.Figure(go.Bar(x=series.index.astype(str), y=series.values, marker_color=colors[0],
                                       text=labels, textposition="outside", cliponaxis=False, textfont=dict(size=12)))
                fig.update_layout(**plotly_layout(theme, height=390, showlegend=False))
                fig.update_xaxes(tickangle=-20)
                fig.update_yaxes(showticklabels=False)
                gradient_bars(fig)
            st.plotly_chart(fig, theme=None, key="overview_split_chart",
                            on_select=_on_bar_click, selection_mode="points")
        with col2:
            total = float(series.sum()) or 1.0
            render_legend([(colors[i % len(colors)], name, f"{format_number(val, fmt)} · {val/total*100:.1f}%")
                           for i, (name, val) in enumerate(series.items())])

    # ---- end table (heading + export share one row) ----
    with chart_card():
        p = scoped["projects"]
        if split_table == "projects" and not p.empty:
            g = p.groupby(split_col).agg(funded=("funded_amount", "sum"), n=("project_id", "count"))
        else:
            g = scoped["investors"].groupby(split_col).agg(n=("investor_id", "count"))
            g["funded"] = g["n"]
        g = g.sort_values("funded", ascending=False)
        grand = float(g["funded"].sum()) or 1.0
        val_is_eur = split_table == "projects"
        valcol = "Funded" if val_is_eur else "Investors"
        rows = [{"Segment": str(idx), valcol: format_number(r.funded, "eur" if val_is_eur else "int"),
                 "% total": f"{r.funded/grand*100:.1f}%", "Count": f"{int(r.n):,}"} for idx, r in g.iterrows()]
        render_table(pd.DataFrame(rows), num_cols={"Count"},
                     bar_frac={valcol: norm(g["funded"].tolist()),
                               "% total": [v / grand for v in g["funded"].tolist()]}, rank=True,
                     export_name="overview_split_summary",
                     title=f"Split summary — {split_label}", subtitle="Funded €, share of total, data bars")


def render_hover_explorer(scoped: dict, split_label: str, split_col: str, split_table: str, theme: str) -> None:
    """The unified split explorer: in-chart Split-by dropdown (instant, client-side),
    Bars/Donut toggle, hover panel with selectable KPIs + a top-10 list."""
    import components_hover

    projects, investors = scoped["projects"], scoped["investors"]
    if projects.empty and investors.empty:
        return

    with chart_card(deep=True):
        st.markdown('<div class="chart-title">Split explorer</div>'
                    '<div class="chart-sub">Change "Split by" inside the chart · hover to drill in — '
                    'pick which KPIs the tooltip shows</div>', unsafe_allow_html=True)
        kpi_opts = ["Funded €", "Loans", "Avg rate", "Avg LTC", "Investors", "Avg wallet"]
        chosen = kpi_opts  # tooltip shows all KPIs (picker removed)

        def extra_kpis(table, sub):
            out = {}
            if table == "projects" and len(sub):
                out["Avg rate"] = f"{sub['interest_rate'].mean():.1f}%"
                out["Avg LTC"] = f"{sub['ltc'].mean():.0f}%"
            if table == "investors" and len(sub):
                out["Investors"] = f"{len(sub):,}"
                out["Avg wallet"] = format_number(float(sub['wallet_balance'].mean()), "eur")
            return [[k, out[k]] for k in chosen if k in out]

        payload = build_split_payload(
            SPLIT_DIMS, {"projects": projects, "investors": investors},
            id_col_by_table={"projects": "project_id", "investors": "investor_id"},
            name_col_by_table={"projects": "project_name", "investors": "name"},
            value_col_by_table={"projects": "funded_amount", "investors": "wallet_balance"},
            fmt="eur", top_label="Top 10", extra_kpis=extra_kpis,
        )
        components_hover.split_explorer(payload, theme, default_dim=split_label, height=520,
                                        panel_title="Segment detail", key="overview_explorer")
