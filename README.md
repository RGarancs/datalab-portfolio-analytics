# Data Lab Banking Analytics — public preview

A loan-book and customer reporting dashboard for a retail and business bank,
built by Rihards Garančs / Data Lab. This repository is the public preview:
one demo dataset with a fixed seed, dark theme only, no sidebar — the visuals
speak for themselves. Nothing here is client data.

The book: ~€330M originated, ~€273M outstanding across 2,000 loans and 6,000
customers. Products are mortgages, consumer loans, business loans, car loans,
credit cards and overdrafts; credit quality runs the Moody's ladder from Aaa to
Caa; loans sit in payment, in risk mitigation, collateralized, sold to
reinsurance, defaulted or repaid.

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
