"""
synthetic_data.py
==================
Fully-linked demonstration dataset for a retail & business BANK: customers,
borrowers, the loan book, disbursements, deposit-account activity, and loans
transferred to reinsurance.

Nothing here is real customer or loan data -- every name, amount and date is
generated from a seed.

Entity graph
------------
    borrowers  1---< loans
    customers  1---< disbursements >---1 loans
    customers  1---< transactions              (deposit account ledger)
    loans      1---0..1 reinsurance transfer

Table names kept from the original schema (projects / investors /
investments / secondary_market) so the reporting layer stays unchanged;
the meaning is the bank one described above.

Simplifications
---------------
    * `transactions` carries deposit-account movements only (credits and
      debits). Interest and principal flows on loans are approximated at
      loan level (status / interest_rate / term_months) rather than posted
      as individual ledger rows.
    * Status transitions are drawn from hand-tuned probabilities keyed off
      loan age vs. term and internal rating -- not a real IFRS 9 model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class Names:
    """Tiny seeded name generator: people, companies, cities. Pure Python,
    no dependency, deterministic for a given numpy Generator."""

    FIRST = ["Anna", "Lukas", "Sofie", "Jonas", "Eva", "Tomas", "Mila", "Pieter", "Hanna", "Marek",
             "Ines", "Niels", "Clara", "Jakub", "Lena", "Rui", "Emma", "Matej", "Nora", "Se\u00e1n",
             "Ida", "Bram", "Laura", "Ciar\u00e1n", "Julia", "Ole", "Tereza", "Joana", "Finn", "Maja"]
    LAST = ["de Vries", "Nov\u00e1k", "Jensen", "Silva", "Bauer", "Murphy", "Horvat", "Peeters", "Dvo\u0159\u00e1k",
            "Nielsen", "Costa", "Huber", "Walsh", "Kova\u010d", "Jansen", "Svoboda", "Larsen", "Pereira",
            "Steiner", "Byrne", "Zupan", "Claes", "Bakker", "\u010cern\u00fd", "Madsen", "Ferreira", "Gruber",
            "Kelly", "Kralj", "Mertens"]
    STEM = ["Nordhaven", "Alder", "Meridian", "Bluestone", "Harbour", "Linden", "Vantage", "Granite",
            "Clearwater", "Orchard", "Keystone", "Brightwater", "Ashford", "Summit", "Beacon", "Copper",
            "Atlas", "Lumen", "Marlow", "Fernhill", "Halcyon", "Ridgeway", "Sterling", "Willow"]
    KIND = ["Logistics", "Engineering", "Foods", "Retail", "Energy", "Textiles", "Components",
            "Packaging", "Construction", "Medical", "Software", "Mobility", "Agri", "Hospitality"]
    SUFFIX = ["B.V.", "GmbH", "s.r.o.", "Lda.", "A/S", "Ltd", "d.o.o.", "N.V.", "S.A.", "Group"]
    CITY = ["Utrecht", "Graz", "Brno", "Porto", "Aarhus", "Cork", "Maribor", "Ghent", "Leiden",
            "Linz", "Olomouc", "Braga", "Odense", "Galway", "Celje", "Leuven", "Haarlem", "Salzburg",
            "Plze\u0148", "Coimbra", "Aalborg", "Limerick", "Kranj", "Bruges", "Delft", "Innsbruck"]

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def _pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def name(self) -> str:
        return f"{self._pick(self.FIRST)} {self._pick(self.LAST)}"

    def company(self) -> str:
        return f"{self._pick(self.STEM)} {self._pick(self.KIND)} {self._pick(self.SUFFIX)}"

    def city(self) -> str:
        return self._pick(self.CITY)


TODAY = pd.Timestamp("2026-08-01")

COUNTRIES = ["Netherlands", "Austria", "Czechia", "Portugal", "Denmark", "Ireland", "Slovenia", "Belgium"]
COUNTRY_WEIGHTS = [0.24, 0.19, 0.15, 0.12, 0.10, 0.09, 0.06, 0.05]

# ---------------------------------------------------------------- loan products
# principal: (low, high) in EUR   terms: months   rate: product base APR
# ltv: (low, high) for secured lending, None when the product is unsecured
PRODUCTS: dict[str, dict] = {
    "Mortgage Loan":  dict(book="Retail",   weight=0.26, principal=(95_000, 640_000),
                           terms=[180, 240, 300, 360], rate=3.6, ltv=(55, 92), revolving=False, ref="MTG"),
    "Consumer Loan":  dict(book="Retail",   weight=0.24, principal=(2_500, 48_000),
                           terms=[12, 24, 36, 48, 60, 84], rate=8.4, ltv=None, revolving=False, ref="CNS"),
    "Credit Card":    dict(book="Retail",   weight=0.16, principal=(1_000, 22_000),
                           terms=[12], rate=17.9, ltv=None, revolving=True, ref="CRD"),
    "Car Loan":       dict(book="Retail",   weight=0.14, principal=(7_000, 62_000),
                           terms=[36, 48, 60, 72, 84], rate=5.3, ltv=(62, 95), revolving=False, ref="CAR"),
    "Business Loan":  dict(book="Business", weight=0.13, principal=(40_000, 2_600_000),
                           terms=[36, 60, 84, 120, 180], rate=5.1, ltv=(45, 82), revolving=False, ref="BUS"),
    "Overdraft":      dict(book="Business", weight=0.07, principal=(3_000, 70_000),
                           terms=[12], rate=12.6, ltv=None, revolving=True, ref="OVD"),
}
PROJECT_TYPES = list(PRODUCTS)
PROJECT_TYPE_WEIGHTS = [PRODUCTS[t]["weight"] for t in PROJECT_TYPES]

# ---------------------------------------------------------------- internal rating (Moody's scale)
RATINGS = ["Aaa", "Aa", "A", "Baa", "Ba", "B", "Caa"]
RATING_WEIGHTS = [0.05, 0.12, 0.22, 0.27, 0.18, 0.11, 0.05]
RATING_SPREAD = {"Aaa": -1.4, "Aa": -0.9, "A": -0.4, "Baa": 0.0, "Ba": 1.0, "B": 2.3, "Caa": 4.4}
RATING_RISK = {"Aaa": 0.002, "Aa": 0.005, "A": 0.012, "Baa": 0.024, "Ba": 0.050, "B": 0.088, "Caa": 0.155}

# ---------------------------------------------------------------- loan status
IN_PAYMENT = "In payment"
REPAID = "Repaid"
RISK_MITIGATION = "In risk mitigation"
COLLATERALIZED = "Collateralized"
REINSURED = "Sold to reinsurance"
DEFAULTED = "Defaulted"

OUTSTANDING_STATUSES = [IN_PAYMENT, RISK_MITIGATION, COLLATERALIZED, REINSURED]
TERMINAL_STATUSES = [REPAID, DEFAULTED]
STATUSES = [IN_PAYMENT, REPAID, RISK_MITIGATION, COLLATERALIZED, REINSURED, DEFAULTED]

CUSTOMER_SEGMENTS = ["Individual customers", "Business customers", "Institutional customers"]
CHANNELS = ["Branch", "Online", "Mobile app", "Broker"]
CHANNEL_WEIGHTS = [0.28, 0.31, 0.27, 0.14]


def generate_clients(rng: np.random.Generator, fake: "Names", n: int) -> pd.DataFrame:
    """Borrower registry -- the counterparties behind business lending."""
    rows = []
    for i in range(n):
        is_company = rng.random() < 0.82
        rows.append({
            "client_id": f"BR{i + 1:04d}",
            "name": fake.company() if is_company else fake.name(),
            "client_type": "Company" if is_company else "Sole trader",
            "country": rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS),
            "registration_date": TODAY - pd.Timedelta(days=int(rng.integers(180, 4500))),
            "kyc_status": rng.choice(["Verified", "Review due"], p=[0.94, 0.06]),
        })
    df = pd.DataFrame(rows)
    df["registration_date"] = pd.to_datetime(df["registration_date"])
    return df


def generate_investors(rng: np.random.Generator, fake: "Names", n: int) -> pd.DataFrame:
    """The bank's customer base: deposit balances, segment, acquisition channel."""
    days_back = rng.triangular(0, 300, 5400, size=n)      # long tail: an established bank
    seg_draw = rng.random(n)
    rows = []
    for i in range(n):
        d = seg_draw[i]
        if d < 0.80:
            segment, deposits = "Individual customers", float(rng.lognormal(mean=9.0, sigma=1.0))
        elif d < 0.955:
            segment, deposits = "Business customers", float(rng.lognormal(mean=11.2, sigma=0.9))
        else:
            segment, deposits = "Institutional customers", float(rng.uniform(120_000, 950_000))
        reg_date = TODAY - pd.Timedelta(days=int(days_back[i]))
        last_login = TODAY - pd.Timedelta(days=int(rng.triangular(0, 6, 420)))
        rows.append({
            "investor_id": f"CU{i + 1:06d}",
            "name": fake.name() if segment == "Individual customers" else fake.company(),
            "investor_type": rng.choice(CHANNELS, p=CHANNEL_WEIGHTS),   # acquisition channel
            "investor_tier": segment,                                    # customer segment
            "wallet_balance": round(deposits, 2),
            "country": rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS),
            "registration_date": reg_date,
            "last_login": max(last_login, reg_date),
            "identified": bool(rng.random() < 0.96),                     # KYC complete
            "auto_invest": bool(rng.random() < 0.58),                    # direct debit set up
        })
    df = pd.DataFrame(rows)
    df["registration_date"] = pd.to_datetime(df["registration_date"])
    df["last_login"] = pd.to_datetime(df["last_login"])
    return df


def _loan_status(rng: np.random.Generator, age_months: float, term_months: int, risk: float) -> str:
    """Live loans sit in the performing/distress ladder; matured loans close as
    Repaid or Defaulted. Probabilities scale with the internal rating's risk."""
    if age_months < term_months * 0.95:
        p_mitig = min(0.010 + risk * 0.50, 0.075)
        p_coll  = min(0.006 + risk * 0.42, 0.060)
        p_reins = min(0.004 + risk * 0.26, 0.038)
        p_pay = 1 - p_mitig - p_coll - p_reins
        probs = np.array([p_pay, p_mitig, p_coll, p_reins])
        return str(rng.choice([IN_PAYMENT, RISK_MITIGATION, COLLATERALIZED, REINSURED], p=probs / probs.sum()))

    p_default = min(0.012 + risk * 0.75, 0.13)
    p_reins = min(0.006 + risk * 0.22, 0.035)
    p_repaid = 1 - p_default - p_reins
    probs = np.array([p_repaid, p_default, p_reins])
    return str(rng.choice([REPAID, DEFAULTED, REINSURED], p=probs / probs.sum()))


def _ltv_band(v) -> str:
    if pd.isna(v): return "Unsecured"
    if v < 60: return "<60%"
    if v < 70: return "60–70%"
    if v < 80: return "70–80%"
    if v < 90: return "80–90%"
    return "90%+"


def _size_band(v: float) -> str:
    if v < 25_000: return "<€25K"
    if v < 100_000: return "€25–100K"
    if v < 250_000: return "€100–250K"
    if v < 500_000: return "€250–500K"
    if v < 1_000_000: return "€500K–1M"
    return "€1M+"


def _maturity_bucket(mat, today) -> str:
    if pd.isna(mat): return "No maturity"
    if mat <= today: return "Matured"
    y = (mat - today).days / 365.25
    if y < 1: return "<1y"
    if y < 3: return "1–3y"
    if y < 5: return "3–5y"
    if y < 10: return "5–10y"
    if y < 20: return "10–20y"
    return "20–30y"


def _vintage(start) -> str:
    q = pd.Timestamp(start).to_period("Q")
    return f"{q.year}-Q{q.quarter}"


def generate_projects(rng: np.random.Generator, fake: "Names", clients: pd.DataFrame,
                      customers: pd.DataFrame, n: int) -> pd.DataFrame:
    """The loan book. One row = one loan account."""
    business_borrowers = clients.to_dict("records")
    retail_ids = customers.loc[customers["investor_tier"] == "Individual customers", "investor_id"].to_numpy()
    corp_ids = customers.loc[customers["investor_tier"] != "Individual customers", "investor_id"].to_numpy()
    if len(retail_ids) == 0:
        retail_ids = customers["investor_id"].to_numpy()
    if len(corp_ids) == 0:
        corp_ids = customers["investor_id"].to_numpy()

    rows = []
    for i in range(n):
        ptype = str(rng.choice(PROJECT_TYPES, p=PROJECT_TYPE_WEIGHTS))
        cfg = PRODUCTS[ptype]
        book = cfg["book"]

        if book == "Business":
            borrower = business_borrowers[int(rng.integers(len(business_borrowers)))]
            client_id, country = borrower["client_id"], borrower["country"]
            customer_id = str(rng.choice(corp_ids))
        else:
            client_id = ""
            customer_id = str(rng.choice(retail_ids))
            country = str(rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS))

        term = int(rng.choice(cfg["terms"]))
        # originations spread over the last 12 years, weighted to recent years
        age_months = float(min(rng.triangular(0, 26, 144), term * 1.35))
        start_date = TODAY - pd.Timedelta(days=int(age_months * 30.44))

        rating = str(rng.choice(RATINGS, p=RATING_WEIGHTS))
        lo, hi = cfg["principal"]
        # log-uniform draw: many small loans, a thin tail of large ones
        principal = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        principal = round(principal / 100) * 100
        interest_rate = round(float(cfg["rate"] + RATING_SPREAD[rating] + rng.normal(0, 0.35)), 2)
        interest_rate = float(np.clip(interest_rate, 1.6, 24.0))

        ltv = (round(float(np.clip(rng.normal(np.mean(cfg["ltv"]), 9), cfg["ltv"][0], cfg["ltv"][1])), 1)
               if cfg["ltv"] else np.nan)

        # revolving facilities roll over on an annual review, so they never
        # "mature" out of the book the way a term loan does
        status_age = min(age_months, term * 0.5) if cfg["revolving"] else age_months
        status = _loan_status(rng, status_age, term, RATING_RISK[rating])
        # revolving products are drawn against a limit; term products are fully disbursed
        drawn = float(rng.uniform(0.18, 0.94)) if cfg["revolving"] else float(rng.uniform(0.97, 1.0))
        disbursed = round(principal * drawn, 2)

        funding_end = start_date + pd.Timedelta(days=int(rng.integers(1, 12)))
        if cfg["revolving"]:
            maturity_date = TODAY + pd.DateOffset(months=int(rng.integers(1, 13)))   # next review
        else:
            maturity_date = funding_end + pd.DateOffset(months=term)

        default_date = None
        expected_recovery_months = None
        if status in (DEFAULTED, REINSURED, COLLATERALIZED):
            distress = funding_end + pd.DateOffset(months=max(int(term * rng.uniform(0.25, 0.9)), 1))
            default_date = min(distress, TODAY)
            expected_recovery_months = int(rng.integers(3, 30))

        ref = f"{cfg['ref']}-{i + 1:05d}"
        rows.append({
            "project_id": f"LN{i + 1:05d}",
            "loan_category": book,
            "loan_ref": ref,
            "client_id": client_id,
            "customer_id": customer_id,
            "project_name": f"{ptype.replace(' Loan', '')} {ref} · {fake.city()}",
            "project_type": ptype,
            "country": country,
            "rating": rating,
            "interest_rate": interest_rate,
            "ltc": ltv,
            "term_months": term,
            "funding_target": principal,
            "funded_amount": disbursed,
            "status": status,
            "start_date": start_date,
            "funding_end_date": funding_end,
            "maturity_date": maturity_date,
            "default_date": default_date,
            "expected_recovery_months": expected_recovery_months,
        })

    df = pd.DataFrame(rows)
    for col in ["start_date", "funding_end_date", "maturity_date", "default_date"]:
        df[col] = pd.to_datetime(df[col])
    df["vintage"] = df["start_date"].map(_vintage)
    df["ltc_band"] = df["ltc"].map(_ltv_band)
    df["size_band"] = df["funding_target"].map(_size_band)
    df["maturity_bucket"] = df["maturity_date"].map(lambda m: _maturity_bucket(m, TODAY))
    return df


def generate_investments(rng: np.random.Generator, investors: pd.DataFrame,
                         projects: pd.DataFrame) -> pd.DataFrame:
    """Disbursements: money paid out on each loan, attributed to the borrowing
    customer. Term products draw once; revolving products draw repeatedly."""
    rows = []
    counter = 0
    for p in projects.itertuples():
        if p.funded_amount <= 0:
            continue
        revolving = PRODUCTS[p.project_type]["revolving"]
        n_draws = int(rng.integers(3, 9)) if revolving else int(rng.integers(1, 3))
        weights = rng.dirichlet(np.full(n_draws, 1.4))
        span = max((TODAY - p.funding_end_date).days, 1) if revolving else 30
        for w in weights:
            counter += 1
            offset = int(rng.integers(0, span)) if revolving else int(rng.integers(0, 12))
            rows.append({
                "investment_id": f"DB{counter:07d}",
                "investor_id": p.customer_id,
                "project_id": p.project_id,
                "amount": round(float(w) * float(p.funded_amount), 2),
                "invested_date": min(p.funding_end_date + pd.Timedelta(days=offset), TODAY),
                "method": "Scheduled" if revolving else "Single drawdown",
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["investment_id", "investor_id", "project_id",
                                     "amount", "invested_date", "method"])
    df["invested_date"] = pd.to_datetime(df["invested_date"])
    return df


def generate_transactions(rng: np.random.Generator, investors: pd.DataFrame) -> pd.DataFrame:
    """Deposit-account ledger: credits (salary, turnover, transfers in) and debits.
    Vectorised -- the customer base is large and this runs in the browser."""
    cols = ["transaction_id", "investor_id", "type", "amount", "date"]
    n = len(investors)
    if n == 0:
        return pd.DataFrame(columns=cols)

    ids = investors["investor_id"].to_numpy()
    bal = investors["wallet_balance"].to_numpy(dtype=float)
    reg = investors["registration_date"].to_numpy().astype("datetime64[D]")
    today = np.datetime64(TODAY, "D")
    span = np.maximum((today - reg) / np.timedelta64(1, "D"), 1.0)

    holds_account = rng.random(n) < 0.94          # the rest are dormant / product-only
    # np.intp: index/count arrays must match the platform word size -- Pyodide
    # (WASM) is 32-bit, where a default int64 count array fails np.repeat
    owners = np.flatnonzero(holds_account).astype(np.intp)

    def block(kind: str, per_lo: int, per_hi: int, frac_lo: float, frac_hi: float, sign: int):
        counts = rng.integers(per_lo, per_hi, size=owners.size).astype(np.intp)
        who = np.repeat(owners, counts)
        total = who.size
        if total == 0:
            return None
        amt = bal[who] * rng.uniform(frac_lo, frac_hi, size=total) * sign
        offs = (rng.random(total) * span[who]).astype("int64")
        dates = reg[who] + offs.astype("timedelta64[D]")
        return pd.DataFrame({
            "investor_id": ids[who],
            "type": kind,
            "amount": np.round(amt, 2),
            "date": dates,
        })

    parts = [b for b in (block("Deposit", 3, 10, 0.05, 0.38, 1),
                         block("Withdrawal", 1, 7, 0.03, 0.24, -1)) if b is not None]
    if not parts:
        return pd.DataFrame(columns=cols)
    df = pd.concat(parts, ignore_index=True).sort_values("date", kind="stable").reset_index(drop=True)
    df["transaction_id"] = [f"TX{i + 1:08d}" for i in range(len(df))]
    df["date"] = pd.to_datetime(df["date"])
    return df[cols]


def generate_secondary_market(rng: np.random.Generator, investments: pd.DataFrame,
                              investors: pd.DataFrame, projects: pd.DataFrame | None = None) -> pd.DataFrame:
    """Loans transferred to reinsurance: the register behind the
    'Sold to reinsurance' status."""
    cols = ["listing_id", "investment_id", "seller_investor_id", "buyer_investor_id",
            "listed_date", "sold_date", "listed_price", "status"]
    if investments.empty or projects is None:
        return pd.DataFrame(columns=cols)

    reinsured = set(projects.loc[projects["status"] == REINSURED, "project_id"])
    pool = investments[investments["project_id"].isin(reinsured)]
    if pool.empty:
        return pd.DataFrame(columns=cols)
    pool = pool.drop_duplicates("project_id")

    counterparties = ["Meridian Re", "Nordhaven Re", "Atlas Credit Re", "Halcyon Assurance"]
    n = len(pool)
    offs = rng.integers(30, 420, size=n)
    listed = np.minimum(pool["invested_date"].to_numpy().astype("datetime64[D]")
                        + offs.astype("timedelta64[D]"), np.datetime64(TODAY, "D"))
    settle = np.minimum(listed + rng.integers(5, 45, size=n).astype("timedelta64[D]"),
                        np.datetime64(TODAY, "D"))
    df = pd.DataFrame({
        "listing_id": [f"RI{i + 1:05d}" for i in range(n)],
        "investment_id": pool["investment_id"].to_numpy(),
        "seller_investor_id": pool["investor_id"].to_numpy(),
        "buyer_investor_id": [counterparties[int(i)] for i in rng.integers(0, len(counterparties), size=n)],
        "listed_date": listed,
        "sold_date": settle,
        "listed_price": np.round(pool["amount"].to_numpy() * rng.uniform(0.62, 0.88, size=n), 2),
        "status": "Transferred",
    })
    df["listed_date"] = pd.to_datetime(df["listed_date"])
    df["sold_date"] = pd.to_datetime(df["sold_date"])
    return df[cols]


def generate_dataset(seed: int = 2026, n_clients: int = 240, n_investors: int = 6000,
                     n_projects: int = 2000) -> dict:
    """Orchestrator: builds the linked bank tables for one seeded scenario."""
    rng = np.random.default_rng(seed)
    fake = Names(np.random.default_rng(seed + 7))

    clients = generate_clients(rng, fake, n_clients)
    investors = generate_investors(rng, fake, n_investors)
    projects = generate_projects(rng, fake, clients, investors, n_projects)
    investments = generate_investments(rng, investors, projects)
    transactions = generate_transactions(rng, investors)
    secondary_market = generate_secondary_market(rng, investments, investors, projects)

    # "active" = the customer uses a deposit account
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
            print(f"{name:18s} {len(table):>8,} rows")
    p = ds["projects"]
    print(f"\nbook          €{p.funded_amount.sum()/1e6:,.1f}M originated")
    live = p[p.status.isin(OUTSTANDING_STATUSES)]
    print(f"outstanding   €{live.funded_amount.sum()/1e6:,.1f}M over {len(live):,} live loans")
    print("\nby product:")
    print(p.groupby("project_type").funded_amount.agg(["count", "sum", "mean"]).sort_values("sum", ascending=False))
    print("\nby status:"); print(p.status.value_counts())
    print("\nby rating:"); print(p.rating.value_counts().reindex(RATINGS))
    print("\nmaturity:"); print(p.maturity_bucket.value_counts())
