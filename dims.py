"""dims.py -- shared dimension registry used by every in-chart "Split by"
control (Overview, Outstanding, Risk). Single source of truth so each chart
offers the same breakdowns of the loan book and the customer base.
"""
from __future__ import annotations

SPLIT_DIMS: dict[str, tuple[str, str]] = {
    "Country": ("projects", "country"),
    "Loan book": ("projects", "loan_category"),
    "Loan type": ("projects", "project_type"),
    "Internal rating": ("projects", "rating"),
    "Status": ("projects", "status"),
    "Vintage (origination quarter)": ("projects", "vintage"),
    "LTV band": ("projects", "ltc_band"),
    "Loan size band": ("projects", "size_band"),
    "Maturity bucket": ("projects", "maturity_bucket"),
    "Acquisition channel": ("investors", "investor_type"),
    "Customer segment": ("investors", "investor_tier"),
}

# subsets for charts that only make sense against one table
LOAN_DIMS = {k: v for k, v in SPLIT_DIMS.items() if v[0] == "projects"}
CUSTOMER_DIMS = {k: v for k, v in SPLIT_DIMS.items() if v[0] == "investors"}

# backwards-compatible aliases
PROJECT_DIMS = LOAN_DIMS
INVESTOR_DIMS = CUSTOMER_DIMS
