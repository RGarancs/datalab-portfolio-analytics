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

from theme import PALETTES, inject_css, render_masthead, render_kpi_row, render_chips, section_title, section_header
from synthetic_data import generate_dataset
from metrics import CATALOG, DEFAULT_KPIS, AUDIENCE_WORD, build_kpis, kpi_items, tab_kpi_items, build_sparklines
import periods
from views import (overview, portfolio, cumulative, activity, funds,
                   projects_view, risk, marketing_regulatory, analytics, my_portfolio, public)
from dims import SPLIT_DIMS
from ui import set_deep_teal, deep_dive

st.set_page_config(page_title="Data Lab Portfolio Analytics", page_icon="◆",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(
    '<div class="dl-demo-banner" style="font:500 12px/1.5 Manrope,Helvetica Neue,Arial,sans-serif;letter-spacing:.04em;'
    'padding:8px 14px;border-radius:8px;background:rgba(26,107,112,.12);border:1px solid rgba(26,107,112,.35);margin:-8px 0 14px">'
    '<b>Data Lab · demonstration.</b> A portfolio and investor-reporting suite for a lending platform. '
    'Everything is interactive — filter, drill down, export. '
    '<a href="https://rihardsgarancs.com/company" style="color:#5fb7ae;text-decoration:none">← rihardsgarancs.com/company</a></div>',
    unsafe_allow_html=True)

TODAY = pd.Timestamp("2026-07-13")

SIZE_PRESETS = {
    "Preview (fast)": dict(n_clients=25, n_projects=80, n_investors=1200),
    "Realistic (default)": dict(n_clients=55, n_projects=190, n_investors=4200),
    "Large (stress test)": dict(n_clients=110, n_projects=380, n_investors=9000),
}
SIZE_SHORT = {"Preview (fast)": "Preview", "Realistic (default)": "Realistic", "Large (stress test)": "Large"}

# tab identity (icon key -> label). Icon order must match the rendered tab order.
BASE_TAB_ORDER = ["overview", "outstanding", "cumulative", "activity", "funds", "projects", "risk", "portfolio"]
TAB_LABELS = {"overview": "Overview", "outstanding": "Outstanding", "cumulative": "Cumulative",
              "activity": "Activity", "funds": "Available Funds", "projects": "Projects",
              "risk": "Risk & Recovery", "portfolio": "My Portfolio"}


def tab_order_for(audience: str):
    # Investor-Facing opens on My Portfolio (their own book is the main screen).
    if audience == "Investor-Facing":
        return ["portfolio"] + [k for k in BASE_TAB_ORDER if k != "portfolio"]
    return BASE_TAB_ORDER




AUDIENCE_MATRIX_MD = """
| Section | Internal | Investor-Facing | Public Website |
|---|---|---|---|
| **Layout** | Full 7-tab dashboard | Full 7-tab dashboard (same as Internal) | Separate trimmed page (hero + 3 charts + glossary) — no tabs |
| Overview — investor & project pipeline, split explorer | ✅ | ✅ | ✕ (not on trimmed page) |
| Outstanding — status, new volume, explorer | ✅ | ✅ | ✕ |
| Cumulative — combo chart, matrix table, snapshot | ✅ | ✅ | ✕ (funded-volume chart only, on trimmed page) |
| Activity — flows, top investors, resale market | ✅ | ✅ | ✕ |
| Available Funds — net deposits, forecast, pipeline | ✅ | ✅ | ✕ |
| Projects — grouping, explorer, grid | ✅ | ✅ | ✕ |
| My Portfolio — per-investor drill-down | ✅ | ✅ | ✕ |
| ⑥ Risk & Recovery — distressed book, recovery time | ✅ | ✅ | ✕ |
| ⑥ Risk — Actual vs Budget, peer benchmark, focus | ✅ | ✕ hidden | ✕ |
| ⑦ Marketing (illustrative) | ✅ | ✅ | ✕ |
| ⑧ Regulatory (illustrative) | ✅ | ✅ | ✕ |
| ⑨ Analytics — concentration, velocity, retention, WAL, cash-flow | ✅ | ✅ | ✕ |
| ⑨ Analytics — Expected loss | ✅ | ✅ | ✕ |
| KPI: default rate, avg investment, avg LTC, deposits, net deposits | ✅ | ✅ | ✕ (not on trimmed page) |
| Trimmed page: 8 hero KPIs (funded, interest paid, AROI, outstanding, default rate, LTC, investors, repaid loans) | — | — | ✅ |
| Trimmed page: funded-volume chart, status donut, LTC distribution, glossary | — | — | ✅ |

**Today, Internal and Investor-Facing are nearly identical** — the only current difference is the
Risk tab's Actual-vs-Budget / peer-benchmark / focus-allocation box (Internal only). Tell me what
else to add or remove for Investor-Facing and for Public, and I'll wire the gating.
"""

DATA_DICTIONARY_MD = """
**Entity graph**
```
clients (borrowers) 1───< projects
investors           1───< investments >───1 projects
investors           1───< transactions        (wallet: deposits / withdrawals)
investments          1───0..1 secondary_market (resale listing)
```
- **projects** — loans/deals, funded in **stages** within a **group**. `loan_category`
  (Real Estate / Business), `vintage`, `ltc_band`, `size_band`, `maturity_bucket`.
- **investors** — `investor_tier` from wallet balance (Retail <€25k · HNWI €25–250k ·
  Professional >€250k), `wallet_balance`, `identified` (KYC), `active`, `last_login`.
- **investments / transactions / secondary_market** — bridge + wallet + resale.

Full column dictionary + Excel model: `README.md` · `data_model.xlsx`.
"""


# Set DATALAB_DATA to a .xlsx workbook (sheet per table) or a folder of {table}.xlsx
# files to run on REAL data -- no code change needed. Unset -> synthetic demo data.
DATALAB_DATA = os.environ.get("DATALAB_DATA")


@st.cache_data(show_spinner="Loading data…")
def load_data(seed: int, size_key: str) -> dict:
    if DATALAB_DATA:
        from real_data import load_from_excel
        return load_from_excel(DATALAB_DATA)
    return generate_dataset(seed=seed, **SIZE_PRESETS[size_key])


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

    with st.sidebar:
        st.markdown('<span class="nk-kicker">Data Lab <i>Controls</i></span>', unsafe_allow_html=True)
        theme = st.radio("Theme", list(PALETTES.keys()), horizontal=True,
                         format_func=lambda t: {"dark": "Dark", "light": "Light"}[t], key="theme",
                         help="Dark or light.")
        audience = st.radio("Report audience", ["Internal", "Investor-Facing", "Public Website"],
                            help="Switches the report name and hides internal-only KPIs for non-internal audiences.")

        st.markdown('<hr class="nk-hr"/>', unsafe_allow_html=True)
        st.markdown('<span class="nk-kicker">Demo <i>Data</i></span>', unsafe_allow_html=True)
        size_key = st.selectbox("Dataset size", list(SIZE_PRESETS.keys()), index=1, help="Row volume to generate.")
        seed = st.number_input("Random seed", min_value=0, max_value=999_999, value=42, step=1,
                               help="Try another random draw of the demo data.")
        if st.button("Regenerate demo data"):
            load_data.clear()
        data = load_data(int(seed), size_key)
        today_ref = pd.Timestamp(data.get("generated_at") or TODAY)

        st.markdown('<hr class="nk-hr"/>', unsafe_allow_html=True)
        st.markdown('<span class="nk-kicker">View</span>', unsafe_allow_html=True)
        loan_cat = st.segmented_control("Loan book", ["All", "Real Estate", "Business"], default="All",
                                        key="loan_cat", help="How the whole book splits.") or "All"
        period = st.segmented_control("Reporting period", periods.PERIODS, default="Snapshot", key="period",
                                      help="Applies to every chart & table. Snapshot = all-time. Flow charts use "
                                           "the window; stock charts are as of the window end; KPIs show deltas.") or "Snapshot"
        custom = None
        if period == "Custom":
            dv = st.date_input("Custom range",
                               value=(data["projects"]["start_date"].min().date(), today_ref.date()),
                               min_value=data["projects"]["start_date"].min().date(), max_value=today_ref.date())
            if isinstance(dv, tuple) and len(dv) == 2:
                custom = (dv[0], dv[1])
        include_infunding = st.toggle("Include in-funding loans", value=True,
                                      help="Include Available / Servicing (still-raising) loans in every view.")
        split_label = st.selectbox("Split by", list(SPLIT_DIMS.keys()), key="split_label",
                                   help="Dimension used by the Overview / Projects breakdown charts & tables.")
        split_table, split_col = SPLIT_DIMS[split_label]
        focus_options = ["All"] + sorted(data[split_table][split_col].dropna().unique().tolist())
        if st.session_state.get("focus_value") not in focus_options:
            st.session_state["focus_value"] = "All"
        focus = st.selectbox(f"Focus · {split_label}", focus_options, key="focus_value",
                             help="Narrow the whole dashboard to one value (or click a bar on Overview).")
        _dmin = min(data["projects"]["start_date"].min(), data["investors"]["registration_date"].min())
        _ws, _we = periods.resolve_window(period, today_ref, _dmin, custom)
        _ps, _pe = periods.previous_window(period, _ws, _we)
        if period in periods.PERIODS_WITH_DELTA:
            st.caption(f"Window: {_ws.date()} → {_we.date()}  ·  ↔ vs {periods.comparison_label(period, _ps, _pe)}")
        else:
            st.caption("All-time snapshot · no period comparison.")

        st.markdown('<hr class="nk-hr"/>', unsafe_allow_html=True)
        st.markdown('<span class="nk-kicker">Dimension <i>Filters</i></span>', unsafe_allow_html=True)
        all_countries = sorted(data["projects"]["country"].unique())
        all_ptypes = sorted(data["projects"]["project_type"].unique())
        all_ratings = sorted(data["projects"]["rating"].unique())
        all_itypes = sorted(data["investors"]["investor_type"].unique())
        countries = st.multiselect("Country", all_countries, default=all_countries)
        ptypes = st.multiselect("Project type", all_ptypes, default=all_ptypes)
        ratings = st.multiselect("Rating", all_ratings, default=all_ratings)
        itypes = st.multiselect("Investor type", all_itypes, default=all_itypes)
        methods = st.multiselect("Investment method", ["Auto", "Manual"], default=["Auto", "Manual"])

        st.markdown('<hr class="nk-hr"/>', unsafe_allow_html=True)
        st.markdown('<span class="nk-kicker">Overview <i>KPIs (8)</i></span>', unsafe_allow_html=True)
        selected_kpis = st.multiselect("KPI cards on Overview", list(CATALOG.keys()),
                                       default=DEFAULT_KPIS, format_func=lambda k: CATALOG[k]["label"],
                                       help="Pick which of the 12 metrics show on the Overview tab.")
        show_sparklines = st.toggle("Sparklines on KPI cards", value=False,
                                    help="Add a 12-month mini trend line under each KPI number.")
        deep_teal = st.toggle("Teal deep-dive sections", value=False,
                              help="Paint the deep-dive cards in each tab with the teal growth-story surface.")
        set_deep_teal(deep_teal)
        st.markdown('<hr class="nk-hr"/>', unsafe_allow_html=True)
        with st.expander("Data dictionary"):
            st.markdown(DATA_DICTIONARY_MD)
        with st.expander("Audience visibility — what's shown to whom"):
            st.markdown(AUDIENCE_MATRIX_MD)

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
    word = AUDIENCE_WORD.get(audience, "Internal")
    render_masthead(f"Data Lab <em>{word}</em> statistics")

    # ---- PUBLIC: trimmed, credibility-first layout (hero + 3 charts + glossary) ----
    if audience == "Public Website":
        render_chips([("Report", "Public"), ("Book", loan_cat), ("As of", str(window_end.date()))])
        public.render(asof, theme, window_end)
        return

    # ---- active-filter chips ----
    chips = [("Report", word), ("Book", loan_cat), ("Period", periods.window_label(period, window_start, window_end))]
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
        st.markdown('<hr class="nk-hr"/>', unsafe_allow_html=True)
        section_title("More views")
        with st.expander("⑦ Marketing — website & acquisition funnel (illustrative)"):
            marketing_regulatory.render_marketing(asof, theme, audience, window_end)
        with st.expander("⑧ Regulatory — KYC / AML / filings (illustrative)"):
            marketing_regulatory.render_regulatory(asof, theme, audience, window_end)
        with st.expander("⑨ Analytics — concentration · expected loss · maturity · recovery · velocity · retention · WAL · cash-flow"):
            analytics.render(asof, theme, audience, window_end)

    def _outstanding():
        tab_kpis("portfolio")
        portfolio.render(asof["projects"], theme, audience, split_col if split_table == "projects" else None)

    def _cumulative():
        tab_kpis("cumulative")
        cumulative.render(asof, theme, audience, window_end, kpis, (window_start, window_end), period)

    def _activity():
        tab_kpis("activity")
        activity.render(windowed, theme, audience, window_end, base=asof)

    def _funds():
        tab_kpis("funds")
        funds.render(windowed, theme, audience, window_end, base=asof)

    def _projects():
        tab_kpis("projects")
        projects_view.render(asof, theme, audience, split_label, split_col if split_table == "projects" else "rating")

    def _risk():
        tab_kpis("risk")
        risk.render(asof, theme, audience, window_end)

    def _portfolio():
        my_portfolio.render(asof, theme, audience)

    renderers = {"overview": _overview, "outstanding": _outstanding, "cumulative": _cumulative,
                 "activity": _activity, "funds": _funds, "projects": _projects, "risk": _risk,
                 "portfolio": _portfolio}
    order = tab_order_for(audience)
    tab_objs = st.tabs([TAB_LABELS[k] for k in order])
    for k, tabobj in zip(order, tab_objs):
        with tabobj:
            renderers[k]()


if __name__ == "__main__":
    main()
