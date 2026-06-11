# Food Subscription Analytics Dashboard

Internal reporting tool for weekly generated dashboard to review performance and support business decisions.

The original version was built for a food subscription company to support weekly reporting and turn raw CSV exports of subscriptions and orders into weekly business KPIs: trials, conversion, churn, renewals, and order behaviour.

This public portfolio-safe mirror uses synthetic sample CSVs so the dashboard can be tested without exposing private customer/order exports or identifying the client.

## Purpose

The dashboard focuses on:

- Trial starts and conversion to full membership.
- Active members, churn, refunds, and renewals.
- Order behaviour after subscription.
- Customer/order matching across messy exports.
- Downloadable PDF reporting for weekly review.

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
python3 -m compileall app.py analytics data_validation.py
python3 scripts/smoke_test.py
streamlit run app.py --server.headless true --server.port 8508
curl http://localhost:8508/_stcore/health
```

Expected health response:

```text
ok
```

## Status

Portfolio-safe mirror of an internal analytics tool originally built for a food subscription company. This public version uses synthetic data and is not presented as the original private deployment or as a full production BI platform.

## License

This repository is shared publicly as portfolio/source-available material. Please contact me before reusing substantial parts of the code.
