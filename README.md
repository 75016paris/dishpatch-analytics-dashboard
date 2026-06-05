# Dishpatch Analytics Dashboard

Streamlit analytics dashboard prototype for subscription and order data.

This public mirror uses synthetic sample CSVs so the dashboard can be tested without private customer/order exports.

## What it demonstrates

- CSV cleaning and transformation with pandas.
- Subscription lifecycle analytics: trials, conversions, churn, renewals, active members.
- Order analytics: first orders, order frequency, gifts/notes, item pricing, customer behavior.
- Business KPI dashboarding with Streamlit, matplotlib and seaborn.
- PDF report generation with matplotlib.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the Streamlit URL, then upload the sample files:

1. `sample_data/subscriptions.csv`
2. `sample_data/orders.csv`
3. `sample_data/products.csv`

## Data

The sample data is synthetic and generated for this public mirror. It is shaped like subscription, order, and product exports, but it does not contain real customer names, emails, payments, or order history.

See `DATA_SCHEMA.md` for column notes.

## Verification

Smoke check:

```bash
python3 -m compileall app.py DISHPATCH.py
streamlit run app.py --server.headless true --server.port 8508
curl http://localhost:8508/_stcore/health
```

Expected health response:

```text
ok
```

## Status

Prototype/portfolio project. It is useful to demonstrate business analytics, KPI design, CSV cleaning, and dashboard/reporting workflows. It is not presented as a production BI platform.

## License

This repository is shared publicly as portfolio/source-available material. Please contact me before reusing substantial parts of the code.
