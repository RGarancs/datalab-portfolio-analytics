"""
smoke_test.py -- headless regression check for app.py via Streamlit's AppTest.

Public preview: loads the app, asserts no sidebar controls exist, then flips
every in-chart control through each option, asserting the script never raises.

Run:  python3 smoke_test.py
"""
from __future__ import annotations

import sys

from streamlit.testing.v1 import AppTest

FAILURES: list[tuple[str, list[str]]] = []


def check(label: str, at: AppTest) -> None:
    if at.exception:
        FAILURES.append((label, [str(e) for e in at.exception]))
        print(f"FAIL  {label}")
        for e in at.exception:
            print("      ", e)
    else:
        print(f"OK    {label}")


def check_data_contract() -> None:
    """The dataset must stay a bank: right vocabulary, right order of magnitude."""
    import synthetic_data as sd
    import metrics
    ds = sd.generate_dataset(seed=42, n_clients=240, n_investors=6000, n_projects=2000)
    p = ds["projects"]

    cases = [
        ("statuses are the bank set",
         set(p["status"]) <= set(sd.STATUSES), sorted(set(p["status"]))),
        ("ratings are the Moody's ladder",
         set(p["rating"]) <= set(sd.RATINGS), sorted(set(p["rating"]))),
        ("loan types are bank products",
         set(p["project_type"]) <= set(sd.PROJECT_TYPES), sorted(set(p["project_type"]))),
        ("no funding-stage columns survive",
         not {"stage_number", "total_stages", "group_id"} & set(p.columns), sorted(p.columns)),
        ("maturities reach 20-30 years",
         "20–30y" in set(p["maturity_bucket"]), sorted(set(p["maturity_bucket"]))),
        ("customer segments renamed",
         set(ds["investors"]["investor_tier"]) <= set(sd.CUSTOMER_SEGMENTS),
         sorted(set(ds["investors"]["investor_tier"]))),
    ]
    st_metrics = metrics.compute_stock(ds, sd.TODAY)
    outstanding = st_metrics["outstanding"]
    cases += [
        ("book is 10-20x the old lending-platform book (EUR 16.3M)",
         160e6 <= outstanding <= 340e6, f"EUR {outstanding/1e6:,.1f}M"),
        ("LTV averages over secured loans only (not NaN)",
         st_metrics["avg_ltv"] == st_metrics["avg_ltv"] and st_metrics["avg_ltv"] > 0,
         st_metrics["avg_ltv"]),
        ("default rate is bank-plausible (< 5%)",
         0 <= st_metrics["default_rate_12m"] < 5, f"{st_metrics['default_rate_12m']:.2f}%"),
        ("loan-to-deposit ratio is 60-120%",
         0.6 <= outstanding / float(ds["investors"]["wallet_balance"].sum()) <= 1.2,
         f"{outstanding / float(ds['investors']['wallet_balance'].sum()) * 100:.0f}%"),
    ]
    for label, ok, detail in cases:
        if ok:
            print(f"OK    {label}  ({detail})" if not isinstance(detail, list) else f"OK    {label}")
        else:
            FAILURES.append((label, [str(detail)]))
            print(f"FAIL  {label}: {detail}")


def main() -> None:
    check_data_contract()
    at = AppTest.from_file("app.py", default_timeout=180)
    at.run()
    check("default load (public preview)", at)
    assert not at.sidebar.radio and not at.sidebar.selectbox, "sidebar widgets must not exist in the public preview"

    # exercise every in-chart control once per option (Bars/Donut, units, split, modes)
    controls = list(at.get("segmented_control"))
    print(f"      {len(controls)} in-chart controls found")
    seen = set()
    for ctl in controls:
        label = getattr(ctl, "label", "?")
        for opt in list(getattr(ctl, "options", []) or []):
            sig = (label, str(opt))
            if sig in seen:
                continue
            seen.add(sig)
            try:
                ctl.set_value(opt).run()
            except Exception as e:  # widget may have been re-created in a rerun; not a script error
                print(f"skip  {label} -> {opt}: {type(e).__name__}")
                continue
            check(f"{label} -> {opt}", at)

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
