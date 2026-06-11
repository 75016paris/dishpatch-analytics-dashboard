#!/usr/bin/env python3
"""Run a lightweight end-to-end smoke test with the synthetic sample CSVs."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import analytics as dp  # noqa: E402
from data_validation import validate_dashboard_inputs  # noqa: E402

SAMPLE_DATA = ROOT / "sample_data"
REFUND_PERIOD_DAYS = 14


def run_subscription_pipeline(today_date):
    today_iso = pd.to_datetime(today_date).isocalendar()

    sub_raw = pd.read_csv(SAMPLE_DATA / "subscriptions.csv")
    sub_df = dp.preprocess_data(sub_raw)
    sub_df, multisub_df = dp.remove_multi_subscriptions(sub_df)
    multisub_df = dp.remove_high_volume_customers(multisub_df)
    multisub_df = dp.custom_multisub_aggregation(multisub_df)
    sub_df = dp.integrate_with_subdf(sub_df, multisub_df)
    sub_df = dp.cancel_during_trial(sub_df)
    sub_df = dp.refund_period_end_utc(sub_df, REFUND_PERIOD_DAYS)
    sub_df = dp.canceled_during_refund_period(sub_df)
    sub_df = dp.full_member_status(sub_df, today_date)
    sub_df = dp.paying_members(sub_df)
    sub_df = dp.add_ended_at_utc(sub_df, today_date)
    sub_df = dp.calculate_duration(sub_df, today_date)

    full_members = dp.get_full_members_count(sub_df)
    renewal = dp.cus_renewal(sub_df, today_date, REFUND_PERIOD_DAYS)
    new_trials = dp.get_new_trial_last_week(sub_df, today_iso, weeks_back=1)

    return sub_df, renewal, full_members, new_trials


def run_order_pipeline(sub_df, renewal, today_date):
    order_raw = pd.read_csv(SAMPLE_DATA / "orders.csv")
    product_raw = pd.read_csv(SAMPLE_DATA / "products.csv")

    order_df = dp.preprocess_order(order_raw)
    order_df = dp.order_grouping(order_df)
    order_df = dp.clean_and_enrich_order_data(order_df)
    order_df = dp.item_name_cleaning(order_df)
    order_df = dp.pricing_items(order_df, product_raw)
    order_df = dp.flag_gift_and_note(order_df)

    sub_df = dp.renew_churn_status(sub_df, renewal)
    short_sub_df = dp.creating_short_sub_df(sub_df)
    merged_df = dp.merging_order_df_with_short_sub_df(order_df, short_sub_df)
    merged_df = dp.creating_year_col(merged_df)
    merged_df = dp.add_subscription_age(merged_df, today_date)

    return merged_df


def validate_sample_schemas():
    sub_raw = pd.read_csv(SAMPLE_DATA / "subscriptions.csv")
    order_raw = pd.read_csv(SAMPLE_DATA / "orders.csv")
    product_raw = pd.read_csv(SAMPLE_DATA / "products.csv")

    missing = validate_dashboard_inputs(sub_raw, order_raw, product_raw)
    assert missing == {}, missing

    missing = validate_dashboard_inputs(sub_raw.drop(columns=["Status"]), order_raw, product_raw)
    assert missing == {"subscription CSV": ["Status"]}, missing


def run_chart_smoke_tests(sub_df, merged_df, today_date):
    today_iso = pd.to_datetime(today_date).isocalendar()
    figures = []

    fig, _ = dp.plot_weekly_trials_all_time(sub_df, today_date, today_iso)
    figures.append(fig)

    fig, _ = dp.weekly_renewal_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
    figures.append(fig)

    fig_cohort, cohort_metrics = dp.plot_cohort_conversion_funnel(sub_df, today_date, today_iso)
    if fig_cohort is not None:
        figures.append(fig_cohort)
        fig, _ = dp.plot_cohort_conversion_funnel_comparison(sub_df, today_date, today_iso, cohort_metrics)
        figures.append(fig)

    figures.append(dp.plot_nb_cmd_by_customer_y1_y2(merged_df, "Full Member"))
    figures.append(dp.plot_nb_cmd_by_customer_y1_y2(merged_df, "Not Full Member"))

    for fig in figures:
        plt.close(fig)


def main():
    today_date = pd.Timestamp.now(tz="UTC").normalize()

    validate_sample_schemas()
    sub_df, renewal, full_members, new_trials = run_subscription_pipeline(today_date)
    merged_df = run_order_pipeline(sub_df, renewal, today_date)
    run_chart_smoke_tests(sub_df, merged_df, today_date)

    print("Smoke test passed")
    print(f"Subscriptions processed: {len(sub_df)}")
    print(f"Orders processed: {len(merged_df)}")
    print(f"Full members: {full_members['total']}")
    print(f"Conversion rate: {renewal['conversion_rate']}%")
    print(f"New trials last week: {new_trials['trials_count']}")


if __name__ == "__main__":
    main()
