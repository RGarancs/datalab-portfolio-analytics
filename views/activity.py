"""Topic ③ -- Activity.

Main charts: wallet deposits/withdrawals, and Invested / Servicing / Available
amounts as full-width hover explorers (Bars/Donut, hover a category for its
top projects / investors, with a Split-by selection where relevant).

Deep dive (collapsible): investor-base net buckets, the top-investors leaderboard,
the resale market, and the monthly wallet-flows table.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import components_hover
from theme import atelier_colorway, plotly_layout, gradient_bars
from metrics import format_number
from ui import chart_card, card_header, render_table, norm, TIER_BADGE, deep_dive

GRAIN_PERIOD = {"Daily": "D", "Monthly": "M", "Annual": "Y"}


def _bucket(series: pd.Series, period_code: str) -> pd.Series:
    return series.dt.to_period(period_code).dt.to_timestamp()


def _two_level_payload(df, group_col, value_col, sub_col, sub_label,
                       top_cats: int = 12, top_items: int = 10) -> dict:
    """One split dimension: bars = top `group_col` by summed `value_col`; hovering
    a bar reveals that group's top `sub_col` contributors (e.g. project -> top
    investors, or investor -> top projects)."""
    if df is None or df.empty:
        return {"cats": [], "values": [], "labels": [], "detail": {}}
    g = df.groupby(group_col)[value_col].sum().sort_values(ascending=False).head(top_cats)
    two = df.groupby([group_col, sub_col])[value_col].sum()          # one pass, sliced per category
    nuniq = df.groupby(group_col)[sub_col].nunique()
    detail = {}
    for cat in g.index:
        try:
            s = two.loc[cat].sort_values(ascending=False).head(top_items)
        except KeyError:
            s = pd.Series(dtype=float)
        kpis = [["Total", format_number(float(g[cat]), "eur")],
                [sub_label.capitalize(), f"{int(nuniq.get(cat, 0)):,}"]]
        top = [[str(n), format_number(float(v), "eur")] for n, v in s.items()]
        detail[str(cat)] = {"kpis": kpis, "toplists": {f"Top {sub_label}": top}}
    return {"cats": [str(c) for c in g.index], "values": [float(v) for v in g.values],
            "labels": [format_number(float(v), "eur") for v in g.values], "detail": detail}


def _time_payload(df, date_col, value_col, sub_col, sub_label, freq,
                  last_days=None, max_months=24, top_items: int = 10) -> dict:
    """Time-series dimension: bars = summed `value_col` per date bucket (day/month),
    in chronological order; hovering a bucket shows that period's top contributors."""
    if df is None or df.empty:
        return {"cats": [], "values": [], "labels": [], "detail": {}}
    d = df.copy()
    d["_bkt"] = d[date_col].dt.to_period(freq).dt.to_timestamp()
    if last_days and freq == "D":
        d = d[d[date_col] >= d[date_col].max() - pd.Timedelta(days=last_days)]
    g = d.groupby("_bkt")[value_col].sum().sort_index()
    if freq == "M" and len(g) > max_months:
        g = g.tail(max_months)
    two = d.groupby(["_bkt", sub_col])[value_col].sum()
    nuniq = d.groupby("_bkt")[sub_col].nunique()
    fmt = "%Y-%m" if freq == "M" else "%Y-%m-%d"
    detail = {}
    for bkt in g.index:
        key = bkt.strftime(fmt)
        try:
            ss = two.loc[bkt].sort_values(ascending=False).head(top_items)
        except KeyError:
            ss = pd.Series(dtype=float)
        kpis = [["Total", format_number(float(g[bkt]), "eur")],
                [sub_label.capitalize(), f"{int(nuniq.get(bkt, 0)):,}"]]
        detail[key] = {"kpis": kpis,
                       "toplists": {f"Top {sub_label}": [[str(n), format_number(float(v), "eur")] for n, v in ss.items()]}}
    return {"cats": [b.strftime(fmt) for b in g.index], "values": [float(v) for v in g.values],
            "labels": [format_number(float(v), "eur") for v in g.values], "detail": detail}


def render(filtered: dict, theme: str, audience: str, today=None, base=None) -> None:
    colors = atelier_colorway(theme)
    tx, investments, investors = filtered["transactions"], filtered["investments"], filtered["investors"]
    projects = filtered["projects"]
    # `base` = full dimension-scoped, as-of book (not time-windowed) -> used for the
    # explorers, the investor-base funnel and the top-investors leaderboard.
    base = base if base is not None else filtered
    base_investors = base["investors"]

    # investments enriched with project + investor names (for the explorers)
    biv = base["investments"].copy()
    if not biv.empty:
        biv = biv.merge(base["projects"][["project_id", "project_name", "status"]], on="project_id", how="left")
        biv = biv.merge(base["investors"][["investor_id", "name"]], on="investor_id", how="left") \
                 .rename(columns={"name": "inv_name"})

    # ---- deposits vs withdrawals ----
    with chart_card():
        grain = card_header("Deposits vs withdrawals vs net", subtitle="Wallet cash flow",
                            options=list(GRAIN_PERIOD.keys()), default="Monthly", key="activity_grain",
                            label="Granularity", help="Time granularity for the wallet cash-flow chart.")
        pc = GRAIN_PERIOD[grain]
        if tx.empty:
            st.info("No wallet activity in range.")
        else:
            t = tx.copy(); t["b"] = _bucket(t["date"], pc)
            dep = t[t.type == "Deposit"].groupby("b")["amount"].sum()
            wd = t[t.type == "Withdrawal"].groupby("b")["amount"].sum().abs()
            idx = sorted(set(dep.index) | set(wd.index))
            dep, wd = dep.reindex(idx, fill_value=0), wd.reindex(idx, fill_value=0)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=idx, y=dep.values, name="Deposits", marker_color=colors[0]))
            fig.add_trace(go.Bar(x=idx, y=-wd.values, name="Withdrawals", marker_color=colors[3]))
            fig.add_trace(go.Scatter(x=idx, y=(dep - wd).values, name="Net", line=dict(color=colors[1], width=3)))
            fig.update_layout(barmode="relative", **plotly_layout(theme, height=340))
            gradient_bars(fig)
            st.plotly_chart(fig, theme=None)

    # ---- invested amount (full width; select top project stages OR top investors) ----
    with chart_card():
        st.markdown('<div class="chart-title">Invested amount</div>'
                    '<div class="chart-sub">Capital deployed into loans · "Split by" → By month / By day (date axis), '
                    'or top project stages / investors · hover for the detail behind each</div>', unsafe_allow_html=True)
        if biv.empty:
            st.info("No investment activity in scope.")
        else:
            payload = {"By month": _time_payload(biv, "invested_date", "amount", "project_name", "projects", "M"),
                       "By day": _time_payload(biv, "invested_date", "amount", "project_name", "projects", "D", last_days=60),
                       "Project stage": _two_level_payload(biv, "project_name", "amount", "inv_name", "investors"),
                       "Investor": _two_level_payload(biv, "inv_name", "amount", "project_name", "projects")}
            components_hover.split_explorer(payload, theme, default_dim="By month", chart_type="Bars",
                                            height=520, panel_title="Detail", key="invested_explorer")

    # ---- collecting amount (full width; top collecting projects, hover top investors) ----
    with chart_card():
        st.markdown('<div class="chart-title">Servicing amount</div>'
                    '<div class="chart-sub">Capital invested into loans still raising funds · "Split by" → By month / By day '
                    '(date axis) or top projects · hover for its top investors</div>', unsafe_allow_html=True)
        coll_df = biv[biv["status"] == "Servicing"] if not biv.empty else biv
        if coll_df is None or coll_df.empty:
            st.info("No capital in collecting loans in scope.")
        else:
            payload = {"By month": _time_payload(coll_df, "invested_date", "amount", "project_name", "projects", "M"),
                       "By day": _time_payload(coll_df, "invested_date", "amount", "project_name", "projects", "D", last_days=60),
                       "Project": _two_level_payload(coll_df, "project_name", "amount", "inv_name", "investors")}
            components_hover.split_explorer(payload, theme, default_dim="By month", chart_type="Bars",
                                            height=520, panel_title="Detail", key="collecting_explorer")

    # ---- available amount (full width; top investors by un-invested wallet cash) ----
    with chart_card():
        st.markdown('<div class="chart-title">Available amount</div>'
                    '<div class="chart-sub">Deposited to wallet but not yet invested · "Split by" → By month / By day '
                    '(balance over time) or top investors · hover for the detail</div>', unsafe_allow_html=True)
        if base_investors.empty:
            st.info("No investors in scope.")
        else:
            # Investor snapshot dim (top by available wallet, hover -> their top projects)
            inv_by_investor = biv.groupby("investor_id")["amount"].sum() if not biv.empty else pd.Series(dtype=float)
            proj_by_investor = biv.groupby(["investor_id", "project_name"])["amount"].sum() if not biv.empty else None
            avail_top = base_investors.sort_values("wallet_balance", ascending=False).head(12)
            cats, vals, detail = [], [], {}
            for _, r in avail_top.iterrows():
                nm, w, iid = str(r["name"]), float(r["wallet_balance"]), r["investor_id"]
                cats.append(nm); vals.append(w)
                invested_tot = float(inv_by_investor.get(iid, 0.0))
                try:
                    their = proj_by_investor.loc[iid].sort_values(ascending=False).head(10)
                except (KeyError, AttributeError):
                    their = pd.Series(dtype=float)
                kpis = [["Available", format_number(w, "eur")], ["Invested", format_number(invested_tot, "eur")],
                        ["Tier", str(r.get("investor_tier", "—"))], ["Country", str(r.get("country", "—"))]]
                top = [[str(n), format_number(float(v), "eur")] for n, v in their.items()]
                detail[nm] = {"kpis": kpis, "toplists": {"Top projects": top}}
            investor_dim = {"cats": cats, "values": vals,
                            "labels": [format_number(v, "eur") for v in vals], "detail": detail}

            # available balance over time = cumulative deposits - cumulative invested
            btx = base["transactions"]
            dep_all = btx[btx["type"] == "Deposit"] if not btx.empty else btx
            snap_top = [[str(n), format_number(float(w), "eur")] for n, w in
                        base_investors.sort_values("wallet_balance", ascending=False).head(10)[["name", "wallet_balance"]].values]

            def _avail_time(freq, last_days=None, max_months=24):
                if dep_all is None or dep_all.empty:
                    return {"cats": [], "values": [], "labels": [], "detail": {}}
                dd = dep_all.copy(); dd["_b"] = dd["date"].dt.to_period(freq).dt.to_timestamp()
                dep_b = dd.groupby("_b")["amount"].sum()
                if not biv.empty:
                    ii = biv.copy(); ii["_b"] = ii["invested_date"].dt.to_period(freq).dt.to_timestamp()
                    inv_b = ii.groupby("_b")["amount"].sum()
                else:
                    inv_b = pd.Series(dtype=float)
                idx = sorted(set(dep_b.index) | set(inv_b.index))
                bal = (dep_b.reindex(idx).fillna(0).cumsum() - inv_b.reindex(idx).fillna(0).cumsum()).clip(lower=0)
                if last_days and freq == "D":
                    bal = bal[bal.index >= max(idx) - pd.Timedelta(days=last_days)]
                if freq == "M" and len(bal) > max_months:
                    bal = bal.tail(max_months)
                fmt = "%Y-%m" if freq == "M" else "%Y-%m-%d"
                det = {b.strftime(fmt): {"kpis": [["Available balance", format_number(float(v), "eur")]],
                                         "toplists": {"Top investors (by wallet)": snap_top}}
                       for b, v in bal.items()}
                return {"cats": [b.strftime(fmt) for b in bal.index], "values": [float(v) for v in bal.values],
                        "labels": [format_number(float(v), "eur") for v in bal.values], "detail": det}

            payload = {"By month": _avail_time("M"), "By day": _avail_time("D", last_days=60), "Investor": investor_dim}
            components_hover.split_explorer(payload, theme, default_dim="By month", chart_type="Bars",
                                            height=520, panel_title="Detail", key="available_explorer")

    # =========================== DEEP DIVE (collapsible) ===========================
    with deep_dive():
        # ---- investor base: net buckets (Bars/Donut + hover top-10 investors) ----
        with chart_card(deep=True):
            st.markdown('<div class="chart-title">Investor base — net buckets</div>'
                        '<div class="chart-sub">Registered · Identified · Active · Passive · each investor counted once · '
                        'Bars/Donut · hover a bucket for its top investors</div>', unsafe_allow_html=True)
            if base_investors.empty:
                st.info("No investors match the current filters.")
            else:
                now = pd.Timestamp(today) if today is not None else pd.Timestamp(base_investors["last_login"].max())
                six_mo = now - pd.DateOffset(months=6)
                inv2 = base_investors
                identified = inv2["identified"].fillna(False) if "identified" in inv2 else pd.Series(False, index=inv2.index)
                active = inv2["active"].fillna(False) if "active" in inv2 else pd.Series(False, index=inv2.index)
                recent = inv2["last_login"] >= six_mo if "last_login" in inv2 else pd.Series(False, index=inv2.index)
                bucket_masks = [("Registered", ~active & ~identified), ("Identified", ~active & identified),
                                ("Active", active & recent), ("Passive", active & ~recent)]
                labels = [b for b, _ in bucket_masks]
                vals = [int(m.sum()) for _, m in bucket_masks]
                total = max(sum(vals), 1)
                detail = {}
                for name, m in bucket_masks:
                    sub = inv2[m].sort_values("wallet_balance", ascending=False)
                    kpis = [["Investors", f"{len(sub):,}"],
                            ["Avg wallet", format_number(float(sub["wallet_balance"].mean()) if len(sub) else 0.0, "eur")],
                            ["Share", f"{len(sub) / total * 100:.1f}%"]]
                    top = [[str(n), format_number(float(w), "eur")]
                           for n, w in sub.head(10)[["name", "wallet_balance"]].values]
                    detail[name] = {"kpis": kpis, "toplists": {"Top 10 investors": top}}
                payload = {"Investor bucket": {"cats": labels, "values": [float(v) for v in vals],
                                               "labels": [f"{v:,}" for v in vals], "detail": detail}}
                components_hover.split_explorer(payload, theme, default_dim="Investor bucket", chart_type="Bars",
                                                height=520, panel_title="Bucket detail", key="investor_buckets_explorer")
                st.caption("Mutually exclusive buckets · Passive = funded wallet, no login in 6 months · illustrative.")

        # ---- top investors leaderboard (as-of book; filter by tier) ----
        with chart_card(deep=True):
            binv, binvest, btx, bproj = base["investors"], base["investments"], base["transactions"], base["projects"]
            hl, hr = st.columns([0.62, 0.38], vertical_alignment="center")
            with hl:
                st.markdown('<div class="chart-title">Top investors</div>'
                            '<div class="chart-sub">Total · invested · available · collecting · projects · last login · '
                            'scroll for more</div>', unsafe_allow_html=True)
            with hr:
                tiers = st.multiselect("Investor tier", ["Retail", "HNWI", "Professional"],
                                       default=["Retail", "HNWI", "Professional"], key="topinv_tier",
                                       label_visibility="collapsed", help="Show only the selected investor tier(s).")
            if binvest.empty:
                st.info("No investments in scope.")
            else:
                collecting_ids = set(bproj.loc[bproj.status == "Servicing", "project_id"]) if len(bproj) else set()
                inv = binvest.copy()
                inv["is_collecting"] = inv["project_id"].isin(collecting_ids)
                g = inv.groupby("investor_id").agg(invested=("amount", "sum"), n_proj=("project_id", "nunique")).reset_index()
                coll = inv[inv.is_collecting].groupby("investor_id")["amount"].sum().rename("collecting")
                g = g.merge(coll, on="investor_id", how="left").fillna({"collecting": 0})
                dep = btx[btx.type == "Deposit"].groupby("investor_id")["amount"].sum().rename("total") if len(btx) else pd.Series(dtype=float, name="total")
                g = g.merge(dep, on="investor_id", how="left").fillna({"total": 0})
                g = g.merge(binv[["investor_id", "name", "investor_tier", "country", "wallet_balance", "last_login"]],
                            on="investor_id", how="inner")
                if tiers:
                    g = g[g["investor_tier"].isin(tiers)]
                ranked = g.sort_values("invested", ascending=False).head(100)
                if ranked.empty:
                    st.info("No investors match the selected tier(s).")
                else:
                    full = pd.DataFrame({
                        "Investor": ranked["name"].values, "Tier": ranked["investor_tier"].values, "Country": ranked["country"].values,
                        "Total": [format_number(v, "eur") for v in ranked["total"]],
                        "Invested": [format_number(v, "eur") for v in ranked["invested"]],
                        "Available": [format_number(v, "eur") for v in ranked["wallet_balance"]],
                        "Servicing": [format_number(v, "eur") for v in ranked["collecting"]],
                        "# Proj.": [f"{int(v):,}" for v in ranked["n_proj"]],
                        "Last login": [pd.Timestamp(v).strftime("%Y-%m-%d") if pd.notna(v) else "—" for v in ranked["last_login"]],
                    })
                    bars = {"Invested": norm(ranked["invested"].tolist()),
                            "Available": norm(ranked["wallet_balance"].tolist())}
                    render_table(full, num_cols={"# Proj."}, badges={"Tier": TIER_BADGE}, bar_frac=bars,
                                 max_height=430, rank=True, export_name="activity_top_investors")
                    plat = float(binvest["amount"].sum()) or 1.0
                    top10_share = ranked.head(10)["invested"].sum() / plat * 100
                    st.caption(f"Showing top {len(ranked)} of {len(g):,} investors · top-10 hold {top10_share:.1f}% of invested capital.")

        # ---- resale market ----
        with chart_card(deep=True):
            card_header("Resale market", subtitle="Resale of existing stakes")
            sm = filtered["secondary_market"]
            if sm.empty:
                st.info("No resale market listings in range.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Listed (period)", format_number(float(sm["listed_price"].sum()), "eur"))
                c2.metric("Sold (period)", format_number(float(sm.loc[sm.status == "Sold", "listed_price"].sum()), "eur"))
                c3.metric("Sell-through rate", format_number(float((sm.status == "Sold").mean() * 100), "pct"))

        # ---- monthly wallet flows table ----
        with chart_card(deep=True):
            card_header("Monthly wallet flows", subtitle="Last 12 months · deposits, withdrawals, net")
            if tx.empty:
                st.info("No wallet activity in range.")
            else:
                t = tx.copy(); t["m"] = t["date"].dt.to_period("M").dt.to_timestamp()
                dep = t[t.type == "Deposit"].groupby("m")["amount"].sum()
                wd = t[t.type == "Withdrawal"].groupby("m")["amount"].sum().abs()
                idx = sorted(set(dep.index) | set(wd.index))[-12:]
                dep, wd = dep.reindex(idx, fill_value=0), wd.reindex(idx, fill_value=0)
                net = dep - wd
                rows = [{"Month": i.strftime("%Y-%m"), "Deposits": format_number(dep[i], "eur"),
                         "Withdrawals": format_number(wd[i], "eur"), "Net": format_number(net[i], "eur")} for i in idx]
                render_table(pd.DataFrame(rows), num_cols={"Deposits", "Withdrawals"},
                             bar_frac={"Net": norm([max(v, 0) for v in net.values])}, export_name="activity_monthly_flows")
