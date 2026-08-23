"""
app.py -- Data Lab Portfolio Analytics (Streamlit)

Interactive reporting dashboard on synthetic real-estate-lending data, styled to
the Data Lab design language. Swap `synthetic_data.generate_dataset()` for a
loader over the real export once it exists.

Controls live in the left pane. The reporting period applies everywhere: flow
charts (Activity, Available Funds) use the window; stock charts are shown as of
the window end; KPIs show period-over-period deltas. Marketing / Regulatory /
Analytics are collapsible sections under the Overview tab.

Run:  streamlit run app.py
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from theme import PALETTES, inject_css, render_masthead, render_kpi_row, render_chips, section_header
from synthetic_data import generate_dataset
from metrics import CATALOG, DEFAULT_KPIS, AUDIENCE_WORD, build_kpis, kpi_items, tab_kpi_items, build_sparklines
import periods
from views import overview, portfolio, cumulative, risk
from dims import SPLIT_DIMS
from ui import set_deep_teal, deep_dive

st.set_page_config(page_title="Data Lab Portfolio Analytics", page_icon="◆",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    '<div class="dl-demo-banner" style="font:500 12px/1.5 Manrope,Helvetica Neue,Arial,sans-serif;letter-spacing:.04em;'
    'padding:9px 16px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);margin:-8px 0 14px;color:#cfdad8">'
    '<b>Data Lab · demonstration.</b> A portfolio and investor-reporting suite for a lending platform. '
    'Everything is interactive — filter, drill down, export. '
    '<a href="https://rihardsgarancs.com/company" style="color:#C9A24E;text-decoration:none">← rihardsgarancs.com/company</a></div>',
    unsafe_allow_html=True)

TODAY = pd.Timestamp("2026-07-13")

SIZE_PRESETS = {
    "Preview": dict(n_clients=25, n_projects=80, n_investors=1200),
}
PREVIEW_SEED = 42

# tab identity (icon key -> label). Icon order must match the rendered tab order.
BASE_TAB_ORDER = ["overview", "outstanding", "cumulative", "risk"]
TAB_LABELS = {"overview": "Overview", "outstanding": "Outstanding", "cumulative": "Cumulative",
              "risk": "Risk & Recovery"}


def tab_order_for(audience: str):
    return list(BASE_TAB_ORDER)




# Set DATALAB_DATA to a .xlsx workbook (sheet per table) or a folder of {table}.xlsx
# files to run on REAL data -- no code change needed. Unset -> synthetic demo data.
DATALAB_DATA = os.environ.get("DATALAB_DATA")


@st.cache_resource(show_spinner="Building the demo dataset…")
def _dataset(seed: int, size_key: str) -> dict:
    # cache_resource keeps the object in memory (no pickling): the in-browser
    # pandas build cannot unpickle datetime64 arrays, which broke cache_data on rerun.
    return generate_dataset(seed=seed, **SIZE_PRESETS[size_key])


def load_data(seed: int, size_key: str) -> dict:
    d = _dataset(seed, size_key)
    return {k: (v.copy() if hasattr(v, "copy") else v) for k, v in d.items()}


def apply_dimension_filters(data, countries, ptypes, ratings, itypes, methods) -> dict:
    projects = data["projects"]
    projects_f = projects[
        projects.country.isin(countries) & projects.project_type.isin(ptypes) & projects.rating.isin(ratings)
    ]
    investors = data["investors"]
    investors_f = investors[investors.country.isin(countries) & investors.investor_type.isin(itypes)]
    investments = data["investments"]
    investments_f = investments[
        investments.project_id.isin(projects_f.project_id)
        & investments.investor_id.isin(investors_f.investor_id)
        & investments.method.isin(methods)
    ]
    transactions = data["transactions"]
    transactions_f = transactions[transactions.investor_id.isin(investors_f.investor_id)]
    secondary = data["secondary_market"]
    secondary_f = secondary[secondary.investment_id.isin(investments_f.investment_id)]
    return dict(projects=projects_f, investors=investors_f, investments=investments_f,
                transactions=transactions_f, secondary_market=secondary_f)


def _cascade_projects(scoped: dict, projects_f) -> dict:
    s = dict(scoped)
    s["projects"] = projects_f
    s["investments"] = scoped["investments"][scoped["investments"].project_id.isin(projects_f.project_id)]
    s["secondary_market"] = scoped["secondary_market"][
        scoped["secondary_market"].investment_id.isin(s["investments"].investment_id)]
    return s


def apply_focus(scoped: dict, table: str, col: str, value: str) -> dict:
    if table == "projects":
        return _cascade_projects(scoped, scoped["projects"][scoped["projects"][col] == value])
    s = dict(scoped)
    s["investors"] = scoped["investors"][scoped["investors"][col] == value]
    s["investments"] = scoped["investments"][scoped["investments"].investor_id.isin(s["investors"].investor_id)]
    s["transactions"] = scoped["transactions"][scoped["transactions"].investor_id.isin(s["investors"].investor_id)]
    s["secondary_market"] = scoped["secondary_market"][
        scoped["secondary_market"].investment_id.isin(s["investments"].investment_id)]
    return s


def apply_window(scoped: dict, start, end) -> dict:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    p = scoped["projects"]
    return dict(
        projects=p[p.start_date.between(start, end)],
        investors=scoped["investors"][scoped["investors"].registration_date.between(start, end)],
        investments=scoped["investments"][scoped["investments"].invested_date.between(start, end)],
        transactions=scoped["transactions"][scoped["transactions"].date.between(start, end)],
        secondary_market=scoped["secondary_market"][scoped["secondary_market"].listed_date.between(start, end)],
    )


def apply_asof(scoped: dict, as_of) -> dict:
    """Stock view: everything that exists on/before the window end."""
    a = pd.Timestamp(as_of)
    p = scoped["projects"]
    return dict(
        projects=p[p.start_date <= a],
        investors=scoped["investors"][scoped["investors"].registration_date <= a],
        investments=scoped["investments"][scoped["investments"].invested_date <= a],
        transactions=scoped["transactions"][scoped["transactions"].date <= a],
        secondary_market=scoped["secondary_market"][scoped["secondary_market"].listed_date <= a],
    )


def main() -> None:
    # apply a pending split-by change made from an in-chart selector (e.g. Overview)
    # BEFORE the sidebar widget with key="split_label" is instantiated below.
    if "_pending_split_label" in st.session_state:
        st.session_state["split_label"] = st.session_state.pop("_pending_split_label")

    # ---- public preview: fixed settings, no sidebar ----
    theme = "dark"
    audience = "Internal"
    size_key = "Preview"
    data = load_data(PREVIEW_SEED, size_key)
    today_ref = pd.Timestamp(data.get("generated_at") or TODAY)
    loan_cat = "All"
    period = "Snapshot"
    custom = None
    include_infunding = True
    split_label = st.session_state.get("split_label") or list(SPLIT_DIMS.keys())[0]
    if split_label not in SPLIT_DIMS:
        split_label = list(SPLIT_DIMS.keys())[0]
    st.session_state["split_label"] = split_label
    split_table, split_col = SPLIT_DIMS[split_label]
    focus = st.session_state.get("focus_value") or "All"
    focus_options = ["All"] + sorted(data[split_table][split_col].dropna().unique().tolist())
    if focus not in focus_options:
        focus = "All"
    all_countries = sorted(data["projects"]["country"].unique())
    all_ptypes = sorted(data["projects"]["project_type"].unique())
    all_ratings = sorted(data["projects"]["rating"].unique())
    all_itypes = sorted(data["investors"]["investor_type"].unique())
    countries, ptypes, ratings, itypes = all_countries, all_ptypes, all_ratings, all_itypes
    methods = ["Auto", "Manual"]
    selected_kpis = DEFAULT_KPIS
    show_sparklines = True
    set_deep_teal(False)

    inject_css(theme, tab_order=tab_order_for(audience))

    # ---- scope ----
    scoped = apply_dimension_filters(
        data, countries or ["__none__"], ptypes or ["__none__"], ratings or ["__none__"],
        itypes or ["__none__"], methods or ["__none__"],
    )
    if loan_cat != "All":
        scoped = _cascade_projects(scoped, scoped["projects"][scoped["projects"].loan_category == loan_cat])
    if not include_infunding:
        scoped = _cascade_projects(scoped, scoped["projects"][~scoped["projects"].status.isin(["Available", "Servicing"])])
    if focus and focus != "All":
        scoped = apply_focus(scoped, split_table, split_col, focus)

    data_min = min(data["projects"]["start_date"].min(), data["investors"]["registration_date"].min())
    window_start, window_end = periods.resolve_window(period, today_ref, data_min, custom)
    prev_start, prev_end = periods.previous_window(period, window_start, window_end)
    show_delta = period in periods.PERIODS_WITH_DELTA
    asof = apply_asof(scoped, window_end)         # stock views (as of window end)
    windowed = apply_window(scoped, window_start, window_end)  # flow views

    # ---- masthead (dynamic name) ----
    word = "Preview"
    render_masthead("Data Lab <em>Portfolio</em> analytics")

    # ---- active-filter chips ----
    chips = [("Report", word), ("Period", periods.window_label(period, window_start, window_end))]
    if show_delta:
        chips.append(("Compare vs", periods.comparison_label(period, prev_start, prev_end)))
    if focus and focus != "All":
        chips.append(("Focus", focus))
    if not include_infunding:
        chips.append(("In-funding", "excluded"))
    if len(countries) < len(all_countries):
        chips.append(("Country", ", ".join(countries) if len(countries) <= 3 else f"{len(countries)}/{len(all_countries)}"))
    if len(ratings) < len(all_ratings):
        chips.append(("Rating", ", ".join(ratings) if len(ratings) <= 4 else f"{len(ratings)}/{len(all_ratings)}"))
    if set(methods) != {"Auto", "Manual"}:
        chips.append(("Method", ", ".join(methods) or "none"))
    chips.append(("Projects", f"{len(asof['projects']):,}"))
    chips.append(("Investors", f"{len(asof['investors']):,}"))
    render_chips(chips)

    # ---- KPIs ----
    kpis = build_kpis(scoped, window_start, window_end, prev_start, prev_end, show_delta)
    sparks = build_sparklines(scoped, window_end) if show_sparklines else None

    def tab_kpis(tab):
        render_kpi_row(tab_kpi_items(kpis, tab, audience, sparks), columns=4)

    def _overview():
        render_kpi_row(kpi_items(kpis, selected_kpis, audience, sparks)[0], columns=4)
        section_header("Pipelines", "Investor & project funnels · as of period end")
        overview.render_pipeline(asof["investors"], scoped["investments"], window_end, theme)
        overview.render_project_pipeline(asof["projects"], window_end, theme)
        section_header("Portfolio split", "Break the book down · click a bar to focus")
        overview.render(asof, theme, audience, split_label, split_col, split_table)
        with deep_dive("Break the book down · hover to drill in"):
            overview.render_hover_explorer(asof, split_label, split_col, split_table, theme)

    def _outstanding():
        tab_kpis("portfolio")
        portfolio.render(asof["projects"], theme, audience, split_col if split_table == "projects" else None)

    def _cumulative():
        tab_kpis("cumulative")
        cumulative.render(asof, theme, audience, window_end, kpis, (window_start, window_end), period)

    def _risk():
        tab_kpis("risk")
        risk.render(asof, theme, audience, window_end)

    renderers = {"overview": _overview, "outstanding": _outstanding, "cumulative": _cumulative, "risk": _risk}
    order = tab_order_for(audience)
    tab_objs = st.tabs([TAB_LABELS[k] for k in order])
    for k, tabobj in zip(order, tab_objs):
        with tabobj:
            renderers[k]()


if __name__ == "__main__":
    main()
