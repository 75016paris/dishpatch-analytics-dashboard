# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from DISHPATCH import preprocess_data, remove_multi_subscriptions, remove_high_volume_customers, clean_inconsistent_statuses, custom_multisub_aggregation, prepare_multisub_for_integration, integrate_with_subdf, cancel_during_trial, refund_period_end_utc, canceled_during_refund_period, full_member_status
from DISHPATCH import paying_members, add_ended_at_utc, calculate_duration, get_full_members_count, get_iso_week_bounds, get_weeks_in_iso_year, calculate_target_iso_week, get_new_trial_last_week, get_conversion_rate_last_weeks, get_churn_members_last_week, cus_renewal, get_new_full_members_last_week
from DISHPATCH import plot_weekly_trials_8_weeks, plot_weekly_trials_all_time, weekly_flow_8_weeks, weekly_flow_all_time, weekly_renewal_flow_8_weeks, weekly_renewal_flow_all_time, plot_cohort_conversion_funnel, plot_cohort_conversion_funnel_comparison
##########################################################
from DISHPATCH import preprocess_order, order_grouping, clean_and_enrich_order_data, item_name_cleaning, pricing_items, flag_gift_and_note
from DISHPATCH import renew_churn_status, creating_short_sub_df, merging_order_df_with_short_sub_df, creating_year_col, after_sub_7, find_nb_cmd, split_by_year
from DISHPATCH import discount_vendor, plot_first_order_1, plot_first_order_2, plot_first_order_3, plot_first_order_4, plot_how_many_days_after_sub, plot_gift_and_not, plot_price_distribution, plot_simple_and_complex_order, plot_nb_cmd_by_customer_10_less, plot_nb_cmd_by_customer_10_more, plot_nb_cmd_by_customer_y1_y2, plot_renew_churn_metrics, subscription_lenght

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_pdf import PdfPages
import io
from datetime import datetime
import time



st.set_page_config(
    page_title="DISHPATCH Analytics",
    page_icon="📊",
    layout="wide"
)


st.markdown("""
<style>
/* Labels des métriques */
[data-testid="stMetricLabel"] p {
    font-size: 20px !important;
}

/* Valeurs des métriques */
[data-testid="stMetricValue"] {
    font-size: 23px !important;
    font-weight: bold !important;
}

/* Animation de chargement personnalisée */
.loading-animation {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 20px 0;
}

.spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    width: 50px;
    height: 50px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.progress-text {
    font-size: 18px;
    color: #333;
    margin-top: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div style='margin: 1px 0;'></div>", unsafe_allow_html=True)  # Contrôle précis


st.title("📊 DISHPATCH")
st.markdown("""
**Subscription Analytics Dashboard**
""")

# Download file
uploaded_file = st.file_uploader("Upload the subscription csv", type="csv")
##########################################################
uploaded_file2 = st.file_uploader("Upload the orders csv", type="csv")
uploaded_file3 = st.file_uploader("Upload the product csv", type="csv")

if uploaded_file3:
    with st.spinner('🔄 Processing your data... This may take a moment.'):
        # Affichage d'une barre de progression
        status_text = st.empty()

        #today_date = pd.Timestamp('2025-05-23', tz='UTC') # For testing purposes
        today_date = pd.Timestamp.now(tz='UTC')
        today_iso = pd.to_datetime(today_date).isocalendar()


        # Set REFUND PERDIOD DURATION
        REFUND_PERIOD_DAYS = 14  # Duration of the refund period in days

        # Set thresholds for cleaning
        HIGH_VOLUME_THRESHOLD = 4
        DUPLICATE_THRESHOLD_MINUTES = 15


        # Traitement des données
        sub_raw = pd.read_csv(uploaded_file)
        sub_df = preprocess_data(sub_raw)
        sub_df, multisub_df = remove_multi_subscriptions(sub_df)
        multisub_df = remove_high_volume_customers(multisub_df)
        multisub_df = custom_multisub_aggregation(multisub_df)
        combined_df = integrate_with_subdf(multisub_df, sub_df)
        sub_df = combined_df.copy()
        sub_df = cancel_during_trial(sub_df)
        sub_df = refund_period_end_utc(sub_df, REFUND_PERIOD_DAYS)
        sub_df = canceled_during_refund_period(sub_df)
        sub_df = full_member_status(sub_df)
        sub_df = paying_members(sub_df)
        sub_df = add_ended_at_utc(sub_df, today_date)
        sub_df = calculate_duration(sub_df, today_date)
        dict_full_member = get_full_members_count(sub_df)
        new_trial_last_week = get_new_trial_last_week(sub_df, today_iso, weeks_back=1)
        new_trial_prev_week = get_new_trial_last_week(sub_df, today_iso, weeks_back=2)
        last_week_conversion_rate = get_conversion_rate_last_weeks(sub_df, today_iso, weeks_back=1)
        prev_week_conversion_rate = get_conversion_rate_last_weeks(sub_df, today_iso, weeks_back=2)
        last_week_churned_members = get_churn_members_last_week(sub_df, today_iso, weeks_back=1)
        prev_week_churned_members = get_churn_members_last_week(sub_df, today_iso, weeks_back=2)
        renewal_dict = cus_renewal(sub_df)
        last_week_new_full_member = get_new_full_members_last_week(sub_df, today_iso, 1, REFUND_PERIOD_DAYS)
        prev_week_new_full_member = get_new_full_members_last_week(sub_df, today_iso, 2, REFUND_PERIOD_DAYS)

        fig_trials_8w, trials_metrics_8w = plot_weekly_trials_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
        fig_trials_all_time, trials_metrics_all = plot_weekly_trials_all_time(sub_df, today_date, today_iso)
        fig_flow_8w, metrics_8w = weekly_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
        fig_flow_all_time, weekly_flow_all_time_result = weekly_flow_all_time(sub_df, today_date, today_iso)
        fig_renewal_8w, renewal_metrics_8w = weekly_renewal_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8)
        fig_renewal_all_time, renewal_flow_results = weekly_renewal_flow_all_time(sub_df, today_date, today_iso)
        fig_cohort, last_cohort_dict = plot_cohort_conversion_funnel(sub_df, today_date, today_iso)
        fig_cohort_comparison, last_cohort_comparison = plot_cohort_conversion_funnel_comparison(sub_df, today_date, today_iso, last_cohort_dict)

##########################################################
        order_raw = pd.read_csv(uploaded_file2)
        product_raw = pd.read_csv(uploaded_file3)


        order_df = preprocess_order(order_raw)
        order_df = order_grouping(order_df)
        order_df = clean_and_enrich_order_data(order_df)
        order_df = item_name_cleaning(order_df)
        order_df = pricing_items(order_df, product_raw)
        order_df = flag_gift_and_note(order_df)

        sub_df = renew_churn_status(sub_df, renewal_dict)
        short_sub_df = creating_short_sub_df(sub_df)

        merged_df = merging_order_df_with_short_sub_df(order_df, short_sub_df)
        merged_df = creating_year_col(merged_df)
        merged_df = subscription_lenght(merged_df)

        after_sub_7_df = after_sub_7(merged_df)
        nb_cmd_alltime_df = find_nb_cmd(merged_df)
        y0_df, y1_df, y2_df, y3_df = split_by_year(nb_cmd_alltime_df)


        # fig_plot_first_order = plot_first_order(after_sub_7_df)
        fig_plot_first_order_1 = plot_first_order_1(after_sub_7_df)
        fig_plot_first_order_2 = plot_first_order_2(after_sub_7_df)
        fig_plot_first_order_3 = plot_first_order_3(after_sub_7_df)
        fig_plot_first_order_4 = plot_first_order_4(after_sub_7_df)
        fig_discount_vendor = discount_vendor(merged_df)
        fig_plot_how_many_days_after_sub = plot_how_many_days_after_sub(merged_df)
        fig_plot_gift_and_not = plot_gift_and_not(after_sub_7_df, sub_df)
        fig_plot_price_distribution = plot_price_distribution(merged_df)
        fig_plot_simple_and_complex_order = plot_simple_and_complex_order(merged_df)
        fig_plot_nb_cmd_by_customer_10_less = plot_nb_cmd_by_customer_10_less(nb_cmd_alltime_df)
        fig_plot_nb_cmd_by_customer_10_more = plot_nb_cmd_by_customer_10_more(nb_cmd_alltime_df)
        fig_plot_nb_cmd_by_customer_y1_y2 = plot_nb_cmd_by_customer_y1_y2(merged_df, 'Full Member')
        fig_plot_nb_cmd_by_customer_y1_y2_not_full = plot_nb_cmd_by_customer_y1_y2(merged_df, 'Not Full Member')
        fig_plot_renew_churn_metrics = plot_renew_churn_metrics(merged_df)


##########################################################


        def generate_pdf_report(sub_df, today_date, dict_full_member, renewal_dict, new_trial_last_week,
                            new_trial_prev_week, last_week_new_full_member, prev_week_new_full_member,
                            last_week_churned_members, prev_week_churned_members, trials_metrics_8w,
                            trials_metrics_all, metrics_8w, weekly_flow_all_time_result, renewal_metrics_8w,
                            renewal_flow_results, last_cohort_dict, REFUND_PERIOD_DAYS,
                            fig_trials_8w, fig_trials_all_time, fig_flow_8w, fig_flow_all_time,
                            fig_renewal_8w, fig_renewal_all_time, fig_cohort, fig_cohort_comparison):

            # Create a buffer for the PDF
            buffer = io.BytesIO()

            with PdfPages(buffer) as pdf:
                # Page 1: Key Metrics
                fig, ax = plt.subplots(figsize=(11, 8))
                ax.axis('off')

                # Title
                fig.suptitle('DISHPATCH Subscription Analytics Report', fontsize=20, fontweight='bold', y=0.95)

                # Report Date
                report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                ax.text(0.5, 0.85, f'Report generated on: {report_date}',
                        ha='center', va='top', fontsize=12, transform=ax.transAxes)

                # Key Metrics
                metrics_text = f"""
        KEY METRICS:

        • Total Active Members: {dict_full_member['active']}
        • Active Members in 1st Year: {renewal_dict['active_in_y1']}
        • Active Members in 2nd Year: {renewal_dict['active_in_y2']}

        • Conversion Rate (Trial → Full Member): {renewal_dict['conversion_rate']}%
        • Renewal Rate: {renewal_dict['renewal_rate_y1_to_y2']}%

        WEEKLY METRICS:

        • New Trials Last Week: {new_trial_last_week['trials_count']}
        • New Trials Previous Week: {new_trial_prev_week['trials_count']}

        • New Full Members Last Week: {last_week_new_full_member['count']}
        • New Full Members Previous Week: {prev_week_new_full_member['count']}

        • Churned Members Last Week: {last_week_churned_members['count']}
        • Churned Members Previous Week: {prev_week_churned_members['count']}

        NOTES:
        - Refund Period: {REFUND_PERIOD_DAYS} days
        - To be a full member, a user must complete their trial,
        not request a refund, and not be gifted
                """

                ax.text(0.05, 0.75, metrics_text, ha='left', va='top', fontsize=11,
                        transform=ax.transAxes, family='monospace')

                pdf.savefig(fig, bbox_inches='tight')
                plt.close()

                # Page 2: Trial Plots
                pdf.savefig(fig_trials_8w, bbox_inches='tight')
                pdf.savefig(fig_trials_all_time, bbox_inches='tight')

                # Page 3: Member Flow
                pdf.savefig(fig_flow_8w, bbox_inches='tight')
                pdf.savefig(fig_flow_all_time, bbox_inches='tight')

                # Page 4: Renewal Flow
                pdf.savefig(fig_renewal_8w, bbox_inches='tight')
                pdf.savefig(fig_renewal_all_time, bbox_inches='tight')

                # Page 5: Conversion Funnel
                pdf.savefig(fig_cohort, bbox_inches='tight')
                pdf.savefig(fig_cohort_comparison, bbox_inches='tight')

            buffer.seek(0)
            return buffer


        target_year, target_week, target_week_key = calculate_target_iso_week(today_iso, weeks_back=1)
        last_week_monday, last_week_sunday = get_iso_week_bounds(target_year, target_week)
        week_label = f"{last_week_monday.strftime('%d-%m-%y')} > {last_week_sunday.strftime('%d-%m-%y')}"

        target_year2, target_week2, target_week_key2 = calculate_target_iso_week(today_iso, weeks_back=2)
        last_week_monday2, last_week_sunday2 = get_iso_week_bounds(target_year2, target_week2)
        week_label2 = f"{last_week_monday2.strftime('%d-%m-%y')} > {last_week_sunday2.strftime('%d-%m-%y')}"


        st.header(f"{today_date.strftime('%B %d, %Y')}")

        col1, col2, col3 = st.columns(3, gap="small")
        col1.metric("Full Active Members :", dict_full_member['active'])
        col1.markdown(f"*Active Full Member in 1st year :* **{renewal_dict['active_in_y1']}**")
        col1.markdown(f"*Active Full Member in 2nd year :* **{renewal_dict['active_in_y2']}**")


        st.markdown(" ")

        st.metric("Conversion Rate (from Trial to Full Member) :", f"{renewal_dict['conversion_rate']}%")
        st.markdown(f"*To be a full member a user must complete their trial, not request a refund, and not be gifted. (refund period {REFUND_PERIOD_DAYS} days)*")

        st.markdown(" ")

        st.metric("Renewal Rate :", f"{renewal_dict['renewal_rate_y1_to_y2']}%")
        st.markdown(f"*Renewal rate from 1st year to 2nd year:* **{renewal_dict['renewal_rate_y1_to_y2']}%** *({renewal_dict['refund_rate_y2']}% Ask for Refund)*")
        st.markdown(f"*Renewal rate from 2nd year to 3rd year:* **{renewal_dict['renewal_rate_y2_to_y3']}%** *({renewal_dict['refund_rate_y3']}% Ask for Refund)*")

        st.markdown(" ")
        st.markdown(" ")


        st.markdown(f"**Last week :** {week_label} vs **Previous week :** {week_label2} :")

        col1, col2, col3 = st.columns(3)
        col1.metric("New trials last week :", value=f"{new_trial_last_week['trials_count']}", delta=f"{new_trial_last_week['trials_count'] - new_trial_prev_week['trials_count']:+d}")
        col2.metric("New full members last week :", value=f"{last_week_new_full_member['count']}", delta=f"{last_week_new_full_member['count'] - prev_week_new_full_member['count']:+d}")
        col3.metric("Churn full members last week :", value=f"{last_week_churned_members['count']}", delta=f"{last_week_churned_members['count'] - prev_week_churned_members['count']:+d}", delta_color='inverse')


        st.markdown("---")


        # Visualisations
        st.header("NEW TRIALS")
        st.pyplot(fig_trials_8w)

        col1, col2, col3 = st.columns(3)
        col1.metric("Last week trials :", trials_metrics_8w['latest_week'])
        col2.metric("Previous week trials :", trials_metrics_8w['previous_week'])
        col3.metric("Week-over-week change :", f"{trials_metrics_8w['week_over_week_change']} ({trials_metrics_8w['week_over_week_pct']:.1f}%)")


        col1, col2 = st.columns(2)
        col1.metric("Average trials per week (last 8 weeks) :", f"{trials_metrics_8w['average_per_week']:.0f}")
        col2.metric(f"Max trials week (last 8 weeks) : *{trials_metrics_8w['max_week_label']}*", f"{trials_metrics_8w['max_week']}")

        col1, col2 = st.columns(2)
        col1.metric("Recent trials average (last 4 weeks) :", f"{trials_metrics_8w['recent_4w_avg']:.0f}")
        col2.metric(f"Min trials week (last 8 weeks) : *{trials_metrics_8w['min_week_label']}*", f"{trials_metrics_8w['min_week']}")



        st.markdown(" ")

        st.pyplot(fig_trials_all_time)

        col1 = st.columns(1)[0]
        col1.metric("Total trials (all time) :", f"{trials_metrics_all['total_trials']:.0f}")

        col1, col2 = st.columns(2)
        col1.metric("Average trials per week (all time) :", f"{trials_metrics_all['average_per_week']:.0f}")
        col2.metric(f"Max trials week (all time) : *{trials_metrics_all['max_week_label']}*", f"{trials_metrics_all['max_week']}")


        col1, col2 = st.columns(2)
        col1.metric("Recent weeks trials average (last 4 weeks) :", f"{trials_metrics_8w['recent_4w_avg']:.0f}")
        col2.metric(f"Min trials week (all time) : *{trials_metrics_all['min_week_label']}*", f"{trials_metrics_all['min_week']}")

        st.markdown("---")

        st.header("FULL MEMBERS FLOW")
        st.pyplot(fig_flow_8w)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Conversions (last 8 weeks) :", f"{metrics_8w['conversions']}")
        col2.metric("Total Churn (last 8 weeks) :", f"{metrics_8w['churn']}")
        col3.metric("Net growth (last 8 weeks) :", f"{metrics_8w['net_growth']}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg. Conversions per week (last 8 weeks) :", f"{metrics_8w['avg_conversions_per_week']:.1f}")
        col2.metric("Avg. Churn per week (last 8 weeks) :", f"{metrics_8w['avg_churn_per_week']:.1f}")
        col3.metric("Avg. Net growth per week (last 8 weeks) :", f"{metrics_8w['avg_net_growth']:.1f}")

        col1, col2 = st.columns(2)
        col1.metric(f"Max conversions week (last 8 weeks): *{metrics_8w['max_conv_label']}*", f"{metrics_8w['max_conv_value']}")
        col2.metric(f"Min conversions week (last 8 weeks): *{metrics_8w['min_conv_label']}*", f"{metrics_8w['min_conv_value']}")

        st.markdown(" ")
        st.pyplot(fig_flow_all_time)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Conversions (all time) :", f"{weekly_flow_all_time_result['total_conversions']}")
        col2.metric("Total Churn (all time) :", f"{weekly_flow_all_time_result['total_churn']}")
        col3.metric("Total Net growth (all time) :", f"{weekly_flow_all_time_result['net_growth']}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg. Conversions per week (all time) :", f"{weekly_flow_all_time_result['avg_conversions_per_week']:.1f}")
        col2.metric("Avg. Churn per week (all time) :", f"{weekly_flow_all_time_result['avg_churn_per_week']:.1f}")
        col3.metric("Avg. Net growth average (all time) :", f"{weekly_flow_all_time_result['avg_net_per_week']:.1f}")

        col1, col2 = st.columns(2)
        col1.metric(f"Max conversions week (all time) : *{weekly_flow_all_time_result['max_conv_label']}*", f"{weekly_flow_all_time_result['max_conv_value']}")
        col2.metric(f"Min conversions week (all time) : *{weekly_flow_all_time_result['min_conv_label']}*", f"{weekly_flow_all_time_result['min_conv_value']}")


        st.markdown("---")


        st.header("RENEWAL FLOW")
        st.pyplot(fig_renewal_8w)

        col1 = st.columns(1)[0]
        col1.metric("Total Renewals (last 8 weeks) :", f"{renewal_metrics_8w['total_renewals']}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Churn (last 8 weeks) :", f"{renewal_metrics_8w['total_churn']}")
        col2.metric("Post-Renewal Churn (last 8 weeks) :", f"{renewal_metrics_8w['churn_post_renewal']}")
        col3.metric("Ask for Refund (last 8 weeks) :", f"{renewal_metrics_8w['churn_refund_renewal']}")

        st.pyplot(fig_renewal_all_time)

        col1 = st.columns(1)[0]
        col1.metric("Total Renewals (all times) :", f"{renewal_flow_results['total_renewals']}")

        col1 = st.columns(1)[0]
        col1.metric("Average Renewals per week (all time) :", f"{renewal_flow_results['avg_renewals_per_week']:.1f}")



        col1, col2, col3 = st.columns(3)
        col1.metric("Total Churn (all times) :", f"{renewal_flow_results['total_churn']}")
        col2.metric("Post-Renewal Churn (all times) :", f"{renewal_flow_results['total_churn_post_renewal']}")
        col3.metric("Ask for Refund (all times) :", f"{renewal_flow_results['total_churn_refund_renewal']}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg. Churn per week (all time) :", f"{renewal_flow_results['avg_post_churn_per_week']:.1f}")
        col2.metric("Avg. Post-Renewal Churn per week (all time) :", f"{renewal_flow_results['avg_post_churn_per_week']:.1f}")
        col3.metric("Avg. Refund per week (all time) :", f"{renewal_flow_results['avg_refund_per_week']:.1f}")

        st.markdown("---")

        st.header("CONVERSION FUNNEL")
        if fig_cohort is not None:
            st.pyplot(fig_cohort)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total drop-off :", f"{last_cohort_dict.get('total_drop_off', 0):.1f}%")
        col2.metric("Drop-off during trial :", f"{last_cohort_dict.get('drop_off_trial', 0):.1f}%")
        col3.metric("Ask for Refund :", f"{last_cohort_dict.get('drop_off_refund', 0):.1f}%")


        st.pyplot(fig_cohort_comparison)

        st.markdown("---")

        st.header("ORDERS ANALYSIS")
        st.pyplot(fig_plot_how_many_days_after_sub)
        st.pyplot(fig_plot_first_order_1)
        st.pyplot(fig_plot_first_order_2)
        st.pyplot(fig_plot_first_order_3)
        st.pyplot(fig_plot_first_order_4)
        st.pyplot(fig_discount_vendor)
        st.pyplot(fig_plot_gift_and_not)
        st.pyplot(fig_plot_price_distribution)
        st.pyplot(fig_plot_simple_and_complex_order)
        st.pyplot(fig_plot_nb_cmd_by_customer_10_less)
        st.pyplot(fig_plot_nb_cmd_by_customer_10_more)
        st.pyplot(fig_plot_nb_cmd_by_customer_y1_y2)
        st.pyplot(fig_plot_nb_cmd_by_customer_y1_y2_not_full)
        st.pyplot(fig_plot_renew_churn_metrics)






        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📄 Download PDF Report", type="primary", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    pdf_buffer = generate_pdf_report(
                        sub_df, today_date, dict_full_member, renewal_dict,
                        new_trial_last_week, new_trial_prev_week,
                        last_week_new_full_member, prev_week_new_full_member,
                        last_week_churned_members, prev_week_churned_members,
                        trials_metrics_8w, trials_metrics_all, metrics_8w,
                        weekly_flow_all_time_result, renewal_metrics_8w,
                        renewal_flow_results, last_cohort_dict, REFUND_PERIOD_DAYS,
                        fig_trials_8w, fig_trials_all_time, fig_flow_8w, fig_flow_all_time,
                        fig_renewal_8w, fig_renewal_all_time, fig_cohort, fig_cohort_comparison
                    )

                    # File name with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"DISHPATCH_Analytics_Report_{timestamp}.pdf"

                    st.download_button(
                        label="⬇️ Click here to download",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )

                    st.success("✅ PDF generated successfully!")
