"""dims.py -- shared dimension registry used by the sidebar Split-by AND by the
in-chart split selectors on individual charts (Overview, Outstanding, Projects,
Risk, Analytics, My Portfolio). Single source of truth so every "split by"
control offers the same options.
"""
from __future__ import annotations

SPLIT_DIMS: dict[str, tuple[str, str]] = {
    "Country": ("projects", "country"),
    "Loan category": ("projects", "loan_category"),
    "Project Type": ("projects", "project_type"),
    "Rating": ("projects", "rating"),
    "Status": ("projects", "status"),
    "Vintage (orig. quarter)": ("projects", "vintage"),
    "LTC band": ("projects", "ltc_band"),
    "Loan size band": ("projects", "size_band"),
    "Maturity bucket": ("projects", "maturity_bucket"),
    "Investor Type": ("investors", "investor_type"),
    "Investor Tier": ("investors", "investor_tier"),
}

# subsets for charts that only make sense against one table
PROJECT_DIMS = {k: v for k, v in SPLIT_DIMS.items() if v[0] == "projects"}
INVESTOR_DIMS = {k: v for k, v in SPLIT_DIMS.items() if v[0] == "investors"}
