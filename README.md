# Data Lab Portfolio Analytics — public preview

A portfolio and investor-reporting suite for a lending platform, built by
Rihards Garančs / Data Lab. This repository is the public preview: one
demo dataset with a fixed seed, dark theme only, no sidebar — the visuals
speak for themselves. Nothing here is client data.

Four views: overview, outstanding book, cumulative flows and risk & recovery.
Every chart has its own split and chart-type controls; tables export to CSV. No Faker, no Excel, no grid component — pandas, numpy and plotly only, so it runs in the browser.

Design: dark-teal surfaces, dark-gold accent, frosted-glass cards, Playfair
Display headline with gradient lettering — the Atelier house style.

Run locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

Runs in the browser (stlite) at https://rihardsgarancs.com/demos/analytics —
no server involved. Part of https://rihardsgarancs.com/company
