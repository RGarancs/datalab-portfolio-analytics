"""Topic ⑤ -- Project view. A split explorer (in-chart split + Bars/Donut + hover
panel) for funded volume; a status chart with Bars/Donut; and one Projects table
with a Stages/Groups toggle -- top 100 by funded €, scrollable within its card,
with Other + TOTAL summary rows, data bars, % of total and rating badges."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import status_colorway, plotly_layout, gradient_bars
from metrics import format_number
from ui import chart_card, card_header, render_table, norm, RATING_BADGE, column_picker, build_split_payload, deep_dive
from dims import PROJECT_DIMS

COL_FOR = {v[1]: lbl for lbl, v in PROJECT_DIMS.items()}
TOP_N = 100


def _group_table(projects: pd.DataFrame) -> pd.DataFrame:
    grp = projects.groupby("group_id")
    agg = grp.agg(
        Group=("group_name", "first"), Type=("project_type", "first"), Country=("country", "first"),
        total=("total_stages", "max"), current=("current_stage", "max"),
        funded=("funded_amount", "sum"), target=("funding_target", "sum"),
    )
    # weighted average rate without groupby.apply (version-safe: pandas 2.x & 3.x)
    w = projects.assign(_rw=projects["interest_rate"] * projects["funded_amount"])
    num = w.groupby("group_id")["_rw"].sum()
    den = w.groupby("group_id")["funded_amount"].sum().clip(lower=1)
    agg["rate"] = (num / den)
    agg["completion"] = (agg["funded"] / agg["target"].clip(lower=1) * 100).clip(0, 100)
    return agg.sort_values("funded", ascending=False)


def render(scoped: dict, theme: str, audience: str, split_label: str, split_col: str) -> None:
    import components_hover

    projects = scoped["projects"]
    if projects.empty:
        st.info("No projects match the current filters.")
        return
    default_break = COL_FOR.get(split_col, "Rating")

    # ---- split explorer: funded volume by any dimension, in-chart switch + hover ----
    with chart_card():
        st.markdown('<div class="chart-title">Funded volume — explore</div>'
                    '<div class="chart-sub">Change "Split by" inside the chart · Bars/Donut · hover for KPIs + top 10</div>',
                    unsafe_allow_html=True)
        kpi_opts = ["Funded €", "Loans", "Avg rate", "Avg LTC", "Avg completion"]
        chosen = kpi_opts

        def extra_kpis(table, sub):
            if not len(sub):
                return []
            comp = (sub["funded_amount"] / sub["funding_target"].clip(lower=1) * 100).clip(0, 100).mean()
            out = {"Avg rate": f"{sub['interest_rate'].mean():.1f}%", "Avg LTC": f"{sub['ltc'].mean():.0f}%",
                   "Avg completion": f"{comp:.0f}%"}
            return [[k, out[k]] for k in chosen if k in out]

        payload = build_split_payload(
            PROJECT_DIMS, {"projects": projects},
            id_col_by_table={"projects": "project_id"}, name_col_by_table={"projects": "project_name"},
            value_col_by_table={"projects": "funded_amount"}, fmt="eur", top_label="Top 10 projects", extra_kpis=extra_kpis,
        )
        components_hover.split_explorer(payload, theme, default_dim=default_break, height=520,
                                        panel_title="Segment detail", key="projects_explorer")

    # ---- status chart (Bars/Donut) + completion ----
    with chart_card():
        st.markdown('<div class="chart-title">Funding status &amp; completion</div>'
                    '<div class="chart-sub">Share of funded \u20ac by status · Bars/Donut · hover a status for the loans behind it</div>',
                    unsafe_allow_html=True)
        by_status = projects.groupby("status")["funded_amount"].sum().sort_values(ascending=False)
        completion = (projects["funded_amount"] / projects["funding_target"].clip(lower=1) * 100).clip(0, 100)
        fully = int((completion >= 99.5).sum())
        detail = {}
        for stt in by_status.index:
            sub = projects[projects.status == stt].sort_values("funded_amount", ascending=False)
            comp = (sub["funded_amount"] / sub["funding_target"].clip(lower=1) * 100).clip(0, 100).mean()
            kpis = [["Funded", format_number(float(by_status[stt]), "eur")],
                    ["Loans", f"{len(sub):,}"],
                    ["Avg completion", f"{comp:.0f}%"],
                    ["Avg rate", f"{sub['interest_rate'].mean():.1f}%"]]
            top = [[str(r.project_name), format_number(float(r.funded_amount), "eur")]
                   for r in sub.head(10).itertuples()]
            detail[str(stt)] = {"kpis": kpis, "toplists": {"Top 10 loans": top}}
        payload = {"Status": {"cats": [str(s) for s in by_status.index],
                              "values": [float(v) for v in by_status.values],
                              "labels": [format_number(float(v), "eur") for v in by_status.values],
                              "detail": detail}}
        components_hover.split_explorer(payload, theme, default_dim="Status", chart_type="Donut",
                                        height=520, panel_title="Status detail", key="proj_status_explorer")
        st.caption(f"Avg. completion {completion.mean():.0f}% · fully funded {fully} / {len(projects)}.")

    # ---- Projects table: Stages or Groups · top 100 + Other + TOTAL · scrollable ----
    # ---- deep dive (collapsible): projects / stages table ----
    with deep_dive("Every project / stage · funded €, completion, rate"):
        with chart_card(deep=True):
            grouping = card_header("Projects table", subtitle=f"Top {TOP_N} by funded € · Other + TOTAL · scroll for more",
                                   options=["Stages", "Projects"], default="Stages", key="proj_table_group", label="ProjGroup",
                                   help="Individual funding stages, or whole projects (all stages combined).")
            n_groups = projects["group_id"].nunique()
            multi = int((projects.groupby("group_id")["stage_number"].count() > 1).sum())
            st.caption(f"{len(projects):,} stages across {n_groups:,} projects · {multi:,} projects are multi-stage.")

            if grouping == "Projects":
                g = _group_table(projects)
                grand = float(g["funded"].sum()) or 1.0
                top = g.head(TOP_N)
                rows, fbar, pbar = [], [], []
                for r in top.itertuples():
                    fbar.append(r.funded); pbar.append(r.funded / grand)
                    rows.append({"Project": r.Group, "Type": r.Type, "Country": r.Country,
                                 "Stages": f"{int(r.current)} of {int(r.total)}",
                                 "Funded": format_number(r.funded, "eur"), "% total": f"{r.funded/grand*100:.1f}%",
                                 "Completion": f"{r.completion:.0f}%", "Rate": f"{r.rate:.1f}%"})
                rest = g.iloc[TOP_N:]
                if len(rest):
                    rf = float(rest["funded"].sum()); fbar.append(0); pbar.append(rf / grand)
                    rows.append({"Project": f"Other ({len(rest)})", "Type": "—", "Country": "—", "Stages": "—",
                                 "Funded": format_number(rf, "eur"), "% total": f"{rf/grand*100:.1f}%",
                                 "Completion": "—", "Rate": "—"})
                fbar.append(0); pbar.append(1.0)
                rows.append({"Project": "TOTAL", "Type": "—", "Country": "—", "Stages": "—",
                             "Funded": format_number(grand, "eur"), "% total": "100.0%", "Completion": "—", "Rate": "—"})
                render_table(pd.DataFrame(rows), num_cols={"Completion", "Rate"},
                             bar_frac={"Funded": norm(fbar), "% total": [min(x, 1) for x in pbar]}, max_height=460, rank=True,
                             export_name="projects_by_project")
                st.caption(f"Showing top {min(TOP_N, len(g))} of {len(g):,} projects.")
            else:
                p = projects.copy()
                p["completion"] = (p["funded_amount"] / p["funding_target"].clip(lower=1) * 100).clip(0, 100)
                grand = float(p["funded_amount"].sum()) or 1.0
                ordered = p.sort_values("funded_amount", ascending=False)
                top = ordered.head(TOP_N)
                rows, fbar, pbar = [], [], []
                for r in top.itertuples():
                    fbar.append(r.funded_amount); pbar.append(r.funded_amount / grand)
                    rows.append({"Stage": r.project_name, "Type": r.project_type, "Country": r.country, "Rating": r.rating,
                                 "Stage #": f"{int(r.stage_number)}/{int(r.total_stages)}",
                                 "Funded": format_number(r.funded_amount, "eur"), "% total": f"{r.funded_amount/grand*100:.1f}%",
                                 "Completion": f"{r.completion:.0f}%", "Rate": f"{r.interest_rate:.1f}%", "Status": r.status})
                rest = ordered.iloc[TOP_N:]
                if len(rest):
                    rf = float(rest["funded_amount"].sum()); fbar.append(0); pbar.append(rf / grand)
                    rows.append({"Stage": f"Other ({len(rest)})", "Type": "—", "Country": "—", "Rating": "—", "Stage #": "—",
                                 "Funded": format_number(rf, "eur"), "% total": f"{rf/grand*100:.1f}%",
                                 "Completion": "—", "Rate": "—", "Status": "—"})
                fbar.append(0); pbar.append(1.0)
                rows.append({"Stage": "TOTAL", "Type": "—", "Country": "—", "Rating": "—", "Stage #": "—",
                             "Funded": format_number(grand, "eur"), "% total": "100.0%", "Completion": "—", "Rate": "—", "Status": "—"})
                render_table(pd.DataFrame(rows), num_cols={"Completion", "Rate"}, badges={"Rating": RATING_BADGE},
                             bar_frac={"Funded": norm(fbar), "% total": [min(x, 1) for x in pbar]}, max_height=460, rank=True,
                             export_name="projects_by_stage")
                st.caption(f"Showing top {min(TOP_N, len(p))} of {len(p):,} stages.")
