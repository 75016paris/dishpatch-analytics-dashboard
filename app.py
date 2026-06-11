# app.py
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from data_validation import validate_dashboard_inputs
from analytics.cohorts import (
    plot_cohort_conversion_funnel,
    plot_cohort_conversion_funnel_comparison,
)
from analytics.orders import (
    after_sub_7,
    clean_and_enrich_order_data,
    creating_short_sub_df,
    creating_year_col,
    find_nb_cmd,
    flag_gift_and_note,
    item_name_cleaning,
    merging_order_df_with_short_sub_df,
    order_grouping,
    preprocess_order,
    pricing_items,
    renew_churn_status,
    add_subscription_age,
)
from analytics.plots import (
    discount_vendor,
    plot_first_order_3,
    plot_how_many_days_after_sub,
    plot_nb_cmd_by_customer_10_less,
    plot_nb_cmd_by_customer_y1_y2,
    plot_price_distribution,
    plot_renew_churn_metrics,
    plot_simple_and_complex_order,
)
from analytics.subscriptions import (
    add_ended_at_utc,
    calculate_duration,
    cancel_during_trial,
    canceled_during_refund_period,
    cus_renewal,
    custom_multisub_aggregation,
    full_member_status,
    get_churn_members_last_week,
    get_full_members_count,
    get_new_full_members_last_week,
    get_new_trial_last_week,
    integrate_with_subdf,
    paying_members,
    preprocess_data,
    refund_period_end_utc,
    remove_high_volume_customers,
    remove_multi_subscriptions,
)
from analytics.weekly_metrics import (
    calculate_target_iso_week,
    get_iso_week_bounds,
    plot_weekly_trials_8_weeks,
    plot_weekly_trials_all_time,
    weekly_flow_8_weeks,
    weekly_flow_all_time,
    weekly_renewal_flow_8_weeks,
    weekly_renewal_flow_all_time,
)


REFUND_PERIOD_DAYS = 14
SAMPLE_DATA_DIR = Path(__file__).resolve().parent / "sample_data"
SAMPLE_SUBSCRIPTION_DATE_COLUMNS = [
    "Created (UTC)",
    "Start (UTC)",
    "Current Period Start (UTC)",
    "Current Period End (UTC)",
    "Trial Start (UTC)",
    "Trial End (UTC)",
    "Canceled At (UTC)",
    "Ended At (UTC)",
]
SAMPLE_ANCHOR_DATE_COLUMNS = [
    "Created (UTC)",
    "Start (UTC)",
    "Current Period Start (UTC)",
    "Canceled At (UTC)",
    "Ended At (UTC)",
]


st.set_page_config(
    page_title="Subscription Analytics",
    layout="wide"
)


st.markdown("""
<style>
[data-testid="stMetricLabel"] p {
    font-size: 20px !important;
}

[data-testid="stMetricValue"] {
    font-size: 23px !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div style='margin: 1px 0;'></div>", unsafe_allow_html=True)


st.title("Subscription Analytics Dashboard")
st.markdown("""
*Portfolio-safe mirror of an internal weekly business review tool for a food subscription company. The dashboard turns subscription, order, and product CSV exports into KPIs and charts for acquisition, conversion, retention, churn, renewals, and post-subscription order behaviour.*
""")

today_date = pd.Timestamp.now(tz='UTC').normalize()
today_iso = pd.to_datetime(today_date).isocalendar()

for key in ("sample_subscriptions_df", "sample_orders_df", "sample_products_df", "sample_generated_for"):
    st.session_state.setdefault(key, None)
st.session_state.setdefault("inputs_collapsed", False)


def shift_dates_to_today(subscriptions, orders):
    """Shift bundled sample dates so the latest real event lands on today."""
    anchor_dates = []
    for column in SAMPLE_ANCHOR_DATE_COLUMNS:
        parsed = pd.to_datetime(subscriptions[column], errors='coerce', utc=True)
        if parsed.notna().any():
            anchor_dates.append(parsed.max())
    if not anchor_dates:
        return subscriptions, orders

    day_offset = int((today_date - max(anchor_dates).normalize()).days)
    if day_offset == 0:
        return subscriptions, orders

    subscriptions = subscriptions.copy()
    orders = orders.copy()
    for column in SAMPLE_SUBSCRIPTION_DATE_COLUMNS:
        shifted = pd.to_datetime(subscriptions[column], errors='coerce', utc=True) + pd.Timedelta(days=day_offset)
        subscriptions[column] = shifted.map(lambda value: value.isoformat() if pd.notna(value) else pd.NA)

    shifted_paid_at = pd.to_datetime(orders['Paid at'], errors='coerce', utc=True) + pd.Timedelta(days=day_offset)
    orders['Paid at'] = shifted_paid_at.map(lambda value: value.isoformat() if pd.notna(value) else pd.NA)
    return subscriptions, orders


def load_current_sample_file(file_key):
    """Load bundled anonymized sample data and shift dates up to today."""
    subscriptions = pd.read_csv(SAMPLE_DATA_DIR / "subscriptions.csv", low_memory=False)
    orders = pd.read_csv(SAMPLE_DATA_DIR / "orders.csv", low_memory=False)
    products = pd.read_csv(SAMPLE_DATA_DIR / "products.csv", low_memory=False)
    subscriptions, orders = shift_dates_to_today(subscriptions, orders)

    st.session_state["sample_generated_for"] = today_date.strftime("%Y-%m-%d")
    if file_key == "subscriptions":
        st.session_state["sample_subscriptions_df"] = subscriptions
    elif file_key == "orders":
        st.session_state["sample_orders_df"] = orders
    elif file_key == "products":
        st.session_state["sample_products_df"] = products


with st.expander("Data inputs", expanded=not st.session_state["inputs_collapsed"]):
    st.info("Upload the three CSV exports, or click the sample link under each uploader. Each sample link regenerates data up to today.")

    uploaded_file = st.file_uploader("Upload subscription CSV", type="csv")
    if st.button("Generate sample subscriptions.csv"):
        load_current_sample_file("subscriptions")
    if st.session_state["sample_subscriptions_df"] is not None and uploaded_file is None:
        st.caption(f"Sample subscriptions.csv selected through {st.session_state['sample_generated_for']}")

    uploaded_file2 = st.file_uploader("Upload orders CSV", type="csv")
    if st.button("Generate sample orders.csv"):
        load_current_sample_file("orders")
    if st.session_state["sample_orders_df"] is not None and uploaded_file2 is None:
        st.caption(f"Sample orders.csv selected through {st.session_state['sample_generated_for']}")

    uploaded_file3 = st.file_uploader("Upload product CSV", type="csv")
    if st.button("Generate sample products.csv"):
        load_current_sample_file("products")
    if st.session_state["sample_products_df"] is not None and uploaded_file3 is None:
        st.caption(f"Sample products.csv selected through {st.session_state['sample_generated_for']}")

    if st.button("Clear selected sample CSVs"):
        st.session_state["sample_subscriptions_df"] = None
        st.session_state["sample_orders_df"] = None
        st.session_state["sample_products_df"] = None
        st.session_state["sample_generated_for"] = None
        st.session_state["inputs_collapsed"] = False
        st.rerun()

sub_raw = pd.read_csv(uploaded_file) if uploaded_file is not None else st.session_state["sample_subscriptions_df"]
order_raw = pd.read_csv(uploaded_file2) if uploaded_file2 is not None else st.session_state["sample_orders_df"]
product_raw = pd.read_csv(uploaded_file3) if uploaded_file3 is not None else st.session_state["sample_products_df"]

inputs_loaded = sub_raw is not None and order_raw is not None and product_raw is not None
if inputs_loaded and not st.session_state["inputs_collapsed"]:
    st.session_state["inputs_collapsed"] = True
    st.rerun()
if inputs_loaded:
    st.success("CSV inputs loaded. Open Data inputs above to change files or samples.")

if sub_raw is not None and order_raw is not None and product_raw is not None:
    with st.spinner('Processing your data... This may take a moment.'):

        missing_columns = validate_dashboard_inputs(sub_raw, order_raw, product_raw)
        if missing_columns:
            st.error("One or more uploaded files do not match the expected export schema.")
            for file_label, columns in missing_columns.items():
                st.markdown(f"**{file_label}** is missing: `{', '.join(columns)}`")
            st.stop()

        sub_df = preprocess_data(sub_raw)
        sub_df, multisub_df = remove_multi_subscriptions(sub_df)
        multisub_df = remove_high_volume_customers(multisub_df)
        multisub_df = custom_multisub_aggregation(multisub_df)
        combined_df = integrate_with_subdf(sub_df, multisub_df)
        sub_df = combined_df.copy()
        sub_df = cancel_during_trial(sub_df)
        sub_df = refund_period_end_utc(sub_df, REFUND_PERIOD_DAYS)
        sub_df = canceled_during_refund_period(sub_df)
        sub_df = full_member_status(sub_df, today_date)
        sub_df = paying_members(sub_df)
        sub_df = add_ended_at_utc(sub_df, today_date)
        sub_df = calculate_duration(sub_df, today_date)
        dict_full_member = get_full_members_count(sub_df)
        new_trial_last_week = get_new_trial_last_week(sub_df, today_iso, weeks_back=1)
        new_trial_prev_week = get_new_trial_last_week(sub_df, today_iso, weeks_back=2)
        last_week_churned_members = get_churn_members_last_week(sub_df, today_iso, weeks_back=1)
        prev_week_churned_members = get_churn_members_last_week(sub_df, today_iso, weeks_back=2)
        renewal_dict = cus_renewal(sub_df, today_date, REFUND_PERIOD_DAYS)
        renewal_rate_y1_to_y2_text = f"{renewal_dict['renewal_rate_y1_to_y2']}%" if renewal_dict['eligible_for_y2'] else "N/A"
        renewal_rate_y2_to_y3_text = f"{renewal_dict['renewal_rate_y2_to_y3']}%" if renewal_dict['eligible_for_y3'] else "N/A"
        refund_rate_y2_text = f"{renewal_dict['refund_rate_y2']}%" if renewal_dict['customer_in_y2'] else "N/A"
        refund_rate_y3_text = f"{renewal_dict['refund_rate_y3']}%" if renewal_dict['customer_in_y3'] else "N/A"
        last_week_new_full_member = get_new_full_members_last_week(sub_df, today_iso, 1, REFUND_PERIOD_DAYS, today_date)
        prev_week_new_full_member = get_new_full_members_last_week(sub_df, today_iso, 2, REFUND_PERIOD_DAYS, today_date)

        fig_trials_8w, trials_metrics_8w = plot_weekly_trials_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
        fig_trials_all_time, trials_metrics_all = plot_weekly_trials_all_time(sub_df, today_date, today_iso)
        fig_flow_8w, metrics_8w = weekly_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
        fig_flow_all_time, weekly_flow_all_time_result = weekly_flow_all_time(sub_df, today_date, today_iso)
        fig_renewal_8w, renewal_metrics_8w = weekly_renewal_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
        fig_renewal_all_time, renewal_flow_results = weekly_renewal_flow_all_time(sub_df, today_date, today_iso)
        fig_cohort, last_cohort_dict = plot_cohort_conversion_funnel(sub_df, today_date, today_iso)
        fig_cohort_comparison, _ = plot_cohort_conversion_funnel_comparison(sub_df, today_date, today_iso, last_cohort_dict)

        order_df = preprocess_order(order_raw)
        order_df = order_grouping(order_df)
        order_df = clean_and_enrich_order_data(order_df)
        order_df = item_name_cleaning(order_df)
        order_df = pricing_items(order_df, product_raw)
        order_df = flag_gift_and_note(order_df)

        sub_df = renew_churn_status(sub_df, renewal_dict)
        short_sub_df = creating_short_sub_df(sub_df)
        if 'customer_join_key' in order_df.columns and 'customer_join_key' in short_sub_df.columns:
            matched_order_rows = order_df['customer_join_key'].isin(short_sub_df['customer_join_key']).sum()
        else:
            matched_order_rows = order_df['customer_name'].isin(short_sub_df['customer_name']).sum()
        total_order_rows = len(order_df)

        merged_df = merging_order_df_with_short_sub_df(order_df, short_sub_df)
        merged_df = creating_year_col(merged_df)
        merged_df = add_subscription_age(merged_df, today_date)

        after_sub_7_df = after_sub_7(merged_df)
        nb_cmd_alltime_df = find_nb_cmd(merged_df)

        fig_plot_first_order_3 = plot_first_order_3(after_sub_7_df)
        fig_discount_vendor = discount_vendor(merged_df)
        fig_plot_how_many_days_after_sub = plot_how_many_days_after_sub(merged_df)
        fig_plot_price_distribution = plot_price_distribution(merged_df)
        fig_plot_simple_and_complex_order = plot_simple_and_complex_order(merged_df)
        fig_plot_nb_cmd_by_customer_10_less = plot_nb_cmd_by_customer_10_less(nb_cmd_alltime_df)
        fig_order_frequency_full_members = plot_nb_cmd_by_customer_y1_y2(merged_df, 'Full Member')
        fig_order_frequency_non_full_members = plot_nb_cmd_by_customer_y1_y2(merged_df, 'Not Full Member')
        fig_plot_renew_churn_metrics = plot_renew_churn_metrics(merged_df)


        def generate_pdf_report():
            buffer = io.BytesIO()
            pdf_page_size = (11.7, 8.3)

            def add_title_page(pdf, title, subtitle=None):
                fig, ax = plt.subplots(figsize=pdf_page_size)
                ax.axis('off')
                ax.text(0.5, 0.58, title, ha='center', va='center', fontsize=24, fontweight='bold')
                if subtitle:
                    ax.text(0.5, 0.47, subtitle, ha='center', va='center', fontsize=12, wrap=True)
                pdf.savefig(fig)
                plt.close(fig)

            def add_text_page(pdf, title, body):
                fig, ax = plt.subplots(figsize=pdf_page_size)
                ax.axis('off')
                fig.suptitle(title, fontsize=20, fontweight='bold', y=0.95)
                ax.text(0.05, 0.88, body, ha='left', va='top', fontsize=11, transform=ax.transAxes, family='monospace')
                pdf.savefig(fig)
                plt.close(fig)

            def add_figure(pdf, fig):
                if fig is None:
                    return

                try:
                    fig.set_size_inches(*pdf_page_size, forward=True)
                    fig.subplots_adjust(
                        top=0.88,
                        bottom=0.24,
                        left=0.09,
                        right=0.94,
                        hspace=0.55,
                        wspace=0.35,
                    )
                except Exception:
                    pass

                image_buffer = io.BytesIO()
                fig.savefig(image_buffer, format="png", dpi=180, bbox_inches="tight", pad_inches=0.25)
                image_buffer.seek(0)
                image = plt.imread(image_buffer)

                page_width, page_height = pdf_page_size
                margin = 0.35
                usable_width = page_width - (2 * margin)
                usable_height = page_height - (2 * margin)
                image_height, image_width = image.shape[:2]
                image_ratio = image_width / image_height
                page_ratio = usable_width / usable_height

                if image_ratio > page_ratio:
                    draw_width = usable_width
                    draw_height = draw_width / image_ratio
                else:
                    draw_height = usable_height
                    draw_width = draw_height * image_ratio

                left = (page_width - draw_width) / 2 / page_width
                bottom = (page_height - draw_height) / 2 / page_height
                width = draw_width / page_width
                height = draw_height / page_height

                page_fig = plt.figure(figsize=pdf_page_size)
                page_ax = page_fig.add_axes([left, bottom, width, height])
                page_ax.imshow(image)
                page_ax.axis("off")
                pdf.savefig(page_fig)
                plt.close(page_fig)

            with PdfPages(buffer) as pdf:
                report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

                add_title_page(
                    pdf,
                    "Subscription Analytics Report",
                    f"Generated on {report_date} · Reporting week {today_date.strftime('%B %d, %Y')}"
                )

                add_text_page(pdf, "Executive Summary", f"""
KEY METRICS

• Active full members: {dict_full_member['active']}
• Trial → full conversion: {renewal_dict['conversion_rate']}%
• Y1 → Y2 renewal: {renewal_rate_y1_to_y2_text}
• Net growth, last 8 weeks: {metrics_8w['net_growth']}

WEEKLY MOVEMENT

• New trials last week: {new_trial_last_week['trials_count']} ({new_trial_last_week['trials_count'] - new_trial_prev_week['trials_count']:+d} vs previous week)
• New full members last week: {last_week_new_full_member['count']} ({last_week_new_full_member['count'] - prev_week_new_full_member['count']:+d} vs previous week)
• Full-member churn last week: {last_week_churned_members['count']} ({last_week_churned_members['count'] - prev_week_churned_members['count']:+d} vs previous week)

ALL-TIME MEMBER FLOW

• Conversions: {weekly_flow_all_time_result['total_conversions']}
• Churn: {weekly_flow_all_time_result['total_churn']}
• Net growth: {weekly_flow_all_time_result['net_growth']}
                """)
                add_figure(pdf, fig_flow_8w)
                add_figure(pdf, fig_flow_all_time)

                add_title_page(pdf, "Weekly Performance", "Weekly operating charts paired with historical context.")
                add_figure(pdf, fig_trials_8w)
                add_figure(pdf, fig_trials_all_time)
                add_figure(pdf, fig_renewal_8w)
                add_figure(pdf, fig_renewal_all_time)

                add_title_page(pdf, "Cohorts & Retention", "Lifecycle conversion, renewal, refund, and cohort drop-off analysis.")
                add_text_page(pdf, "Lifecycle Retention Metrics", f"""
RETENTION METRICS

• Y1 → Y2 renewal: {renewal_rate_y1_to_y2_text}
• Y2 → Y3 renewal: {renewal_rate_y2_to_y3_text}
• Y2 refund rate: {refund_rate_y2_text}
• Y3 refund rate: {refund_rate_y3_text}

COHORT DROP-OFF

• Total drop-off: {last_cohort_dict.get('total_drop_off', 0):.1f}%
• Trial drop-off: {last_cohort_dict.get('drop_off_trial', 0):.1f}%
• Refund drop-off: {last_cohort_dict.get('drop_off_refund', 0):.1f}%
                """)
                add_figure(pdf, fig_cohort)
                add_figure(pdf, fig_cohort_comparison)

                add_title_page(pdf, "Order Behaviour", "Core order behaviour and customer depth after subscription.")
                add_figure(pdf, fig_plot_how_many_days_after_sub)
                add_figure(pdf, fig_plot_first_order_3)
                add_figure(pdf, fig_plot_price_distribution)
                add_figure(pdf, fig_plot_nb_cmd_by_customer_10_less)
                add_figure(pdf, fig_order_frequency_full_members)
                add_figure(pdf, fig_order_frequency_non_full_members)

                add_title_page(pdf, "Exploratory Appendix", "Deeper cuts kept separate from the weekly operating review.")
                add_figure(pdf, fig_discount_vendor)
                add_figure(pdf, fig_plot_simple_and_complex_order)
                add_figure(pdf, fig_plot_renew_churn_metrics)

                add_text_page(pdf, "Methodology", f"""
PROJECT CONTEXT

This public version uses anonymized, date-shifted sample data shaped like the original exports.

BUSINESS RULES

• Full member: completed trial, passed the {REFUND_PERIOD_DAYS}-day refund period, and is not marked as gifted.
• Weekly metrics use ISO weeks.
• Order matching uses normalized customer labels to handle variants such as 'Customer 5019' vs 'Customer5019'.

INPUTS

• Subscription CSV
• Orders CSV
• Product CSV
                """)

            buffer.seek(0)
            return buffer


        target_year, target_week, _ = calculate_target_iso_week(today_iso, weeks_back=1)
        last_week_monday, last_week_sunday = get_iso_week_bounds(target_year, target_week)
        week_label = f"{last_week_monday.strftime('%d-%m-%y')} > {last_week_sunday.strftime('%d-%m-%y')}"

        target_year2, target_week2, _ = calculate_target_iso_week(today_iso, weeks_back=2)
        last_week_monday2, last_week_sunday2 = get_iso_week_bounds(target_year2, target_week2)
        week_label2 = f"{last_week_monday2.strftime('%d-%m-%y')} > {last_week_sunday2.strftime('%d-%m-%y')}"


        with st.spinner("Preparing PDF report..."):
            pdf_buffer = generate_pdf_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Subscription_Analytics_Report_{timestamp}.pdf"

        title_col, pdf_col = st.columns([4.8, 1.2], vertical_alignment="center")
        with title_col:
            st.header(f"Reporting week: {today_date.strftime('%B %d, %Y')}")
        with pdf_col:
            st.download_button(
                label="PDF report",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf",
                on_click="ignore",
                use_container_width=True
            )
        st.caption(f"Last week: {week_label} · Previous week: {week_label2}")


        tab_overview, tab_weekly, tab_retention, tab_orders, tab_exploratory, tab_methodology = st.tabs([
            "Executive summary",
            "Weekly performance",
            "Cohorts & retention",
            "Order behaviour",
            "Exploratory appendix",
            "Methodology"
        ])

        with tab_overview:
            st.subheader("Business KPIs")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Active full members", dict_full_member['active'])
            col2.metric("Trial → full conversion", f"{renewal_dict['conversion_rate']}%")
            col3.metric("Y1 → Y2 renewal", renewal_rate_y1_to_y2_text)
            col4.metric("Net growth, 8 weeks", f"{metrics_8w['net_growth']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("New trials last week", value=f"{new_trial_last_week['trials_count']}", delta=f"{new_trial_last_week['trials_count'] - new_trial_prev_week['trials_count']:+d}")
            col2.metric("New full members", value=f"{last_week_new_full_member['count']}", delta=f"{last_week_new_full_member['count'] - prev_week_new_full_member['count']:+d}")
            col3.metric("Full-member churn", value=f"{last_week_churned_members['count']}", delta=f"{last_week_churned_members['count'] - prev_week_churned_members['count']:+d}", delta_color='inverse')

            st.markdown("---")
            st.subheader("Full-member flow, last 8 weeks")
            st.caption("This is the decision view: conversions, churn, and net growth in the current reporting window.")
            st.pyplot(fig_flow_8w)

            st.subheader("Full-member flow, all time")
            st.caption("This gives the longer-term context behind the current reporting window.")
            st.pyplot(fig_flow_all_time)
            col1, col2, col3 = st.columns(3)
            col1.metric("All-time conversions", f"{weekly_flow_all_time_result['total_conversions']}")
            col2.metric("All-time churn", f"{weekly_flow_all_time_result['total_churn']}")
            col3.metric("All-time net growth", f"{weekly_flow_all_time_result['net_growth']}")

        with tab_weekly:
            st.subheader("New trials, last 8 weeks")
            st.caption("Weekly acquisition view, paired with historical context in the expander below.")
            st.pyplot(fig_trials_8w)
            col1, col2, col3 = st.columns(3)
            col1.metric("Latest complete week", trials_metrics_8w['latest_week'])
            col2.metric("Previous week", trials_metrics_8w['previous_week'])
            col3.metric("Week-over-week", f"{trials_metrics_8w['week_over_week_change']} ({trials_metrics_8w['week_over_week_pct']:.1f}%)")

            with st.expander("Historical trial context"):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("8-week average", f"{trials_metrics_8w['average_per_week']:.0f}")
                col2.metric("Recent 4-week average", f"{trials_metrics_8w['recent_4w_avg']:.0f}")
                col3.metric(f"Max week: {trials_metrics_8w['max_week_label']}", trials_metrics_8w['max_week'])
                col4.metric(f"Min week: {trials_metrics_8w['min_week_label']}", trials_metrics_8w['min_week'])
                st.pyplot(fig_trials_all_time)

            st.subheader("Renewal flow, last 8 weeks")
            st.caption("Weekly retention operations view, with all-time renewal context kept one click away.")
            st.pyplot(fig_renewal_8w)
            col1, col2, col3 = st.columns(3)
            col1.metric("Renewals, 8 weeks", f"{renewal_metrics_8w['total_renewals']}")
            col2.metric("Post-renewal churn, 8 weeks", f"{renewal_metrics_8w['churn_post_renewal']}")
            col3.metric("Refund churn, 8 weeks", f"{renewal_metrics_8w['churn_refund_renewal']}")

            with st.expander("Historical renewal context"):
                st.pyplot(fig_renewal_all_time)
                col1, col2, col3 = st.columns(3)
                col1.metric("All-time renewals", f"{renewal_flow_results['total_renewals']}")
                col2.metric("All-time post-renewal churn", f"{renewal_flow_results['total_churn_post_renewal']}")
                col3.metric("All-time refund churn", f"{renewal_flow_results['total_churn_refund_renewal']}")

        with tab_retention:
            st.subheader("Lifecycle retention metrics")
            st.caption("These are deeper lifecycle metrics; useful for periodic review, not necessarily every weekly stand-up.")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Y1 → Y2 renewal", renewal_rate_y1_to_y2_text)
            col2.metric("Y2 → Y3 renewal", renewal_rate_y2_to_y3_text)
            col3.metric("Y2 refund rate", refund_rate_y2_text)
            col4.metric("Y3 refund rate", refund_rate_y3_text)

            st.subheader("Cohort conversion")
            if fig_cohort is not None:
                st.pyplot(fig_cohort)
                col1, col2, col3 = st.columns(3)
                col1.metric("Total drop-off", f"{last_cohort_dict.get('total_drop_off', 0):.1f}%")
                col2.metric("Trial drop-off", f"{last_cohort_dict.get('drop_off_trial', 0):.1f}%")
                col3.metric("Refund drop-off", f"{last_cohort_dict.get('drop_off_refund', 0):.1f}%")

            st.subheader("Cohort comparison across reporting periods")
            st.pyplot(fig_cohort_comparison)

        with tab_orders:
            st.subheader("Order behaviour")
            if total_order_rows:
                match_rate = matched_order_rows / total_order_rows
                if match_rate < 0.8:
                    st.warning(
                        f"Matched only {matched_order_rows:,} of {total_order_rows:,} order rows "
                        "to subscription customers. Full-member vs trial comparisons may not be reliable with these files."
                    )
                else:
                    st.success(f"Matched {matched_order_rows:,} of {total_order_rows:,} order rows to subscription customers ({match_rate:.1%}).")

            st.pyplot(fig_plot_how_many_days_after_sub)
            st.pyplot(fig_plot_first_order_3)
            st.pyplot(fig_plot_price_distribution)
            st.pyplot(fig_plot_nb_cmd_by_customer_10_less)

            with st.expander("Full-member vs non-full-member order frequency"):
                st.caption("This segment connects subscription lifecycle status to ordering depth, which is more useful than a generic order count chart.")
                st.pyplot(fig_order_frequency_full_members)
                st.pyplot(fig_order_frequency_non_full_members)

        with tab_exploratory:
            st.subheader("Exploratory order analysis")
            st.caption("Useful deeper cuts for occasional investigation; kept separate from the weekly operating review.")
            st.pyplot(fig_discount_vendor)
            st.pyplot(fig_plot_simple_and_complex_order)
            st.pyplot(fig_plot_renew_churn_metrics)

        with tab_methodology:
            st.subheader("Methodology")
            st.markdown(f"""
            **Core questions**

            - Are weekly trials increasing or decreasing?
            - How many trial users convert into full members?
            - How many full members churn or renew?
            - Where do users drop off between trial, refund period, and full membership?
            - Do full members behave differently from non-full members after subscribing?

            **Metric definitions**

            - Current reporting date: **{today_date.strftime('%B %d, %Y')}**.
            - A **full member** has completed the trial, passed the {REFUND_PERIOD_DAYS}-day refund period, and is not marked as gifted.
            - Weekly metrics use ISO weeks.
            - Renewal metrics compare first-year, second-year, and third-year subscription behaviour.
            - Cohort conversion follows users from trial start through refund-period completion.

            **Data handling**

            - Customer/order matching uses normalized customer labels to handle messy exports, such as `Customer 5019` vs `Customer5019`.
            - The public version uses anonymized and date-shifted sample data shaped like the original exports.
            - This is a portfolio-safe mirror of the original internal tool, not the private deployment or a production BI platform.
            """)
