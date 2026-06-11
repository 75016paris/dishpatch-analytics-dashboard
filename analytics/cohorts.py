"""Cohort conversion and retention funnel charts."""

from .common import *

def plot_cohort_conversion_funnel(sub_df, today_date, today_iso):
    """
    Plot a conversion funnel for different cohorts with 3 bars:
    1. Initial trials
    2. Survivors after trial period (not canceled during trial)
    3. Survivors after refund period (not canceled during refund)

    """

    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    _log("Creating cohort conversion funnel using ISO calendar...")

    # Check if there is data
    if 'trial_start_utc' not in sub_df.columns or sub_df['trial_start_utc'].isna().all():
        _log("No trial data found")
        return None, {}

    # Calculate the cohort week (4 weeks back for a complete cohort)
    weeks_back = 4
    cohort_year, cohort_week, cohort_week_key = calculate_target_iso_week(today_iso, weeks_back)
    cohort_year_complete, cohort_week_complete, cohort_week_key_complete = calculate_target_iso_week(today_iso, weeks_back=1)

    _log(f"Target cohort week: {cohort_week_key}")

    try:
        cohort_monday, cohort_sunday = get_iso_week_bounds(cohort_year, cohort_week)

        # Convert to UTC for comparison
        cohort_monday_utc = pd.Timestamp(cohort_monday).tz_localize('UTC')
        cohort_sunday_utc = pd.Timestamp(cohort_sunday).tz_localize('UTC') + pd.Timedelta(hours=23, minutes=59, seconds=59)

        _log(f"Analyzing cohort from {cohort_monday.strftime('%d-%m-%Y')} to {cohort_sunday.strftime('%d-%m-%Y')}")

    except Exception as e:
        _log(f"Error calculating ISO week bounds: {e}")
        return None, {}

    try:
        cohort_monday_complete, cohort_sunday_complete = get_iso_week_bounds(cohort_year_complete, cohort_week_complete)

        # Convert to UTC for comparison
        cohort_monday_complete_utc = pd.Timestamp(cohort_monday_complete).tz_localize('UTC')
        cohort_sunday_complete_utc = pd.Timestamp(cohort_sunday_complete).tz_localize('UTC') + pd.Timedelta(hours=23, minutes=59, seconds=59)

        _log(f"Analyzing cohort from {cohort_sunday_complete.strftime('%d-%m-%Y')} to {cohort_sunday.strftime('%d-%m-%Y')}")

    except Exception as e:
        _log(f"Error calculating ISO week bounds: {e}")
        return None, {}

    def add_iso_week_columns(df, date_column):
        """Standardized function to add ISO week columns"""
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])

        # Filter valid dates to avoid <NA>
        valid_dates = df[date_column].notna()

        # Initialize columns with default values
        df['iso_year'] = pd.NA
        df['iso_week'] = pd.NA
        df['iso_week_key'] = pd.NA

        # Calculate only for valid dates
        if valid_dates.any():
            df.loc[valid_dates, 'iso_year'] = df.loc[valid_dates, date_column].dt.isocalendar().year
            df.loc[valid_dates, 'iso_week'] = df.loc[valid_dates, date_column].dt.isocalendar().week
            df.loc[valid_dates, 'iso_week_key'] = (
                df.loc[valid_dates, 'iso_year'].astype(str) + '-W' +
                df.loc[valid_dates, 'iso_week'].astype(str).str.zfill(2)
            )

        return df

    # Option 1: Direct filtering with calculated bounds
    complete_cohort_trials = sub_df[
        (sub_df['trial_start_utc'] >= cohort_monday_utc) &
        (sub_df['trial_start_utc'] <= cohort_sunday_utc)
    ].copy()

    # Option 2: Validation with ISO week key (optional for debugging)
    if len(complete_cohort_trials) > 0:
        trials_with_iso = add_iso_week_columns(complete_cohort_trials, 'trial_start_utc')
        iso_validation = trials_with_iso[trials_with_iso['iso_week_key'] == cohort_week_key]

        if len(iso_validation) != len(complete_cohort_trials):
            _log(f"Validation warning: Direct filter ({len(complete_cohort_trials)}) vs ISO filter ({len(iso_validation)})")
            # Use the ISO method for greater accuracy
            complete_cohort_trials = iso_validation

    def create_default_cohort_dict():
        """Crée un dictionnaire avec toutes les clés nécessaires à 0"""
        return {
            'total_trials': 0,
            'survived_trial': 0,
            'survived_refund': 0,
            'conversion_trial_rate': 0.0,
            'conversion_refund_rate': 0.0,
            'survival_rate_trial_to_refund': 0.0,
            'drop_off_trial': 0.0,
            'drop_off_refund': 0.0,
            'total_drop_off': 0.0,
            'cohort_week_start': None,
            'cohort_week_end': None,
            'cohort_week_label': 'No Data',
            'cohort_week_key': 'No Data',
            'cohort_year': 0,
            'cohort_week_number': 0,
            'weeks_back': 0
        }

    # Dans vos fonctions, au lieu de retourner {} :
    if len(complete_cohort_trials) == 0:
        _log(f"No trial data found for cohort week {cohort_week_key}")
        return None, create_default_cohort_dict()

    _log(f"Found {len(complete_cohort_trials)} trials in cohort week {cohort_week_key}")

    total_trials = len(complete_cohort_trials)

    # Survivors after trial period (not canceled during trial)
    survivors_trial = len(complete_cohort_trials[
        ~complete_cohort_trials['canceled_during_trial']
    ])

    # Survivors after refund period (not canceled during refund)
    survivors_refund = len(complete_cohort_trials[
        (~complete_cohort_trials['canceled_during_trial']) &
        (~complete_cohort_trials['canceled_during_refund_period'])
    ])

    fig, ax = plt.subplots(1, 1, figsize=(11, 8))

    categories = ['Initial Trials', 'Survived Trial Period', 'Full Members']
    values = [total_trials, survivors_trial, survivors_refund]
    colors = ['steelblue', 'orange', 'darkgreen']

    bars = ax.bar(categories, values, color=colors, alpha=0.7)

    # Add numbers on bars (same style as other functions)
    for i, (bar, value) in enumerate(zip(bars, values)):
        height = bar.get_height()
        # Protection against max() on empty list
        max_val = max(values) if values else 1
        ax.text(bar.get_x() + bar.get_width()/2., height + max_val * 0.01,
                f'{value:,}', ha='center', va='bottom',
                fontsize=11, color='darkblue', fontweight='bold')

        # Add percentage from previous step
        if total_trials > 0:
            percentage = (value / total_trials) * 100
            ax.text(bar.get_x() + bar.get_width()/2., height/2,
                    f'{percentage:.1f}%', ha='center', va='center',
                    fontweight='bold', fontsize=10, color='white')

    week_label_complete = f"{cohort_monday_complete_utc.strftime('%d-%m-%y')} > {cohort_sunday_complete_utc.strftime('%d-%m-%y')}"
    week_label = f"{cohort_monday.strftime('%d-%m-%y')} > {cohort_sunday.strftime('%d-%m-%y')}"
    ax.set_title(
        f'CONVERSION FUNNEL\nComplete Cohort Week {cohort_week_key}\nTrialers: {week_label}\nConverted: {week_label_complete}',
        fontsize=15,
        fontweight='bold',
        pad=24
    )

    ax.set_ylabel('Number of Users', fontsize=12)
    ax.grid(axis='y', alpha=0.3)

    # Protection against max() on empty list
    max_val = max(values) if values else 1
    ax.set_ylim(0, max_val * 1.2)

    ax.set_xlim(-0.5, len(categories) - 0.5)

    _log("=== CALCULATING METRICS ===")

    conversion_trial = (survivors_trial / total_trials * 100) if total_trials > 0 else 0
    conversion_refund = (survivors_refund / total_trials * 100) if total_trials > 0 else 0
    drop_off_trial = ((total_trials - survivors_trial) / total_trials * 100) if total_trials > 0 else 0
    drop_off_refund = ((survivors_trial - survivors_refund) / total_trials * 100) if total_trials > 0 else 0

    # Additional metrics
    survival_rate_trial_to_refund = (survivors_refund / survivors_trial * 100) if survivors_trial > 0 else 0

    _log(f"Cohort week: {cohort_week_key}")
    _log(f"Total trials: {total_trials:,}")
    _log(f"Trial survival rate: {conversion_trial:.1f}%")
    _log(f"Full conversion rate: {conversion_refund:.1f}%")
    _log(f"Trial→Refund survival rate: {survival_rate_trial_to_refund:.1f}%")
    _log(f"Drop-off during trial: {drop_off_trial:.1f}%")
    _log(f"Drop-off during refund: {drop_off_refund:.1f}%")
    _log(f"Total drop-off: {100 - conversion_refund:.1f}%")

    # Add a separator line as in other functions
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)

    plt.tight_layout()



    return fig, {
        'total_trials': total_trials,
        'survived_trial': survivors_trial,
        'survived_refund': survivors_refund,
        'conversion_trial_rate': conversion_trial,
        'conversion_refund_rate': conversion_refund,
        'survival_rate_trial_to_refund': survival_rate_trial_to_refund,
        'drop_off_trial': drop_off_trial,
        'drop_off_refund': drop_off_refund,
        'total_drop_off': 100 - conversion_refund,
        'cohort_week_start': cohort_monday,
        'cohort_week_end': cohort_sunday,
        'cohort_week_label': week_label,
        'cohort_week_key': cohort_week_key,
        'cohort_year': cohort_year,
        'cohort_week_number': cohort_week,
        'weeks_back': weeks_back
    }


def plot_cohort_conversion_funnel_comparison(sub_df, today_date, today_iso, last_cohort_dict):
    """
    Plot a conversion funnel comparing different cohorts with 3 bars:
    1. Initial trials
    2. Survivors after trial period (not canceled during trial)
    3. Survivors after refund period (not canceled during refund)

    """


    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    _log("Creating cohort conversion funnel comparison using ISO calendar...")

    # Check if there is data
    if 'trial_start_utc' not in sub_df.columns or sub_df['trial_start_utc'].isna().all():
        _log("No trial data found")
        return None, {}

    # last_total_trials = last_cohort_dict['total_trials']
    # last_survived_trial = last_cohort_dict['survived_trial']
    # last_survived_refund = last_cohort_dict['survived_refund']
    # last_conversion_trial_rate = last_cohort_dict['conversion_trial_rate']
    # last_conversion_refund_rate = last_cohort_dict['conversion_refund_rate']
    # last_total_drop_off = last_cohort_dict['total_drop_off']
    last_total_trials = last_cohort_dict.get('total_trials', 0)
    last_survived_trial = last_cohort_dict.get('survived_trial', 0)
    last_survived_refund = last_cohort_dict.get('survived_refund', 0)
    last_conversion_trial_rate = last_cohort_dict.get('conversion_trial_rate', 0)
    last_conversion_refund_rate = last_cohort_dict.get('conversion_refund_rate', 0)
    last_total_drop_off = last_cohort_dict.get('total_drop_off', 0)

    if 'cohort_week_key' in last_cohort_dict:
        # New format with ISO data - utilise .get() même après avoir vérifié l'existence
        complete_cohort_start = last_cohort_dict.get('cohort_week_start', None)
        complete_cohort_end = last_cohort_dict.get('cohort_week_end', None)
        complete_cohort_label = last_cohort_dict.get('cohort_week_label', 'Unknown')
        complete_cohort_key = last_cohort_dict.get('cohort_week_key', 'Unknown')
        _log(f"Using ISO cohort data: {complete_cohort_key}")
    else:
        complete_cohort_start = last_cohort_dict.get('cohort_week_start', None)
        complete_cohort_end = last_cohort_dict.get('cohort_week_end', None)
        complete_cohort_label = last_cohort_dict.get('cohort_week_label', 'Legacy Cohort')
        complete_cohort_key = "Unknown"
        _log("Using legacy cohort data format")

    _log("=== CALCULATING COMPARISON COHORTS WITH ISO FUNCTIONS ===")

    prev_weeks_back = 5

    try:
        prev_cohort_year, prev_cohort_week, prev_cohort_key = calculate_target_iso_week(today_iso, prev_weeks_back)
        prev_cohort_monday, prev_cohort_sunday = get_iso_week_bounds(prev_cohort_year, prev_cohort_week)

        # UTC conversion for comparison
        prev_cohort_monday_utc = pd.Timestamp(prev_cohort_monday).tz_localize('UTC')
        prev_cohort_sunday_utc = pd.Timestamp(prev_cohort_sunday).tz_localize('UTC') + pd.Timedelta(hours=23, minutes=59, seconds=59)

        _log(f"Previous cohort: {prev_cohort_key} ({prev_cohort_monday.strftime('%d-%m-%Y')} to {prev_cohort_sunday.strftime('%d-%m-%Y')})")

        prev_cohort_trials = sub_df[
            (sub_df['trial_start_utc'] >= prev_cohort_monday_utc) &
            (sub_df['trial_start_utc'] <= prev_cohort_sunday_utc)
        ]

        prev_total_trials = len(prev_cohort_trials)
        prev_survivors_trial = len(prev_cohort_trials[~prev_cohort_trials['canceled_during_trial']])
        prev_survivors_refund = len(prev_cohort_trials[
            (~prev_cohort_trials['canceled_during_trial']) &
            (~prev_cohort_trials['canceled_during_refund_period'])
        ])

    except Exception as e:
        _log(f"Error calculating previous cohort: {e}")
        prev_total_trials = prev_survivors_trial = prev_survivors_refund = 0
        prev_cohort_monday = prev_cohort_sunday = today_date
        prev_cohort_key = "Error"

    try:
        # 6-month period (24 weeks) ending 4 weeks ago
        six_m_end_year, six_m_end_week, six_m_end_key = calculate_target_iso_week(today_iso, weeks_back=4)
        six_m_start_year, six_m_start_week, six_m_start_key = calculate_target_iso_week(today_iso, weeks_back=28)  # 4 + 24

        six_m_start_monday, _ = get_iso_week_bounds(six_m_start_year, six_m_start_week)
        _, six_m_end_sunday = get_iso_week_bounds(six_m_end_year, six_m_end_week)

        # UTC conversion
        six_m_start_utc = pd.Timestamp(six_m_start_monday).tz_localize('UTC')
        six_m_end_utc = pd.Timestamp(six_m_end_sunday).tz_localize('UTC') + pd.Timedelta(hours=23, minutes=59, seconds=59)

        _log(f"6-month period: {six_m_start_key} to {six_m_end_key}")

        six_m_cohort_trials = sub_df[
            (sub_df['trial_start_utc'] >= six_m_start_utc) &
            (sub_df['trial_start_utc'] <= six_m_end_utc)
        ]

        six_m_time_divider = 24  # 24 weeks
        six_m_total_trials = len(six_m_cohort_trials) / six_m_time_divider
        six_m_survivors_trial = len(six_m_cohort_trials[~six_m_cohort_trials['canceled_during_trial']]) / six_m_time_divider
        six_m_survivors_refund = len(six_m_cohort_trials[
            (~six_m_cohort_trials['canceled_during_trial']) &
            (~six_m_cohort_trials['canceled_during_refund_period'])
        ]) / six_m_time_divider

    except Exception as e:
        _log(f"Error calculating 6-month average: {e}")
        six_m_total_trials = six_m_survivors_trial = six_m_survivors_refund = 0

    try:
        all_time_cohort_start = sub_df['trial_start_utc'].min()

        # Use the same end bound as 6-month period
        six_m_end_year, six_m_end_week, _ = calculate_target_iso_week(today_iso, weeks_back=4)
        _, all_time_cohort_end = get_iso_week_bounds(six_m_end_year, six_m_end_week)
        all_time_cohort_end_utc = pd.Timestamp(all_time_cohort_end).tz_localize('UTC') + pd.Timedelta(hours=23, minutes=59, seconds=59)

        if pd.notna(all_time_cohort_start):
            # Calculate the divider in ISO weeks
            all_time_divider = (all_time_cohort_end_utc - all_time_cohort_start).days / 7

            all_time_cohort_trials = sub_df[
                (sub_df['trial_start_utc'] >= all_time_cohort_start) &
                (sub_df['trial_start_utc'] <= all_time_cohort_end_utc)
            ]

            all_time_total_trials = len(all_time_cohort_trials) / all_time_divider
            all_time_survivors_trial = len(all_time_cohort_trials[~all_time_cohort_trials['canceled_during_trial']]) / all_time_divider
            all_time_survivors_refund = len(all_time_cohort_trials[
                (~all_time_cohort_trials['canceled_during_trial']) &
                (~all_time_cohort_trials['canceled_during_refund_period'])
            ]) / all_time_divider

            _log(f"All-time period: {all_time_cohort_start.strftime('%Y-%m-%d')} to {all_time_cohort_end.strftime('%Y-%m-%d')} ({all_time_divider:.1f} weeks)")
        else:
            all_time_total_trials = all_time_survivors_trial = all_time_survivors_refund = 0

    except Exception as e:
        _log(f"Error calculating all-time average: {e}")
        all_time_total_trials = all_time_survivors_trial = all_time_survivors_refund = 0

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    # Prepare data with ISO labels
    prev_cohort_label = f"{prev_cohort_monday.strftime('%d-%m-%y')} > {prev_cohort_sunday.strftime('%d-%m-%y')}"

    complete_cohort_label_short = complete_cohort_label.replace(' > ', '\n→ ')
    prev_cohort_label_short = prev_cohort_label.replace(' > ', '\n→ ')
    periods = [
        f'Last cohort\n{complete_cohort_label_short}',
        f'Previous cohort\n{prev_cohort_label_short}',
        '6 Month\nAverage',
        'All Time\nAverage'
    ]

    initial_trials = [last_total_trials, prev_total_trials, six_m_total_trials, all_time_total_trials]
    survived_trial = [last_survived_trial, prev_survivors_trial, six_m_survivors_trial, all_time_survivors_trial]
    full_members = [last_survived_refund, prev_survivors_refund, six_m_survivors_refund, all_time_survivors_refund]

    # Positioning of bars
    x = np.arange(len(periods))
    bar_width = 0.25

    colors = ['steelblue', 'orange', 'darkgreen']

    # Create bars
    bars1 = ax.bar(x - bar_width, initial_trials, bar_width,
                   label='Initial Trials', color=colors[0], alpha=0.7)
    bars2 = ax.bar(x, survived_trial, bar_width,
                   label='Survived Trial', color=colors[1], alpha=0.7)
    bars3 = ax.bar(x + bar_width, full_members, bar_width,
                   label='Full Members', color=colors[2], alpha=0.7)

    def add_value_labels(bars, values):
        # Protection against max() on empty lists
        max_val = max(max(initial_trials) if initial_trials else [0],
                      max(survived_trial) if survived_trial else [0],
                      max(full_members) if full_members else [0])
        max_val = max_val if max_val > 0 else 1

        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max_val * 0.01,
                    f'{value:.0f}', ha='center', va='bottom', fontweight='bold',
                    fontsize=10, color='darkblue')

    add_value_labels(bars1, initial_trials)
    add_value_labels(bars2, survived_trial)
    add_value_labels(bars3, full_members)

    # Add percentages inside bars
    def add_percentage_labels(bars, values, base_values):
        for i, (bar, value, base) in enumerate(zip(bars, values, base_values)):
            if base > 0:
                percentage = (value / base) * 100
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height/2,
                        f'{percentage:.1f}%', ha='center', va='center',
                        fontweight='bold', fontsize=9, color='white')

    # Add percentages (all relative to initial trials)
    add_percentage_labels(bars1, initial_trials, initial_trials)  # 100% for initial trials
    add_percentage_labels(bars2, survived_trial, initial_trials)
    add_percentage_labels(bars3, full_members, initial_trials)

    ax.set_xlabel('')
    ax.set_ylabel('Number of Users', fontsize=12)
    ax.set_title('CONVERSION FUNNEL COMPARISON ACROSS PERIODS\n(Using ISO Week Calculations)',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=9)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(axis='y', alpha=0.3)

    all_values = initial_trials + survived_trial + full_members
    max_value = max(all_values) if all_values else 1
    if max_value > 0:
        ax.set_ylim(0, max_value * 1.2)

    # Separator line
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)

    _log("=== CALCULATING COMPARISON METRICS ===")

    last_conversion_rate = last_conversion_refund_rate
    prev_conversion_rate = (prev_survivors_refund / prev_total_trials * 100) if prev_total_trials > 0 else 0
    six_m_conversion_rate = (six_m_survivors_refund / six_m_total_trials * 100) if six_m_total_trials > 0 else 0
    all_time_conversion_rate = (all_time_survivors_refund / all_time_total_trials * 100) if all_time_total_trials > 0 else 0

    _log(f"Last cohort ({complete_cohort_key}): {last_conversion_rate:.1f}%")
    _log(f"Previous cohort ({prev_cohort_key}): {prev_conversion_rate:.1f}%")
    _log(f"6-month average: {six_m_conversion_rate:.1f}%")
    _log(f"All-time average: {all_time_conversion_rate:.1f}%")

    plt.tight_layout()



    cohort_dict = fig, {
        'last_cohort': {
            'values': [last_total_trials, last_survived_trial, last_survived_refund],
            'conversion_rate': last_conversion_rate,
            'week_label': complete_cohort_label,
            'week_key': complete_cohort_key if 'cohort_week_key' in last_cohort_dict else "Unknown"
        },
        'prev_cohort': {
            'values': [prev_total_trials, prev_survivors_trial, prev_survivors_refund],
            'conversion_rate': prev_conversion_rate,
            'week_label': prev_cohort_label,
            'week_key': prev_cohort_key if 'prev_cohort_key' in locals() else "Unknown"
        },
        'six_month_avg': {
            'values': [six_m_total_trials, six_m_survivors_trial, six_m_survivors_refund],
            'conversion_rate': six_m_conversion_rate,
            'period_start_key': six_m_start_key if 'six_m_start_key' in locals() else "Unknown",
            'period_end_key': six_m_end_key if 'six_m_end_key' in locals() else "Unknown"
        },
        'all_time_avg': {
            'values': [all_time_total_trials, all_time_survivors_trial, all_time_survivors_refund],
            'conversion_rate': all_time_conversion_rate
        }
    }

    return fig, cohort_dict
__all__ = [
    "plot_cohort_conversion_funnel",
    "plot_cohort_conversion_funnel_comparison",
]
