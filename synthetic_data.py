"""
synthetic_data.py
==================
Fully-linked SYNTHETIC dataset standing in for the real "Ledger" data
export (Clients/Debtors, Projects, Investors, Investments, Transactions,
Secondary Market) described in the data model.

Nothing here is real client, investor or project data -- every name,
amount and date is generated. Change `seed` to explore other draws.

Entity graph
------------
    clients (borrowers) 1---< projects
    investors            1---< investments >---1 projects
    investors            1---< transactions              (wallet ledger)
    investments           1---0..1 secondary_market       (resale listing)
    investors            1---< secondary_market.seller_investor_id
    investors            1---< secondary_market.buyer_investor_id

Simplifications made for this mockup (see README "Simplifications"):
    * `transactions` only carries Deposit / Withdrawal rows (wallet
      funding activity). Capital moving into loans is represented by
      `investments`; interest/principal flowing back is approximated
      at the project level (status / interest_rate / term_months)
      rather than posted as per-investor ledger rows.
    * Status transitions are drawn from hand-tuned probabilities keyed
      off loan age vs. term and rating -- not a real risk model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from faker import Faker

TODAY = pd.Timestamp("2026-08-01")

COUNTRIES = ["Netherlands", "Austria", "Czechia", "Portugal", "Denmark", "Ireland", "Slovenia", "Belgium"]
COUNTRY_WEIGHTS = [0.24, 0.19, 0.15, 0.12, 0.10, 0.09, 0.06, 0.05]

PROJECT_TYPES = ["Growth Facility", "Working-Capital Line", "Asset-Backed Loan", "Expansion Loan", "Transition Loan"]
PROJECT_TYPE_WEIGHTS = [0.26, 0.24, 0.22, 0.17, 0.11]

RATINGS = ["A", "B", "C", "D", "E"]
RATING_WEIGHTS = [0.15, 0.27, 0.30, 0.19, 0.09]
RATING_BASE_RATE = {"A": 7.2, "B": 8.6, "C": 10.1, "D": 11.9, "E": 14.2}
RATING_RISK = {"A": 0.012, "B": 0.028, "C": 0.055, "D": 0.092, "E": 0.15}

TERMS_MONTHS = [9, 12, 18, 24, 30, 48]
FUNDING_TARGETS = [75_000, 120_000, 180_000, 300_000, 450_000, 650_000, 900_000, 1_250_000]
FUNDING_TARGET_WEIGHTS = [0.12, 0.17, 0.19, 0.19, 0.15, 0.10, 0.05, 0.03]

OUTSTANDING_STATUSES = ["Available", "Servicing", "Active", "Restructured", "In Recovery"]
TERMINAL_STATUSES = ["Repaid", "Defaulted"]


def generate_clients(rng: np.random.Generator, fake: Faker, n: int) -> pd.DataFrame:
    rows = []
    for i in range(n):
        is_company = rng.random() < 0.75
        rows.append({
            "client_id": f"CL{i + 1:04d}",
            "name": fake.company() if is_company else fake.name(),
            "client_type": "Company" if is_company else "Individual",
            "country": rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS),
            "registration_date": TODAY - pd.Timedelta(days=int(rng.integers(60, 1800))),
            "kyc_status": rng.choice(["Verified", "Pending"], p=[0.93, 0.07]),
        })
    df = pd.DataFrame(rows)
    df["registration_date"] = pd.to_datetime(df["registration_date"])
    return df


def generate_investors(rng: np.random.Generator, fake: Faker, n: int) -> pd.DataFrame:
    days_back = rng.triangular(0, 45, 1825, size=n)  # skewed toward recent -> growth curve
    rows = []
    for i in range(n):
        is_inst = rng.random() < 0.09
        # available wallet balance -> tier (Retail <25k, HNWI 25-250k, Professional >250k)
        wallet = float(rng.lognormal(mean=9.1, sigma=1.2))
        if is_inst:
            wallet = max(wallet, float(rng.uniform(60_000, 450_000)))
        tier = "Retail" if wallet < 25_000 else ("HNWI" if wallet < 250_000 else "Professional")
        reg_date = TODAY - pd.Timedelta(days=int(days_back[i]))
        # last login skews recent; identified = KYC verified
        last_login = TODAY - pd.Timedelta(days=int(rng.triangular(0, 6, 420)))
        rows.append({
            "investor_id": f"IN{i + 1:05d}",
            "name": fake.company() if is_inst else fake.name(),
            "investor_type": "Institutional" if is_inst else "Individual",
            "investor_tier": tier,
            "wallet_balance": round(wallet, 2),
            "country": rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS),
            "registration_date": reg_date,
            "last_login": max(last_login, reg_date),
            "identified": bool(rng.random() < 0.90),
            "auto_invest": bool(rng.random() < 0.62),
        })
    df = pd.DataFrame(rows)
    df["registration_date"] = pd.to_datetime(df["registration_date"])
    df["last_login"] = pd.to_datetime(df["last_login"])
    return df


def _project_status(rng: np.random.Generator, age_months: float, term_months: int, risk: float) -> str:
    if age_months < 0.5:
        return rng.choice(["Available", "Recovery"], p=[0.4, 0.6])
    if age_months < 1.0:
        return rng.choice(["Recovery", "Active"], p=[0.25, 0.75])

    if age_months < term_months * 0.92:
        p_default = min(0.02 + risk * 0.3, 0.12)
        p_recovery = min(0.03 + risk * 0.3, 0.14)
        p_restructured = min(0.03 + risk * 0.15, 0.09)
        p_active = 1 - p_default - p_recovery - p_restructured
        probs = np.array([p_active, p_restructured, p_recovery, p_default])
        probs = probs / probs.sum()
        return rng.choice(["Active", "Restructured", "In Recovery", "Defaulted"], p=probs)

    p_default = min(0.06 + risk * 0.6, 0.30)
    p_recovery = min(0.05 + risk * 0.3, 0.14)
    p_restructured = min(0.02 + risk * 0.15, 0.08)
    p_repaid = 1 - p_default - p_recovery - p_restructured
    probs = np.array([p_repaid, p_default, p_recovery, p_restructured])
    probs = probs / probs.sum()
    return rng.choice(["Repaid", "Defaulted", "In Recovery", "Restructured"], p=probs)


def _ltc_band(v: float) -> str:
    if v < 50: return "<50%"
    if v < 65: return "50–65%"
    if v < 75: return "65–75%"
    return "75%+"


def _size_band(v: float) -> str:
    if v < 100_000: return "<€100K"
    if v < 250_000: return "€100–250K"
    if v < 500_000: return "€250–500K"
    if v < 1_000_000: return "€500K–1M"
    return "€1M+"


def _maturity_bucket(mat, today) -> str:
    if pd.isna(mat): return "No maturity"
    if mat <= today: return "Matured"
    d = (mat - today).days
    if d < 90: return "<3m"
    if d < 180: return "3–6m"
    if d < 365: return "6–12m"
    return "12m+"


def _vintage(start) -> str:
    q = pd.Timestamp(start).to_period("Q")
    return f"{q.year}-Q{q.quarter}"


def _one_stage(rng, fake, client, ptype, country, pid, group_id, group_name,
               stage_number, total_stages, start_date):
    """Build a single funding stage (one project row) of a group."""
    term = int(rng.choice(TERMS_MONTHS))
    age_months = (TODAY - start_date).days / 30.44
    rating = rng.choice(RATINGS, p=RATING_WEIGHTS)
    interest_rate = round(float(RATING_BASE_RATE[rating] + rng.normal(0, 0.5)), 2)
    ltc = round(float(np.clip(rng.normal(52, 11), 18, 82)), 1)
    funding_target = float(rng.choice(FUNDING_TARGETS, p=FUNDING_TARGET_WEIGHTS))
    status = _project_status(rng, age_months, term, RATING_RISK[rating])

    if status == "Available":
        funded_amount = 0.0
    elif status == "Recovery":
        funded_amount = round(funding_target * float(rng.uniform(0.1, 0.85)), 2)
    else:
        funded_amount = round(funding_target * float(rng.uniform(0.95, 1.0)), 2)

    funding_end = None if status == "Available" else start_date + pd.Timedelta(days=int(rng.integers(3, 22)))
    maturity_date = None if funding_end is None else funding_end + pd.DateOffset(months=term)

    default_date = None
    expected_recovery_months = None
    if status in ("Defaulted", "In Recovery"):
        distress_start = funding_end + pd.DateOffset(months=max(int(term * rng.uniform(0.3, 0.9)), 1))
        default_date = min(distress_start, TODAY)
        expected_recovery_months = int(rng.integers(3, 24))

    return {
        "project_id": f"PR{pid:04d}",
        "loan_category": "Business" if ptype == "Business Loan" else "Real Estate",
        "group_id": group_id,
        "group_name": group_name,
        "stage_number": stage_number,
        "total_stages": total_stages,
        "client_id": client["client_id"],
        "project_name": f"{group_name} — Stage {stage_number}",
        "project_type": ptype,
        "country": country,
        "rating": rating,
        "interest_rate": interest_rate,
        "ltc": ltc,
        "term_months": term,
        "funding_target": funding_target,
        "funded_amount": funded_amount,
        "status": status,
        "start_date": start_date,
        "funding_end_date": funding_end,
        "maturity_date": maturity_date,
        "default_date": default_date,
        "expected_recovery_months": expected_recovery_months,
    }


def generate_projects(rng: np.random.Generator, fake: Faker, clients: pd.DataFrame, n: int) -> pd.DataFrame:
    """Projects are funded in STAGES that belong to a project GROUP (a single
    development can be raised across several sequential tranches). Most groups
    are single-stage; some run 2-4 stages. `total_stages` is the planned count,
    `current_stage` (added below) is the latest stage launched so far."""
    client_lookup = clients[["client_id", "country"]].to_dict("records")
    rows = []
    pid = 0
    group_idx = 0
    # multi-stage groups are much more likely for Development / Bridge loans
    while pid < n:
        group_idx += 1
        client = client_lookup[int(rng.integers(0, len(client_lookup)))]
        country = client["country"] if rng.random() < 0.85 else rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS)
        ptype = rng.choice(PROJECT_TYPES, p=PROJECT_TYPE_WEIGHTS)
        multi_prone = ptype in ("Development Loan", "Bridge Loan", "Land Loan")
        total_stages = int(rng.choice([1, 2, 3, 4], p=[0.55, 0.25, 0.13, 0.07]) if multi_prone
                           else rng.choice([1, 2], p=[0.85, 0.15]))
        launched = int(rng.integers(1, total_stages + 1))
        group_id = f"GRP{group_idx:04d}"
        group_name = f"{fake.city()} {ptype.split()[0]}"
        group_start_back = int(rng.integers(30, 900))
        group_start = TODAY - pd.Timedelta(days=group_start_back)
        stage_gap = int(rng.integers(60, 210))
        for stage in range(1, launched + 1):
            if pid >= n:
                break
            pid += 1
            stage_start = min(group_start + pd.Timedelta(days=stage_gap * (stage - 1)), TODAY - pd.Timedelta(days=5))
            rows.append(_one_stage(rng, fake, client, ptype, country, pid, group_id,
                                   group_name, stage, total_stages, stage_start))

    df = pd.DataFrame(rows)
    for col in ["start_date", "funding_end_date", "maturity_date", "default_date"]:
        df[col] = pd.to_datetime(df[col])

    # current stage launched per group (handles groups truncated at n)
    df["current_stage"] = df.groupby("group_id")["stage_number"].transform("max")
    # useful derived groupings
    df["vintage"] = df["start_date"].map(_vintage)
    df["ltc_band"] = df["ltc"].map(_ltc_band)
    df["size_band"] = df["funding_target"].map(_size_band)
    df["maturity_bucket"] = df["maturity_date"].map(lambda m: _maturity_bucket(m, TODAY))
    return df


def generate_investments(rng: np.random.Generator, investors: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    investor_ids = investors["investor_id"].to_numpy()
    auto_pref = investors.set_index("investor_id")["auto_invest"]
    rows = []
    counter = 0
    for p in projects.itertuples():
        if p.status == "Available" or p.funded_amount <= 0:
            continue
        n_investors = int(np.clip(p.funded_amount / rng.uniform(450, 1900), 12, min(400, len(investor_ids))))
        chosen = rng.choice(investor_ids, size=n_investors, replace=False)
        weights = rng.dirichlet(np.full(n_investors, 0.7))
        amounts = weights * p.funded_amount
        window_days = max((p.funding_end_date - p.start_date).days, 1)
        for inv_id, amt in zip(chosen, amounts):
            counter += 1
            invested_date = p.start_date + pd.Timedelta(days=int(rng.integers(0, window_days + 1)))
            is_auto = bool(auto_pref.get(inv_id, False)) and rng.random() < 0.82
            rows.append({
                "investment_id": f"IV{counter:06d}",
                "investor_id": inv_id,
                "project_id": p.project_id,
                "amount": round(float(amt), 2),
                "invested_date": invested_date,
                "method": "Auto" if is_auto else "Manual",
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["investment_id", "investor_id", "project_id", "amount", "invested_date", "method"])
    df["invested_date"] = pd.to_datetime(df["invested_date"])
    return df


def generate_transactions(rng: np.random.Generator, investors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    counter = 0
    for inv in investors.itertuples():
        last_date = inv.registration_date
        if rng.random() < 0.12:      # ~12% register but never fund a wallet (not "active")
            continue
        n_dep = int(rng.integers(1, 6))
        # lifetime deposits scale with the investor's wallet balance
        lifetime = float(getattr(inv, "wallet_balance", 5000.0)) * float(rng.uniform(1.1, 2.2))
        split = rng.dirichlet(np.ones(n_dep))
        for k in range(n_dep):
            last_date = min(last_date + pd.Timedelta(days=int(rng.integers(0, 120))), TODAY)
            counter += 1
            rows.append({
                "transaction_id": f"TX{counter:07d}",
                "investor_id": inv.investor_id,
                "type": "Deposit",
                "amount": round(max(float(lifetime * split[k]), 5.0), 2),
                "date": last_date,
            })
        if rng.random() < 0.35:
            for _ in range(int(rng.integers(1, 3))):
                wd_date = min(last_date + pd.Timedelta(days=int(rng.integers(10, 200))), TODAY)
                counter += 1
                rows.append({
                    "transaction_id": f"TX{counter:07d}",
                    "investor_id": inv.investor_id,
                    "type": "Withdrawal",
                    "amount": -round(float(rng.lognormal(mean=6.4, sigma=0.9)), 2),
                    "date": wd_date,
                })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def generate_secondary_market(rng: np.random.Generator, investments: pd.DataFrame, investors: pd.DataFrame) -> pd.DataFrame:
    cols = ["listing_id", "investment_id", "seller_investor_id", "buyer_investor_id",
            "listed_date", "sold_date", "listed_price", "status"]
    if investments.empty:
        return pd.DataFrame(columns=cols)
    sample = investments.sample(frac=0.07, random_state=int(rng.integers(0, 1_000_000)))
    investor_ids = investors["investor_id"].to_numpy()
    rows = []
    for i, inv in enumerate(sample.itertuples(), start=1):
        listed_date = min(inv.invested_date + pd.Timedelta(days=int(rng.integers(20, 400))), TODAY)
        outcome = rng.choice(["Sold", "Listed", "Cancelled"], p=[0.55, 0.30, 0.15])
        sold_date, buyer = None, None
        if outcome == "Sold":
            sold_date = min(listed_date + pd.Timedelta(days=int(rng.integers(1, 30))), TODAY)
            candidates = investor_ids[investor_ids != inv.investor_id]
            buyer = rng.choice(candidates)
        rows.append({
            "listing_id": f"SM{i:05d}",
            "investment_id": inv.investment_id,
            "seller_investor_id": inv.investor_id,
            "buyer_investor_id": buyer,
            "listed_date": listed_date,
            "sold_date": sold_date,
            "listed_price": round(inv.amount * float(rng.uniform(0.97, 1.03)), 2),
            "status": outcome,
        })
    df = pd.DataFrame(rows, columns=cols)
    df["listed_date"] = pd.to_datetime(df["listed_date"])
    df["sold_date"] = pd.to_datetime(df["sold_date"])
    return df


def generate_dataset(seed: int = 2026, n_clients: int = 48, n_investors: int = 3600, n_projects: int = 164) -> dict:
    """Orchestrator: builds all six linked tables for one consistent, seeded scenario."""
    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    clients = generate_clients(rng, fake, n_clients)
    investors = generate_investors(rng, fake, n_investors)
    projects = generate_projects(rng, fake, clients, n_projects)
    investments = generate_investments(rng, investors, projects)
    transactions = generate_transactions(rng, investors)
    secondary_market = generate_secondary_market(rng, investments, investors)

    # active = investor has funded a wallet (any deposit)
    depositors = set(transactions.loc[transactions["type"] == "Deposit", "investor_id"].unique())
    investors["active"] = investors["investor_id"].isin(depositors)

    return {
        "clients": clients,
        "investors": investors,
        "projects": projects,
        "investments": investments,
        "transactions": transactions,
        "secondary_market": secondary_market,
        "generated_at": TODAY,
    }


if __name__ == "__main__":
    ds = generate_dataset()
    for name, table in ds.items():
        if isinstance(table, pd.DataFrame):
            print(f"{name:18s} {len(table):>7,} rows  {list(table.columns)}")
