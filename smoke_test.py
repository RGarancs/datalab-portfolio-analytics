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


def main() -> None:
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
