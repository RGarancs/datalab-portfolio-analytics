"""
smoke_test.py -- headless regression check for app.py via Streamlit's AppTest.

Exercises every palette, audience, dataset size, seed, reporting period,
split dimension, focus value, and per-view toggle, plus an empty-filter edge
case, asserting the script never raises.

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


def radio(at, key):
    return next(r for r in at.sidebar.radio if r.key == key)


def sc(at, label):
    return next((s for s in at.segmented_control if s.label == label), None)


def main() -> None:
    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()
    check("default load (Internal / Teal / Snapshot / Country)", at)

    for palette in ["light", "dark"]:
        radio(at, "theme").set_value(palette).run()
        check(f"palette={palette}", at)

    for aud in ["Investor-Facing", "Public Website", "Internal"]:
        radio(at, "audience_key" if False else None) if False else None
        # audience radio has no key; it's the 2nd sidebar radio
        at.sidebar.radio[1].set_value(aud).run()
        check(f"audience={aud}", at)

    for period in ["MTD", "YTD", "12MR", "Snapshot"]:
        w = sc(at, "Reporting period")
        w.set_value(period).run()
        check(f"period={period}", at)

    def split_sb():
        return next(s for s in at.selectbox if s.key == "split_label")
    for split in ["Project Type", "Rating", "Status", "Vintage (orig. quarter)",
                  "LTC band", "Loan size band", "Maturity bucket", "Investor Type",
                  "Investor Tier", "Country"]:
        split_sb().set_value(split).run()
        check(f"split={split}", at)

    # focus selectbox: pick a concrete value then back to All
    focus_sb = next((s for s in at.selectbox if s.key == "focus_value"), None)
    if focus_sb is not None and len(focus_sb.options) > 1:
        focus_sb.set_value(focus_sb.options[1]).run()
        check("focus set to first split value", at)
        next(s for s in at.selectbox if s.key == "focus_value").set_value("All").run()
        check("focus=All", at)

    for size in ["Preview (fast)", "Large (stress test)", "Realistic (default)"]:
        at.sidebar.selectbox[0].set_value(size).run()
        check(f"dataset size={size}", at)

    for label, seq in [("Unit", ["#", "%", "€"]), ("Granularity", ["Daily", "Annual", "Monthly"])]:
        w = sc(at, label)
        if w is None:
            continue
        for val in seq:
            w2 = sc(at, label)
            w2.set_value(val).run()
            check(f"{label}={val}", at)

    countries = at.sidebar.multiselect[0]
    original = list(countries.value)
    countries.set_value([]).run()
    check("countries cleared (empty filter)", at)
    at.sidebar.multiselect[0].set_value(original).run()
    check("countries restored", at)

    kpi_ms = at.sidebar.multiselect[-1]
    kpi_ms.set_value(["outstanding", "total_funded", "avg_ltv", "n_projects", "deposits_period"]).run()
    check("custom KPI selection", at)

    at.sidebar.number_input[0].set_value(7).run()
    check("seed=7", at)

    at.sidebar.button[0].click().run()
    check("regenerate button clicked", at)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S)")
        sys.exit(1)
    print(f"ALL CHECKS PASSED ({len(FAILURES)} failures)")


if __name__ == "__main__":
    main()
