"""ui.py -- layout helpers: chart cards, in-card view toggles, legend rows, and
styled HTML tables with data bars + colour-coded badges (Data Lab look)."""
from __future__ import annotations

import contextlib
import html
import itertools

import pandas as pd
import streamlit as st

RATING_BADGE = {"A": "#059669", "B": "#65A30D", "C": "#D4792E", "D": "#EA580C", "E": "#DC2626"}
TIER_BADGE = {"Retail": "#64748B", "HNWI": "#D4792E", "Professional": "#5226E5"}
TYPE_BADGE = {"Individual": "#64748B", "Institutional": "#5226E5"}


def norm(values) -> list[float]:
    """Normalise a numeric sequence to 0..1 against its own max (for data bars)."""
    vals = [float(v or 0) for v in values]
    m = max(vals) if vals else 0
    return [(v / m if m else 0) for v in vals]


_card_seq = itertools.count()


def set_deep_teal(on: bool) -> None:
    st.session_state["_deep_teal"] = bool(on)


@contextlib.contextmanager
def chart_card(deep: bool = False):
    """Bordered card. `deep=True` marks it as a deep-dive card; when the sidebar
    'teal deep-dive' toggle is on those cards get the teal growth-story surface.
    Keyed so the theme CSS ([class*=st-key-nkcard]) actually applies -- this
    Streamlit build has no stable border-container testid."""
    teal = deep and st.session_state.get("_deep_teal", False)
    key = f"nkcard{'_teal' if teal else ''}_{next(_card_seq)}"
    with st.container(border=True, key=key):
        yield


_dd_seq = itertools.count()


@contextlib.contextmanager
def deep_dive(sub: str = "", expanded: bool = False):
    """Collapsible 'Deep dive' subsection -- closed by default, click to reveal.
    Keyed + teal-aware so its header can echo the deep-dive accent."""
    teal = st.session_state.get("_deep_teal", False)
    key = f"deepdivexp{'_teal' if teal else ''}_{next(_dd_seq)}"
    label = "Deep dive"  # kept short -> renders as the blue pill header (one deep dive per tab)
    with st.container(key=key):
        with st.expander(label, expanded=expanded):
            yield


def card_header(title: str, subtitle: str | None = None, options=None, default=None,
                key=None, label: str | None = None, ratio=(0.56, 0.44), help=None):
    """Chart title (+ subtitle) left, in-card view toggle right. Returns the
    selected toggle value (or `default`). `help` shows a tooltip on the toggle."""
    left, right = st.columns(list(ratio), vertical_alignment="center")
    with left:
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<div class="chart-sub">{subtitle}</div>', unsafe_allow_html=True)
    value = None
    if options:
        with right:
            value = st.segmented_control(label or title, options, default=default, key=key,
                                         label_visibility="collapsed", help=help)
    return value if value is not None else default


def render_legend(rows: list[tuple[str, str, str]]) -> None:
    """rows: list of (color, label, value)."""
    html_rows = "".join(
        f'<div class="nk-legend"><span class="dot" style="background:{c}"></span>'
        f'<span class="rlabel">{html.escape(str(l))}</span><span class="rval">{v}</span></div>'
        for c, l, v in rows
    )
    st.markdown(html_rows, unsafe_allow_html=True)


_export_seq = itertools.count()


def _export_popover(df: pd.DataFrame, name: str) -> None:
    """CSV download button."""
    tid = next(_export_seq)
    csv_text = df.to_csv(index=False)
    st.download_button("\u2913 CSV", csv_text.encode("utf-8"),
                       file_name=f"{name}.csv", mime="text/csv",
                       key=f"exp_csv_{tid}", use_container_width=True)


def _export_controls(df: pd.DataFrame, name: str) -> None:
    """Right-aligned export popover on its own row above a table."""
    _, right = st.columns([0.82, 0.18], vertical_alignment="center")
    with right:
        _export_popover(df, name)


def render_table(df: pd.DataFrame, num_cols=None, bar_frac=None, badges=None,
                 total_labels=("TOTAL",), other_prefix="Other", max_height=None, rank=False,
                 export=True, export_name="datalab_table", title=None, subtitle=None) -> None:
    """Clean HTML table with optional data bars + colour-coded badges.

    num_cols  : columns right-aligned with tabular nums
    bar_frac  : {col: [fraction 0..1 per row]} -> inline data bar behind the value
    badges    : {col: {value: hex}} -> coloured pill badge (e.g. rating / tier)
    rank      : prepend a "#" ordinal column (1,2,3...; blank for Other/TOTAL rows)
    export    : show a CSV / Excel download control
    title     : if set, render the heading + export inline on ONE row (no wasted gap)
    TOTAL / Other rows are emphasised automatically.
    """
    if title is not None:
        htxt = f'<div class="chart-title">{html.escape(str(title))}</div>'
        if subtitle:
            htxt += f'<div class="chart-sub">{html.escape(str(subtitle))}</div>'
        hl, hr = st.columns([0.74, 0.26], vertical_alignment="center")
        with hl:
            st.markdown(htxt, unsafe_allow_html=True)
        if export:
            with hr:
                _export_popover(df, export_name)
    elif export:
        _export_controls(df, export_name)
    num_cols = set(num_cols or [])
    bar_frac = bar_frac or {}
    badges = badges or {}
    num_cols |= set(bar_frac.keys())
    cols = list(df.columns)
    if rank and cols:
        df = df.copy()
        ranks, c = [], 1
        for _, rr in df.iterrows():
            first = str(rr[cols[0]])
            if first in total_labels or first.startswith(other_prefix):
                ranks.append("")
            else:
                ranks.append(str(c)); c += 1
        df.insert(0, "#", ranks)
        cols = list(df.columns)

    thead = "".join(f'<th class="{"num" if c in num_cols else ""}">{html.escape(str(c))}</th>' for c in cols)
    body = []
    for i, (_, r) in enumerate(df.iterrows()):
        first = str(r[cols[0]])
        cls = " class='total'" if (first in total_labels or first.startswith(other_prefix)) else ""
        tds = []
        for c in cols:
            val = r[c]
            text = "" if (isinstance(val, float) and pd.isna(val)) or val is None else html.escape(str(val))
            if c in badges and str(val) in badges[c]:
                tds.append(f'<td><span class="nk-badge" style="background:{badges[c][str(val)]}">{text}</span></td>')
            elif c in bar_frac:
                f = bar_frac[c][i] if i < len(bar_frac[c]) else 0
                f = max(0.0, min(float(f), 1.0))
                tds.append(f'<td class="num nk-bar"><span class="fill" style="width:{f*100:.1f}%"></span>'
                           f'<span class="val">{text}</span></td>')
            else:
                tds.append(f'<td class="{"num" if c in num_cols else ""}">{text}</td>')
        body.append(f"<tr{cls}>{''.join(tds)}</tr>")

    wrap_cls = "nk-table-wrap scroll-y" if max_height else "nk-table-wrap"
    wrap_style = f' style="max-height:{int(max_height)}px"' if max_height else ""
    st.markdown(f'<div class="{wrap_cls}"{wrap_style}><table class="nk-table"><thead><tr>{thead}</tr></thead>'
                f'<tbody>{"".join(body)}</tbody></table></div>', unsafe_allow_html=True)


def column_picker(all_cols, key, default=None, label="Columns"):
    """Popover multiselect to choose which columns a table shows."""
    default = default if default is not None else all_cols
    with st.popover(label):
        sel = st.multiselect("Show columns", all_cols, default=default, key=key, label_visibility="collapsed")
    return [c for c in all_cols if c in sel] or all_cols


def aggrid_table(df, group_cols=None, key=None, height=380, csv_name="table.csv",
                 sum_cols=None, default_expanded=0):
    """Sortable table with a CSV download (the AG Grid component was dropped to
    keep the in-browser build small)."""
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                       file_name=csv_name, key=(str(key) + "_csv"), use_container_width=False)
    st.dataframe(df, hide_index=True, width="stretch")


def build_split_payload(dims: dict, tables: dict, id_col_by_table: dict, name_col_by_table: dict,
                        value_col_by_table: dict, fmt: str = "eur", top_label: str = "Top 10",
                        extra_kpis=None, top_n: int = 10):
    """Precompute {dim_label: {cats, values, labels, detail}} for every dimension in
    `dims`, ready to hand to components_hover.split_explorer (client-side dim switch).

    tables            : {"projects": df, "investors": df}
    id_col_by_table   : {"projects": "project_id", "investors": "investor_id"}
    name_col_by_table : {"projects": "project_name", "investors": "name"}
    value_col_by_table: {"projects": "funded_amount", "investors": "wallet_balance"}
    extra_kpis(table, cat_df) -> list[[label, value_str]]  (optional, appended per category)
    """
    from metrics import format_number
    payload = {}
    for label, (table, col) in dims.items():
        df = tables.get(table)
        if df is None or df.empty or col not in df.columns:
            continue
        id_col, name_col, value_col = id_col_by_table[table], name_col_by_table[table], value_col_by_table[table]
        g = df.groupby(col).agg(value=(value_col, "sum"), count=(id_col, "count")).sort_values("value", ascending=False)
        if g.empty:
            continue
        cats = g.index.astype(str).tolist()
        values = [float(v) for v in g["value"].tolist()]
        labels = [format_number(v, fmt) for v in values]
        detail = {}
        for cat in g.index:
            sub = df[df[col] == cat].sort_values(value_col, ascending=False).head(top_n)
            kpis = [["Total", format_number(float(g.loc[cat, "value"]), fmt)],
                    ["Count", f"{int(g.loc[cat, 'count']):,}"]]
            if extra_kpis:
                kpis += extra_kpis(table, df[df[col] == cat])
            top = [[str(getattr(r, name_col)), format_number(float(getattr(r, value_col)), fmt)]
                   for r in sub.itertuples()]
            detail[str(cat)] = {"kpis": kpis, "toplists": {top_label: top}}
        payload[label] = {"cats": cats, "values": values, "labels": labels, "detail": detail}
    return payload
