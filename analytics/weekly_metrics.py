"""ISO week helpers and weekly subscription flow metrics."""

from .common import *
from .subscriptions import cus_renewal

def plot_weekly_trials_8_weeks(sub_df, today_date, today_iso, num_weeks=8):
    """
    Plot new trials each week for the last N weeks (default 8) using ISO calendar
    """

    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    _log(f"Creating LAST {num_weeks} WEEKS trials analysis using ISO calendar...")

    # Check if there is data
    if 'trial_start_utc' not in sub_df.columns or sub_df['trial_start_utc'].isna().all():
        _log("No trial data found")
        return {}

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

    iso_week_keys = []
    current_year, current_week = today_iso.year, today_iso.week

    for i in range(num_weeks):
        # Add current week
        iso_week_key = f"{current_year}-W{current_week:02d}"
        iso_week_keys.insert(0, iso_week_key)  # Insert at beginning for chronological order

        # Go back one ISO week correctly with get_weeks_in_iso_year
        current_week -= 1
        if current_week <= 0:
            current_year -= 1
            current_week = get_weeks_in_iso_year(current_year)

    _log(f"Analysis from {iso_week_keys[0]} to {iso_week_keys[-1]} ({len(iso_week_keys)} ISO weeks)")

    _log("Adding ISO week columns...")

    # Add ISO columns to trials DataFrame
    trials_with_iso = add_iso_week_columns(sub_df, 'trial_start_utc')

    # Group by ISO week instead of Pandas Grouper
    weekly_trials = trials_with_iso[trials_with_iso['iso_week_key'].notna()].groupby('iso_week_key').size()

    weekly_trials = weekly_trials.reindex(iso_week_keys, fill_value=0)

    week_labels = []
    week_dates = []

    for week_key in iso_week_keys:
        try:
            year, week = week_key.split('-W')
            year, week = int(year), int(week)

            # USE STANDARDIZED FUNCTION get_iso_week_bounds
            monday, sunday = get_iso_week_bounds(year, week)

            week_labels.append(f"{monday.strftime('%d-%m-%y')} > {sunday.strftime('%d-%m-%y')}")
            week_dates.append(monday)

        except Exception as e:
            _log(f"Error processing week {week_key}: {e}")
            week_labels.append(week_key)
            week_dates.append(today_date)  # Fallback

    x_pos = range(len(iso_week_keys))

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    bars = ax.bar(x_pos, weekly_trials, label='New Trials',
                  color='steelblue', alpha=0.7)

    for i, v in enumerate(weekly_trials):
        if v > 0:
            # Protection against empty series
            max_trials = max(weekly_trials) if len(weekly_trials) > 0 and max(weekly_trials) > 0 else 1
            ax.text(i, v + max_trials * 0.01, str(int(v)),
                   ha='center', va='bottom', fontsize=9, color='darkblue', fontweight='bold')

    ax.set_ylabel('Number of New Trials per Week', fontsize=12)
    ax.set_xlabel('Weeks (Monday - Sunday)', fontsize=12)

    ax.grid(True, alpha=0.3, axis='y')

    if len(weekly_trials) > 0 and max(weekly_trials) > 0:
        y_max = max(weekly_trials) * 1.2
        ax.set_ylim(0, y_max)
    else:
        ax.set_ylim(0, 1)

    ax.set_xlim(-0.5, len(x_pos) - 0.5)

    # X-axis configuration - show all labels for short periods
    ax.set_xticks(x_pos)
    ax.set_xticklabels(week_labels, rotation=45, ha='right', fontsize=9)

    # Calculate immature cutoff week (1 week before for trials - most recent)
    immature_year, immature_week, immature_cutoff_key = calculate_target_iso_week(today_iso, weeks_back=0)

    _log(f"Immature cutoff at: {immature_cutoff_key}")

    immature_weeks = []
    for i, week_key in enumerate(iso_week_keys):
        # Compare ISO weeks directly
        if week_key >= immature_cutoff_key:
            immature_weeks.append(i)

    if immature_weeks:
        start_idx = min(immature_weeks) - 0.4
        end_idx = max(immature_weeks) + 0.5
        ax.axvspan(start_idx, end_idx, alpha=0.2, color='gray',
                   label='Current week not ended', zorder=0)
        _log(f"Immature period: {len(immature_weeks)} recent weeks")

    if len(week_dates) > 0:
        start_date = week_dates[0].strftime("%d-%m-%Y")
        end_date = week_dates[-1].strftime("%d-%m-%Y")
        period_text = f'Last {num_weeks} weeks (from {start_date} to {end_date})'
    else:
        period_text = f'Last {num_weeks} weeks'

    ax.set_title(f'WEEKLY NEW TRIALS\n{period_text}',
                 fontsize=16, fontweight='bold', pad=20)

    ax.legend(loc='upper right', fontsize=10)

    _log("=== CALCULATING METRICS ===")

    # Calculer les métriques en EXCLUANT la semaine courante (immature)
    # Filtrer les données pour exclure les semaines >= immature_cutoff_key
    mature_weeks_mask = pd.Series(iso_week_keys) < immature_cutoff_key
    mature_iso_weeks = [week for i, week in enumerate(iso_week_keys) if mature_weeks_mask.iloc[i]]

    if len(mature_iso_weeks) == 0:
        _log("No mature weeks available for calculations")
        # Fallback sur toutes les semaines si pas de semaines matures
        mature_weekly_trials = weekly_trials
        mature_iso_weeks = iso_week_keys
    else:
        # Filtrer weekly_trials pour ne garder que les semaines matures
        mature_weekly_trials = weekly_trials.loc[mature_iso_weeks]

    # Calculer les métriques sur les semaines matures uniquement
    total_trials = mature_weekly_trials.sum()
    avg_trials = mature_weekly_trials.mean() if len(mature_weekly_trials) > 0 else 0
    max_trials_value = mature_weekly_trials.max() if len(mature_weekly_trials) > 0 else 0
    min_trials_value = mature_weekly_trials.min() if len(mature_weekly_trials) > 0 else 0

    if len(mature_weekly_trials) > 0:
        max_week_idx = mature_weekly_trials.idxmax()
        min_week_idx = mature_weekly_trials.idxmin()

        # Trouver les positions dans la série complète pour les labels
        max_week_position = iso_week_keys.index(max_week_idx)
        min_week_position = iso_week_keys.index(min_week_idx)

        max_week_label = week_labels[max_week_position]
        min_week_label = week_labels[min_week_position]
    else:
        max_week_label = "N/A"
        min_week_label = "N/A"

    # Additional metrics - utiliser les semaines matures pour les dernières semaines
    if len(mature_weekly_trials) >= 2:
        latest_mature_week = mature_weekly_trials.iloc[-1]
        previous_mature_week = mature_weekly_trials.iloc[-2]
        latest_week_text = f"Latest complete week: {latest_mature_week:,} trials\nPrevious week: {previous_mature_week:,} trials"
        week_over_week_change = latest_mature_week - previous_mature_week
        week_over_week_pct = (week_over_week_change / previous_mature_week * 100) if previous_mature_week > 0 else 0
    elif len(mature_weekly_trials) >= 1:
        latest_mature_week = mature_weekly_trials.iloc[-1]
        previous_mature_week = 0
        latest_week_text = f"Latest complete week: {latest_mature_week:,} trials\nPrevious week: N/A"
        week_over_week_change = 0
        week_over_week_pct = 0
    else:
        latest_mature_week = 0
        previous_mature_week = 0
        latest_week_text = f"Latest complete week: N/A\nPrevious week: N/A"
        week_over_week_change = 0
        week_over_week_pct = 0

    # Calculer le nombre de semaines matures
    num_weeks_mature = len(mature_weekly_trials)

    # Calculer les dates de période pour les semaines matures uniquement
    if len(mature_iso_weeks) > 0:
        # Trouver les positions des semaines matures dans la liste complète
        mature_positions = [i for i, week in enumerate(iso_week_keys) if week in mature_iso_weeks]
        mature_start_date = week_dates[mature_positions[0]].strftime("%d-%m-%Y") if mature_positions else "N/A"
        mature_end_date = week_dates[mature_positions[-1]].strftime("%d-%m-%Y") if mature_positions else "N/A"
    else:
        mature_start_date = "N/A"
        mature_end_date = "N/A"

    # Trend metrics - utiliser les semaines matures
    if len(mature_weekly_trials) >= 4:
        # Average of last 4 mature weeks
        recent_4w_avg = mature_weekly_trials.iloc[-4:].mean()
        _log(f"Total trials (mature weeks only): {total_trials:,}")
        _log(f"Average per week (mature weeks only): {avg_trials:.1f}")
        _log(f"Recent 4-week average (mature): {recent_4w_avg:.1f}")
    else:
        recent_4w_avg = avg_trials  # Fallback si moins de 4 semaines
        _log(f"Total trials (mature weeks only): {total_trials:,}")
        _log(f"Average per week (mature weeks only): {avg_trials:.1f}")

    _log(f"Maximum week: {max_trials_value:,}")
    _log(f"Minimum week: {min_trials_value:,}")
    _log(f"Number of mature weeks: {num_weeks_mature:,}")
    _log(f"Total weeks displayed: {num_weeks:,}")
    _log(f"Mature period: from {mature_start_date} to {mature_end_date}")
    _log(latest_week_text)

    if len(mature_weekly_trials) >= 2:
        _log(f"Week-over-week change (mature): {week_over_week_change:+,} ({week_over_week_pct:+.1f}%)")

    plt.tight_layout()

    return fig, {
        'total_trials': total_trials,  # Calculé sur semaines matures uniquement
        'average_per_week': avg_trials,  # Calculé sur semaines matures uniquement
        'max_week': max_trials_value,
        'max_week_label': max_week_label,
        'min_week': min_trials_value,
        'min_week_label': min_week_label,
        'latest_week': latest_mature_week,  # Dernière semaine mature
        'previous_week': previous_mature_week,  # Avant-dernière semaine mature
        'week_over_week_change': week_over_week_change,
        'week_over_week_pct': week_over_week_pct,
        'num_weeks': num_weeks,  # Total semaines affichées (incluant courante)
        'num_weeks_mature': num_weeks_mature,  # Semaines matures pour calculs
        'weekly_data': weekly_trials.tolist(),  # Toutes les semaines pour graphique
        'weekly_trials_series': weekly_trials,  # Toutes les semaines pour graphique
        'mature_weekly_trials': mature_weekly_trials,  # Semaines matures pour calculs
        'iso_week_keys': iso_week_keys,  # Toutes les semaines
        'mature_iso_weeks': mature_iso_weeks,  # Semaines matures uniquement
        'week_labels': week_labels,
        'week_dates': week_dates,
        'start_date': start_date,  # Période complète affichée
        'end_date': end_date,      # Période complète affichée
        'mature_start_date': mature_start_date,  # Période des calculs (matures)
        'mature_end_date': mature_end_date,      # Période des calculs (matures)
        'period_text': period_text,  # Période complète
        'recent_4w_avg': recent_4w_avg,  # Calculé sur semaines matures
        'immature_cutoff_key': immature_cutoff_key  # Seuil semaine courante
    }


def plot_weekly_trials_all_time(sub_df, today_date, today_iso):
    """
    Plot new trials each week since the beginning using ISO calendar
    """

    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    # Check if there is data
    if 'trial_start_utc' not in sub_df.columns or sub_df['trial_start_utc'].isna().all():
        _log("No trial data found")
        return {}

    first_date = sub_df['trial_start_utc'].min()
    if pd.isna(first_date):
        _log("No trial data found")
        return {}

    _log(f"Creating ALL TIME weekly trials analysis using ISO calendar...")
    _log(f"Analysis since first date: {first_date.strftime('%d-%m-%Y')}")

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

    _log("Adding ISO week columns...")

    # Add ISO columns to trials DataFrame
    trials_with_iso = add_iso_week_columns(sub_df, 'trial_start_utc')

    # Group by ISO week instead of Pandas Grouper
    weekly_trials = trials_with_iso[trials_with_iso['iso_week_key'].notna()].groupby('iso_week_key').size()

    # Check if there is data after grouping
    if len(weekly_trials) == 0:
        _log("No trial data found after ISO grouping")
        return {}

    all_iso_weeks = weekly_trials.index.tolist()

    def sort_iso_weeks(week_keys):
        """Sort ISO week keys by year and week"""
        def parse_week(week_key):
            try:
                if pd.isna(week_key) or week_key == '<NA>' or not isinstance(week_key, str):
                    return (0, 0)
                year, week = week_key.split('-W')
                return (int(year), int(week))
            except (ValueError, AttributeError):
                _log(f"Invalid week key ignored: {week_key}")
                return (0, 0)

        valid_weeks = [week for week in week_keys
                      if pd.notna(week) and week != '<NA>' and isinstance(week, str) and '-W' in str(week)]
        return sorted(valid_weeks, key=parse_week)

    sorted_iso_weeks = sort_iso_weeks(all_iso_weeks)

    if not sorted_iso_weeks:
        _log("No valid ISO weeks after filtering")
        return {}

    # Get start and end dates for display
    first_week_key = sorted_iso_weeks[0]
    last_week_key = sorted_iso_weeks[-1]
    num_weeks = len(sorted_iso_weeks)

    _log(f"Analysis from {first_week_key} to {last_week_key} ({num_weeks} ISO weeks)")

    weekly_trials = weekly_trials.reindex(sorted_iso_weeks, fill_value=0)

    week_labels = []
    week_dates = []

    for week_key in sorted_iso_weeks:
        try:
            year, week = week_key.split('-W')
            year, week = int(year), int(week)

            # USE STANDARDIZED FUNCTION get_iso_week_bounds
            monday, sunday = get_iso_week_bounds(year, week)

            week_labels.append(f"{monday.strftime('%d-%m-%y')} > {sunday.strftime('%d-%m-%y')}")
            week_dates.append(monday)

        except Exception as e:
            _log(f"Error processing week {week_key}: {e}")
            week_labels.append(week_key)
            week_dates.append(today_date)  # Fallback

    x_pos = range(len(sorted_iso_weeks))

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    bars = ax.bar(x_pos, weekly_trials, label='New Trials',
                  color='steelblue', alpha=0.7)

    for i, v in enumerate(weekly_trials):
        if v > 0:
            max_trials = max(weekly_trials) if len(weekly_trials) > 0 and max(weekly_trials) > 0 else 1
            ax.text(i, v + max_trials * 0.01, str(int(v)),
                   ha='center', va='bottom', fontsize=7, color='darkblue')

    ax.set_ylabel('Number of New Trials per Week', fontsize=12)
    ax.set_xlabel('Weeks (Monday - Sunday)', fontsize=12)

    ax.grid(True, alpha=0.3, axis='y')

    if len(weekly_trials) > 0 and max(weekly_trials) > 0:
        y_max = max(weekly_trials) * 1.2
        ax.set_ylim(0, y_max)
    else:
        ax.set_ylim(0, 1)

    ax.set_xlim(-0.3, len(x_pos) - 0.5)

    # X-axis configuration - reduce labels for long periods
    step = max(1, len(x_pos) // 10)
    ax.set_xticks(x_pos[::step])
    ax.set_xticklabels([week_labels[i] for i in x_pos[::step]],
                       rotation=45, ha='right', fontsize=9)

    # Calculate immature cutoff week (1 week before for trials - most recent)
    immature_year, immature_week, immature_cutoff_key = calculate_target_iso_week(today_iso, weeks_back=0)

    _log(f"Immature cutoff at: {immature_cutoff_key}")

    immature_weeks = []
    for i, week_key in enumerate(sorted_iso_weeks):
        # Compare ISO weeks directly
        if week_key >= immature_cutoff_key:
            immature_weeks.append(i)

    if immature_weeks:
        start_idx = min(immature_weeks) - 0.4
        end_idx = max(immature_weeks) + 0.5
        ax.axvspan(start_idx, end_idx, alpha=0.15, color='gray',
                   label='Current week not ended', zorder=0)
        _log(f"Immature period: {len(immature_weeks)} recent weeks")

    start_date = week_dates[0].strftime("%d-%m-%Y") if week_dates else "N/A"
    end_date = week_dates[-1].strftime("%d-%m-%Y") if week_dates else "N/A"

    period_text = f'(from {start_date} to {end_date})'
    ax.set_title(f'WEEKLY NEW TRIALS - ALL TIME\n{period_text}',
                 fontsize=18, fontweight='bold', pad=30)

    ax.legend(loc='upper right', fontsize=10)

    _log("=== CALCULATING METRICS ===")

    # Calculer les métriques en EXCLUANT la semaine courante (immature)
    # Filtrer les données pour exclure les semaines >= immature_cutoff_key
    mature_weeks_mask = pd.Series(sorted_iso_weeks) < immature_cutoff_key
    mature_iso_weeks = [week for i, week in enumerate(sorted_iso_weeks) if mature_weeks_mask.iloc[i]]

    if len(mature_iso_weeks) == 0:
        _log("No mature weeks available for calculations")
        # Fallback sur toutes les semaines si pas de semaines matures
        mature_weekly_trials = weekly_trials
        mature_iso_weeks = sorted_iso_weeks
    else:
        # Filtrer weekly_trials pour ne garder que les semaines matures
        mature_weekly_trials = weekly_trials.loc[mature_iso_weeks]

    # Calculer les métriques sur les semaines matures uniquement
    total_trials = mature_weekly_trials.sum()
    avg_trials = mature_weekly_trials.mean() if len(mature_weekly_trials) > 0 else 0
    max_trials_value = mature_weekly_trials.max() if len(mature_weekly_trials) > 0 else 0
    min_trials_value = mature_weekly_trials.min() if len(mature_weekly_trials) > 0 else 0

    if len(mature_weekly_trials) > 0:
        max_week_idx = mature_weekly_trials.idxmax()
        min_week_idx = mature_weekly_trials.idxmin()

        # Trouver les positions dans la série complète pour les labels
        max_week_position = sorted_iso_weeks.index(max_week_idx)
        min_week_position = sorted_iso_weeks.index(min_week_idx)

        max_week_label = week_labels[max_week_position]
        min_week_label = week_labels[min_week_position]
    else:
        max_week_label = "N/A"
        min_week_label = "N/A"

    # Additional metrics - utiliser les semaines matures pour les dernières semaines
    if len(mature_weekly_trials) >= 2:
        latest_mature_week = mature_weekly_trials.iloc[-1]
        previous_mature_week = mature_weekly_trials.iloc[-2]
        latest_week_text = f"Latest complete week: {latest_mature_week:,} trials\nPrevious week: {previous_mature_week:,} trials"
        week_over_week_change = latest_mature_week - previous_mature_week
        week_over_week_pct = (week_over_week_change / previous_mature_week * 100) if previous_mature_week > 0 else 0
    elif len(mature_weekly_trials) >= 1:
        latest_mature_week = mature_weekly_trials.iloc[-1]
        previous_mature_week = 0
        latest_week_text = f"Latest complete week: {latest_mature_week:,} trials\nPrevious week: N/A"
        week_over_week_change = 0
        week_over_week_pct = 0
    else:
        latest_mature_week = 0
        previous_mature_week = 0
        latest_week_text = f"Latest complete week: N/A\nPrevious week: N/A"
        week_over_week_change = 0
        week_over_week_pct = 0

    # Calculer le nombre de semaines matures
    num_weeks_mature = len(mature_weekly_trials)

    # Calculer les dates de période pour les semaines matures uniquement
    if len(mature_iso_weeks) > 0:
        # Trouver les positions des semaines matures dans la liste complète
        mature_positions = [i for i, week in enumerate(sorted_iso_weeks) if week in mature_iso_weeks]
        mature_start_date = week_dates[mature_positions[0]].strftime("%d-%m-%Y") if mature_positions else "N/A"
        mature_end_date = week_dates[mature_positions[-1]].strftime("%d-%m-%Y") if mature_positions else "N/A"
    else:
        mature_start_date = "N/A"
        mature_end_date = "N/A"

    _log(f"Total trials (mature weeks only): {total_trials:,}")
    _log(f"Average per week (mature weeks only): {avg_trials:.1f}")
    _log(f"Maximum week: {max_trials_value:,}")
    _log(f"Minimum week: {min_trials_value:,}")
    _log(f"Number of mature weeks: {num_weeks_mature:,}")
    _log(f"Total weeks displayed: {num_weeks:,}")
    _log(f"Mature period: from {mature_start_date} to {mature_end_date}")
    _log(latest_week_text)
    if len(mature_weekly_trials) >= 2:
        _log(f"Week-over-week change (mature): {week_over_week_change:+,} ({week_over_week_pct:+.1f}%)")

    plt.tight_layout()

    return fig, {
        'total_trials': total_trials,  # Calculé sur semaines matures uniquement
        'average_per_week': avg_trials,  # Calculé sur semaines matures uniquement
        'max_week': max_trials_value,
        'max_week_label': max_week_label,
        'min_week': min_trials_value,
        'min_week_label': min_week_label,
        'latest_week': latest_mature_week,  # Dernière semaine mature
        'previous_week': previous_mature_week,  # Avant-dernière semaine mature
        'week_over_week_change': week_over_week_change,
        'week_over_week_pct': week_over_week_pct,
        'num_weeks': num_weeks,  # Total semaines affichées (incluant courante)
        'num_weeks_mature': num_weeks_mature,  # Semaines matures pour calculs
        'weekly_data': weekly_trials.tolist(),  # Toutes les semaines pour graphique
        'weekly_trials_series': weekly_trials,  # Toutes les semaines pour graphique
        'mature_weekly_trials': mature_weekly_trials,  # Semaines matures pour calculs
        'iso_weeks': sorted_iso_weeks,  # Toutes les semaines
        'mature_iso_weeks': mature_iso_weeks,  # Semaines matures uniquement
        'week_dates': week_dates,
        'first_week_key': first_week_key,
        'last_week_key': last_week_key,
        'start_date': start_date,  # Période complète affichée
        'end_date': end_date,      # Période complète affichée
        'mature_start_date': mature_start_date,  # Période des calculs (matures)
        'mature_end_date': mature_end_date,      # Période des calculs (matures)
        'period_text': period_text,  # Période complète
        'immature_cutoff_key': immature_cutoff_key  # Seuil semaine courante
    }


def weekly_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8):
    """
    Plot weekly metrics for last N weeks (default 8) using ISO calendar
    North: Conversions (Trial→Full)
    South: Churn full members
    Focus: Full members only (no renewals)

    """

    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    # Get renewal data (for consistency with weekly_flow_all_time)
    renewal_dict = cus_renewal(sub_df, today_date)
    trial_to_full_member_df = renewal_dict['trial_to_full_member_df']

    full_member_churn_df = renewal_dict['trial_to_full_member_df']
    full_member_churn_df = full_member_churn_df[full_member_churn_df['is_full_member'] == True]

    _log(f"Creating LAST {num_weeks} WEEKS flow analysis using ISO calendar...")

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

    # Generate the last N ISO weeks correctly with calculate_target_iso_week
    iso_weeks = []
    current_year, current_week = today_iso.year, today_iso.week

    for i in range(num_weeks):
        # Add current week
        iso_week_key = f"{current_year}-W{current_week:02d}"
        iso_weeks.insert(0, iso_week_key)  # Insert at beginning for chronological order

        # Go back one ISO week correctly
        current_week -= 1
        if current_week <= 0:
            current_year -= 1
            current_week = get_weeks_in_iso_year(current_year)

    _log(f"Analysis from {iso_weeks[0]} to {iso_weeks[-1]} ({len(iso_weeks)} ISO weeks)")

    _log("Adding ISO week columns...")

    # Conversions (account creations)
    conversion_customers = add_iso_week_columns(trial_to_full_member_df, 'refund_period_end_utc')

    # Churn (cancellations)
    churn_customers = add_iso_week_columns(full_member_churn_df.copy(), 'canceled_at_utc')

    # Filter valid data before groupby
    weekly_conversions = conversion_customers[conversion_customers['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_churn = churn_customers[churn_customers['iso_week_key'].notna()].groupby('iso_week_key').size()

    weekly_conversions = weekly_conversions.reindex(iso_weeks, fill_value=0)
    weekly_churn = weekly_churn.reindex(iso_weeks, fill_value=0)

    week_labels = []
    week_dates = []

    for week_key in iso_weeks:
        try:
            year, week = week_key.split('-W')
            year, week = int(year), int(week)

            # USE STANDARDIZED FUNCTION get_iso_week_bounds
            monday, sunday = get_iso_week_bounds(year, week)

            week_labels.append(f"{monday.strftime('%d-%m-%y')} > {sunday.strftime('%d-%m-%y')}")
            week_dates.append(monday)

        except Exception as e:
            _log(f"Error processing week {week_key}: {e}")
            week_labels.append(week_key)
            week_dates.append(today_date)  # Fallback

    x_pos = range(len(iso_weeks))

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    ax.bar(x_pos, weekly_conversions, label='Conversions (Trial→Full)', color='green')

    ax.bar(x_pos, -weekly_churn, label='Churn Full Members', color='red')

    ax.set_ylabel('Full Members per week\n(Positive: Gains | Negative: Losses)', fontsize=12)
    ax.set_xlabel('Weeks (Monday - Sunday)', fontsize=12)

    for i, (conv, churn) in enumerate(zip(weekly_conversions, weekly_churn)):
        if conv > 0:
            # Protection against empty series
            max_conv = max(weekly_conversions) if len(weekly_conversions) > 0 and max(weekly_conversions) > 0 else 1
            ax.text(i, conv + max_conv * 0.02, str(int(conv)),
                   ha='center', va='bottom', fontsize=9, color='darkgreen', fontweight='bold')

        if churn > 0:
            # Protection against empty series
            max_churn = max(weekly_churn) if len(weekly_churn) > 0 and max(weekly_churn) > 0 else 1
            ax.text(i, -churn - max_churn * 0.02, str(int(churn)),
                   ha='center', va='top', fontsize=9, color='darkred', fontweight='bold')

    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-0.5, len(x_pos) - 0.5)

    if len(weekly_conversions) > 0 and max(weekly_conversions) > 0:
        y_max = max(weekly_conversions) * 1.2
    else:
        y_max = 1

    if len(weekly_churn) > 0 and max(weekly_churn) > 0:
        y_min = -max(weekly_churn) * 1.2
    else:
        y_min = -1

    ax.set_ylim(y_min, y_max)

    # X-axis configuration - show all labels for short periods
    ax.set_xticks(x_pos)
    ax.set_xticklabels(week_labels, rotation=45, ha='right', fontsize=9)

    # Calculate immature cutoff week (current week)
    immature_year, immature_week, immature_cutoff_key = calculate_target_iso_week(today_iso, weeks_back=0)

    _log(f"Immature cutoff at: {immature_cutoff_key}")

    immature_weeks = []
    for i, week_key in enumerate(iso_weeks):
        # Compare ISO weeks directly
        if week_key >= immature_cutoff_key:
            immature_weeks.append(i)

    if immature_weeks:
        start_idx = min(immature_weeks) - 0.4
        end_idx = max(immature_weeks) + 0.5
        ax.axvspan(start_idx, end_idx, alpha=0.2, color='gray',
                   label='Current week not ended', zorder=0)
        _log(f"Immature period: {len(immature_weeks)} recent weeks")

    if len(week_dates) > 0:
        start_date = week_dates[0].strftime("%d-%m-%Y")
        end_date = week_dates[-1].strftime("%d-%m-%Y")
        period_text = f'{num_weeks} last weeks (from {start_date} to {end_date})'
    else:
        period_text = f'{num_weeks} last weeks'

    ax.set_title(f'WEEKLY FULL MEMBERS FLOW\n{period_text}',
                 fontsize=16, fontweight='bold', pad=20)

    # Legends
    lines1, labels1 = ax.get_legend_handles_labels()
    ax.legend(lines1, labels1, loc='best', fontsize=10)

    _log("=== CALCULATING METRICS ===")

    # Calculer les métriques en EXCLUANT la semaine courante (immature)
    # Filtrer les données pour exclure les semaines >= immature_cutoff_key
    mature_weeks_mask = pd.Series(iso_weeks) < immature_cutoff_key
    mature_iso_weeks = [week for i, week in enumerate(iso_weeks) if mature_weeks_mask.iloc[i]]

    if len(mature_iso_weeks) == 0:
        _log("No mature weeks available for calculations")
        # Fallback sur toutes les semaines si pas de semaines matures
        mature_weekly_conversions = weekly_conversions
        mature_weekly_churn = weekly_churn
        mature_iso_weeks = iso_weeks
    else:
        # Filtrer les séries pour ne garder que les semaines matures
        mature_weekly_conversions = weekly_conversions.loc[mature_iso_weeks]
        mature_weekly_churn = weekly_churn.loc[mature_iso_weeks]

    # Calculer les métriques sur les semaines matures uniquement
    total_conversions = mature_weekly_conversions.sum()
    total_churn = mature_weekly_churn.sum()
    net_growth = total_conversions - total_churn

    # Calculer le nombre de semaines matures
    num_weeks_mature = len(mature_weekly_conversions)

    # Additional metrics for consistency - utiliser les semaines matures
    avg_conversions_per_week = total_conversions / num_weeks_mature if num_weeks_mature > 0 else 0
    avg_churn_per_week = total_churn / num_weeks_mature if num_weeks_mature > 0 else 0
    avg_net_growth = (total_conversions - total_churn) / num_weeks_mature if num_weeks_mature > 0 else 0

    if len(mature_weekly_conversions) > 0:
        max_conv_value = mature_weekly_conversions.max()
        min_conv_value = mature_weekly_conversions.min()
        max_conv_idx = mature_weekly_conversions.idxmax()
        min_conv_idx = mature_weekly_conversions.idxmin()

        max_conv_position = iso_weeks.index(max_conv_idx)
        min_conv_position = iso_weeks.index(min_conv_idx)

        max_conv_label = week_labels[max_conv_position]
        min_conv_label = week_labels[min_conv_position]
    else:
        max_conv_value = min_conv_value = 0
        max_conv_label = min_conv_label = "N/A"

    if len(mature_weekly_churn) > 0:
        max_churn_value = mature_weekly_churn.max()
        min_churn_value = mature_weekly_churn.min()
        max_churn_idx = mature_weekly_churn.idxmax()
        min_churn_idx = mature_weekly_churn.idxmin()

        max_churn_position = iso_weeks.index(max_churn_idx)
        min_churn_position = iso_weeks.index(min_churn_idx)

        max_churn_label = week_labels[max_churn_position]
        min_churn_label = week_labels[min_churn_position]
    else:
        max_churn_value = min_churn_value = 0
        max_churn_label = min_churn_label = "N/A"

    # Calculer les dates de période pour les semaines matures uniquement
    if len(mature_iso_weeks) > 0:
        # Trouver les positions des semaines matures dans la liste complète
        mature_positions = [i for i, week in enumerate(iso_weeks) if week in mature_iso_weeks]
        mature_start_date = week_dates[mature_positions[0]].strftime("%d-%m-%Y") if mature_positions else "N/A"
        mature_end_date = week_dates[mature_positions[-1]].strftime("%d-%m-%Y") if mature_positions else "N/A"
    else:
        mature_start_date = "N/A"
        mature_end_date = "N/A"

    _log(f"Total conversions (mature weeks only): {total_conversions:,}")
    _log(f"Total churn (mature weeks only): {total_churn:,}")
    _log(f"Net growth (mature weeks only): {net_growth:,}")
    _log(f"Number of mature weeks: {num_weeks_mature:,}")
    _log(f"Total weeks displayed: {num_weeks:,}")
    _log(f"Mature period: from {mature_start_date} to {mature_end_date}")
    _log(f"Avg conversions per week (mature): {avg_conversions_per_week:.1f}")
    _log(f"Avg churn per week (mature): {avg_churn_per_week:.1f}")
    _log(f"Avg net growth per week (mature): {avg_net_growth:.1f}")

    plt.tight_layout()

    return fig, {
        'conversions': total_conversions,  # Calculé sur semaines matures uniquement
        'churn': total_churn,  # Calculé sur semaines matures uniquement
        'net_growth': net_growth,  # Calculé sur semaines matures uniquement
        'num_weeks': num_weeks,  # Total semaines affichées (incluant courante)
        'num_weeks_mature': num_weeks_mature,  # Semaines matures pour calculs
        'avg_conversions_per_week': avg_conversions_per_week,  # Calculé sur semaines matures
        'avg_churn_per_week': avg_churn_per_week,  # Calculé sur semaines matures
        'avg_net_growth': avg_net_growth,  # Calculé sur semaines matures
        'weekly_conversions': weekly_conversions,  # Toutes les semaines pour graphique
        'weekly_churn': weekly_churn,  # Toutes les semaines pour graphique
        'mature_weekly_conversions': mature_weekly_conversions,  # Semaines matures pour calculs
        'mature_weekly_churn': mature_weekly_churn,  # Semaines matures pour calculs
        'iso_weeks': iso_weeks,  # Toutes les semaines
        'mature_iso_weeks': mature_iso_weeks,  # Semaines matures uniquement
        'week_dates': week_dates,
        'start_date': start_date,  # Période complète affichée
        'end_date': end_date,      # Période complète affichée
        'mature_start_date': mature_start_date,  # Période des calculs (matures)
        'mature_end_date': mature_end_date,      # Période des calculs (matures)
        'period_text': period_text,  # Période complète
        'max_churn_label': max_churn_label,
        'max_churn_value': max_churn_value,
        'min_churn_label': min_churn_label,
        'min_churn_value': min_churn_value,
        'min_conv_value': min_conv_value,
        'min_conv_label': min_conv_label,
        'max_conv_value': max_conv_value,
        'max_conv_label': max_conv_label,
        'immature_cutoff_key': immature_cutoff_key  # Seuil semaine courante
    }


def weekly_flow_all_time(sub_df, today_date, today_iso):
    """
    Plot weekly metrics for ALL TIME using ISO calendar
    North: Conversions (Trial→Full)
    South: Churn full members
    + Cumulative line plot

    """

    # Obtain renewal data
    renewal_dict = cus_renewal(sub_df, today_date)
    trial_to_full_member_df = renewal_dict['trial_to_full_member_df']

    _log("Creating ALL TIME weekly flow analysis using ISO calendar...")

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

    _log("Adding ISO week columns...")

    # Conversions (account creations)
    conversion_customers = add_iso_week_columns(trial_to_full_member_df, 'refund_period_end_utc')

    # Churn (cancellations)
    churn_customers = add_iso_week_columns(trial_to_full_member_df.copy(), 'canceled_at_utc')

    # Filter valid data before groupby
    weekly_conversions = conversion_customers[conversion_customers['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_churn = churn_customers[churn_customers['iso_week_key'].notna()].groupby('iso_week_key').size()

    all_iso_weeks = set()

    for series in [weekly_conversions, weekly_churn]:
        if len(series) > 0:
            all_iso_weeks.update(series.index.tolist())

    if not all_iso_weeks:
        _log("No data found")
        return {}

    def sort_iso_weeks(week_keys):
        """Sort ISO week keys by year and week"""
        def parse_week(week_key):
            try:
                year, week = week_key.split('-W')
                return (int(year), int(week))
            except (ValueError, AttributeError):
                _log(f"Invalid week key ignored: {week_key}")
                return (0, 0)

        # Filter valid week keys
        valid_weeks = [week for week in week_keys
                      if pd.notna(week) and isinstance(week, str) and '-W' in str(week)]
        return sorted(valid_weeks, key=parse_week)

    sorted_iso_weeks = sort_iso_weeks(list(all_iso_weeks))

    if not sorted_iso_weeks:
        _log("No valid ISO weeks after filtering")
        return {}

    # Obtain start and end dates for display
    first_week_key = sorted_iso_weeks[0]
    last_week_key = sorted_iso_weeks[-1]

    _log(f"Analysis from {first_week_key} to {last_week_key} ({len(sorted_iso_weeks)} ISO weeks)")

    weekly_conversions = weekly_conversions.reindex(sorted_iso_weeks, fill_value=0)
    weekly_churn = weekly_churn.reindex(sorted_iso_weeks, fill_value=0)

    week_labels = []
    week_dates = []

    for week_key in sorted_iso_weeks:
        try:
            year, week = week_key.split('-W')
            year, week = int(year), int(week)

            # USE STANDARDIZED get_iso_week_bounds FUNCTION
            monday, sunday = get_iso_week_bounds(year, week)

            week_labels.append(f"{monday.strftime('%d-%m-%y')} > {sunday.strftime('%d-%m-%y')}")
            week_dates.append(monday)

        except Exception as e:
            _log(f"Error processing week {week_key}: {e}")
            week_labels.append(week_key)
            week_dates.append(today_date)  # Fallback

    x_pos = range(len(sorted_iso_weeks))

    net_weekly = weekly_conversions - weekly_churn
    net_cumulative = net_weekly.cumsum()

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    ax.bar(x_pos, weekly_conversions, label='Conversions (Trial→Full)', color='green')

    ax.bar(x_pos, -weekly_churn, label='Churn Full Members', color='red')

    ax_twin = ax.twinx()
    ax_twin.plot(x_pos, net_cumulative, color='darkblue', linewidth=1,
                 label='Net Cumulative (Gains - Losses)')

    ax.set_ylabel('Full Members per week\n(Positive: Gains | Negative: Losses)', fontsize=12)
    ax.set_xlabel('Weeks (Monday - Sunday)', fontsize=12)

    for i, (conv, churn) in enumerate(zip(weekly_conversions, weekly_churn)):
        if conv > 0:
            ax.text(i, conv + max(weekly_conversions) * 0.02, str(int(conv)),
                   ha='center', va='bottom', fontsize=7, color='darkgreen')

        if churn > 0:
            ax.text(i, -churn - max(weekly_churn) * 0.02, str(int(churn)),
                   ha='center', va='top', fontsize=7, color='darkred')

    ax_twin.set_ylabel('Net Cumulative Total', fontsize=12)
    ax_twin.tick_params(axis='y', labelcolor='darkblue')

    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax.grid(True, alpha=0.3)

    ax.set_xlim(-0.3, len(x_pos) - 0.5)

    if len(weekly_conversions) > 0 and max(weekly_conversions) > 0:
        y_max = max(weekly_conversions) * 1.2
    else:
        y_max = 1

    if len(weekly_churn) > 0 and max(weekly_churn) > 0:
        y_min = -max(weekly_churn) * 1.2
    else:
        y_min = -1

    ax.set_ylim(y_min, y_max)

    # X-axis configuration - reduce labels for long periods
    step = max(1, len(x_pos) // 10)
    ax.set_xticks(x_pos[::step])
    ax.set_xticklabels([week_labels[i] for i in x_pos[::step]],
                       rotation=45, ha='right', fontsize=9)

    # Calculate immature cutoff week (4 weeks prior)
    immature_year, immature_week, immature_cutoff_key = calculate_target_iso_week(today_iso, weeks_back=0)

    _log(f"Immature cutoff at: {immature_cutoff_key}")

    immature_weeks = []
    for i, week_key in enumerate(sorted_iso_weeks):
        # Compare ISO weeks directly
        if week_key == immature_cutoff_key:
            immature_weeks.append(i)

    if immature_weeks:
        start_idx = min(immature_weeks) - 0.4
        end_idx = max(immature_weeks) + 0.5
        ax.axvspan(start_idx, end_idx, alpha=0.15, color='gray',
                   label='Current week not ended', zorder=0)
        _log(f"Immature period: {len(immature_weeks)} recent weeks")

    start_date = week_dates[0].strftime("%d-%m-%Y") if week_dates else "N/A"
    end_date = week_dates[-1].strftime("%d-%m-%Y") if week_dates else "N/A"
    period_text = f'(from {start_date} to {end_date})'
    ax.set_title(f'WEEKLY FULL MEMBERS FLOW - ALL TIME\n{period_text}',
                 fontsize=18, fontweight='bold', pad=30)

    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax_twin.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=10)

    _log("=== CALCULATING METRICS ===")

    total_conversions = weekly_conversions.sum()
    total_churn = weekly_churn.sum()
    net_growth = total_conversions - total_churn
    final_cumulative = net_cumulative.iloc[-1] if len(net_cumulative) > 0 else 0
    num_weeks = len(sorted_iso_weeks)

    # Additional metrics for consistency
    avg_conversions_per_week = total_conversions / num_weeks if num_weeks > 0 else 0
    avg_churn_per_week = total_churn / num_weeks if num_weeks > 0 else 0
    avg_net_per_week = net_growth / num_weeks if num_weeks > 0 else 0

    max_conv_value = weekly_conversions.max()
    min_conv_value = weekly_conversions.min()
    max_conv_idx = weekly_conversions.idxmax()
    min_conv_idx = weekly_conversions.idxmin()

    max_conv_position = sorted_iso_weeks.index(max_conv_idx)
    min_conv_position = sorted_iso_weeks.index(min_conv_idx)

    max_conv_label = week_labels[max_conv_position]
    min_conv_label = week_labels[min_conv_position]

    max_churn_value = weekly_churn.max()
    min_churn_value = weekly_churn.min()
    max_churn_idx = weekly_churn.idxmax()
    min_churn_idx = weekly_churn.idxmin()

    max_churn_position = sorted_iso_weeks.index(max_churn_idx)
    min_churn_position = sorted_iso_weeks.index(min_churn_idx)

    max_churn_label = week_labels[max_churn_position]
    min_churn_label = week_labels[min_churn_position]

    _log(f"Total conversions (all time): {total_conversions:,}")
    _log(f"Total churn (all time): {total_churn:,}")
    _log(f"Net growth (all time): {net_growth:,}")
    _log(f"Final cumulative: {final_cumulative:,}")

    plt.tight_layout()



    return fig, {
        'total_conversions': total_conversions,
        'total_churn': total_churn,
        'net_growth': net_growth,
        'final_cumulative': final_cumulative,
        'weekly_conversions': weekly_conversions,
        'weekly_churn': weekly_churn,
        'net_cumulative': net_cumulative,
        'iso_weeks': sorted_iso_weeks,
        'week_dates': week_dates,
        'num_weeks': len(sorted_iso_weeks),
        'avg_conversions_per_week': avg_conversions_per_week,
        'avg_churn_per_week': avg_churn_per_week,
        'avg_net_per_week': avg_net_per_week,
        'max_churn_label': max_churn_label,
        'max_churn_value': max_churn_value,
        'min_churn_label': min_churn_label,
        'min_churn_value': min_churn_value,
        'min_conv_value': min_conv_value,
        'min_conv_label': min_conv_label,
        'max_conv_value': max_conv_value,
        'max_conv_label': max_conv_label
    }


def weekly_renewal_flow_8_weeks(sub_df, today_date, today_iso, num_weeks=8):
    """
    Plot weekly renewal metrics for last N weeks using ISO calendar
    FOCUS: Renewals only (Y1→Y2, Y2→Y3) and churn during refund + churn AFTER renewals
    North: Y1→Y2 Renewals + Y2→Y3 Renewals (stacked)
    South: Churn of renewed members only

    """

    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    # Obtain renewal data
    renewal_dict = cus_renewal(sub_df, today_date)

    renewed_to_y2_df = renewal_dict['renewed_to_y2_df']  # Customers who renewed to Y2
    renewed_to_y3_df = renewal_dict['renewed_to_y3_df']  # Customers who renewed to Y3
    customers_in_y2 = renewal_dict['customer_in_y2_df']
    customers_in_y3 = renewal_dict['customer_in_y3_df']

    _log(f"Creating RENEWAL-FOCUSED analysis for last {num_weeks} ISO weeks...")

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

    iso_week_keys = []
    current_year, current_week = today_iso.year, today_iso.week

    for i in range(num_weeks):
        # Add the current week
        iso_week_key = f"{current_year}-W{current_week:02d}"
        iso_week_keys.insert(0, iso_week_key)  # Insert at the beginning for chronological order

        # Move back one ISO week correctly with get_weeks_in_iso_year
        current_week -= 1
        if current_week <= 0:
            current_year -= 1
            current_week = get_weeks_in_iso_year(current_year)

    _log(f"Analyzing ISO weeks: {iso_week_keys[0]} to {iso_week_keys[-1]}")

    _log("Adding ISO week columns...")

    # RENEWALS: Moment they become renewed members (end of refund period)
    y1_to_y2_renewals = add_iso_week_columns(renewed_to_y2_df.copy(), 'refund_period_end_utc')
    y2_to_y3_renewals = add_iso_week_columns(renewed_to_y3_df.copy(), 'refund_period_end_utc')

    # CHURN: Only renewed members who later churned
    # For Y2 renewals that churned
    churn_after_y2_renewal = renewed_to_y2_df[renewed_to_y2_df['canceled_at_utc'].notna()].copy()
    churn_after_y2_renewal = add_iso_week_columns(churn_after_y2_renewal, 'canceled_at_utc')

    # For Y3 renewals that churned
    churn_after_y3_renewal = renewed_to_y3_df[renewed_to_y3_df['canceled_at_utc'].notna()].copy()
    churn_after_y3_renewal = add_iso_week_columns(churn_after_y3_renewal, 'canceled_at_utc')

    # For Y2 churn during refund period
    churn_during_y2_renewal = customers_in_y2[
        (customers_in_y2['canceled_at_utc'].notna()) &
        (customers_in_y2['canceled_during_refund_period'])
    ].copy()
    churn_during_y2_renewal = add_iso_week_columns(churn_during_y2_renewal, 'canceled_at_utc')

    # For Y3 churn during refund period
    churn_during_y3_renewal = customers_in_y3[
        (customers_in_y3['canceled_at_utc'].notna()) &
        (customers_in_y3['canceled_during_refund_period'])
    ].copy()
    churn_during_y3_renewal = add_iso_week_columns(churn_during_y3_renewal, 'canceled_at_utc')

    _log("Calculating renewal metrics...")

    # RENEWALS (gains)
    weekly_renewals_y1_to_y2 = y1_to_y2_renewals[y1_to_y2_renewals['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_renewals_y2_to_y3 = y2_to_y3_renewals[y2_to_y3_renewals['iso_week_key'].notna()].groupby('iso_week_key').size()

    # CHURN post-renewal (losses)
    weekly_churn_post_y2 = churn_after_y2_renewal[churn_after_y2_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_churn_post_y3 = churn_after_y3_renewal[churn_after_y3_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()

    # CHURN during refund period (losses)
    weekly_churn_refund_y2 = churn_during_y2_renewal[churn_during_y2_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_churn_refund_y3 = churn_during_y3_renewal[churn_during_y3_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()

    weekly_renewals_y1_to_y2 = weekly_renewals_y1_to_y2.reindex(iso_week_keys, fill_value=0)
    weekly_renewals_y2_to_y3 = weekly_renewals_y2_to_y3.reindex(iso_week_keys, fill_value=0)
    weekly_churn_post_y2 = weekly_churn_post_y2.reindex(iso_week_keys, fill_value=0)
    weekly_churn_post_y3 = weekly_churn_post_y3.reindex(iso_week_keys, fill_value=0)
    weekly_churn_refund_y2 = weekly_churn_refund_y2.reindex(iso_week_keys, fill_value=0)
    weekly_churn_refund_y3 = weekly_churn_refund_y3.reindex(iso_week_keys, fill_value=0)

    # Combine total churn
    weekly_total_churn_post_renewal = weekly_churn_post_y2 + weekly_churn_post_y3
    weekly_total_churn_refund_renewal = weekly_churn_refund_y2 + weekly_churn_refund_y3

    week_labels = []
    week_dates = []

    for week_key in iso_week_keys:
        try:
            year, week = week_key.split('-W')
            year, week = int(year), int(week)

            # USE STANDARDIZED get_iso_week_bounds FUNCTION
            monday, sunday = get_iso_week_bounds(year, week)

            week_labels.append(f"{monday.strftime('%d-%m-%y')} > {sunday.strftime('%d-%m-%y')}")
            week_dates.append(monday)

        except Exception as e:
            _log(f"Error processing week {week_key}: {e}")
            week_labels.append(week_key)
            week_dates.append(today_date)  # Fallback

    x_pos = range(len(iso_week_keys))

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    bars_pos_1 = ax.bar(x_pos, weekly_renewals_y1_to_y2,
                        label='Renewals Y1→Y2', color='lightgreen', alpha=0.8)
    bars_pos_2 = ax.bar(x_pos, weekly_renewals_y2_to_y3,
                        bottom=weekly_renewals_y1_to_y2,
                        label='Renewals Y2→Y3', color='green', alpha=0.8)

    bars_neg_1 = ax.bar(x_pos, -weekly_total_churn_post_renewal,
                        label='Churn (Post-Renewal)', color='darkred', alpha=0.8)

    bars_neg_2 = ax.bar(x_pos, -weekly_total_churn_refund_renewal,
                        bottom=-weekly_total_churn_post_renewal,  # Stack below
                        label='Churn (During Refund)', color='coral', alpha=0.8)

    ax.set_ylabel('Renewed Members per week\n(Positive: Renewals | Negative: Churn)',
                  fontsize=12, fontweight='bold')
    ax.set_xlabel('Weeks (Monday - Sunday)', fontsize=12, fontweight='bold')

    for i, (ren1, ren2, churn1, churn2) in enumerate(zip(
        weekly_renewals_y1_to_y2, weekly_renewals_y2_to_y3,
        weekly_total_churn_post_renewal, weekly_total_churn_refund_renewal)):

        # Gains (top)
        total_renewals = ren1 + ren2
        if total_renewals > 0:
            # Protection against empty series
            max_positive = max(weekly_renewals_y1_to_y2 + weekly_renewals_y2_to_y3) if len(weekly_renewals_y1_to_y2) > 0 else 1
            ax.text(i, total_renewals + max_positive * 0.02, str(int(total_renewals)),
                   ha='center', va='bottom', fontsize=9, color='darkgreen', fontweight='bold')

        # Losses (bottom) - Total stacked
        total_churn = churn1 + churn2
        if total_churn > 0:
            max_churn = max(weekly_total_churn_post_renewal + weekly_total_churn_refund_renewal) if len(weekly_total_churn_post_renewal) > 0 else 1
            ax.text(i, -(churn1 + churn2) - max_churn * 0.02, str(int(total_churn)),
                   ha='center', va='top', fontsize=9, color='darkred', fontweight='bold')

    ax.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xlim(-0.5, len(x_pos) - 0.5)

    max_positive = max(weekly_renewals_y1_to_y2 + weekly_renewals_y2_to_y3) if len(weekly_renewals_y1_to_y2) > 0 else 1
    max_negative = max(weekly_total_churn_post_renewal + weekly_total_churn_refund_renewal) if len(weekly_total_churn_post_renewal) > 0 else 0

    y_max = max_positive * 1.2
    y_min = -max_negative * 1.2 if max_negative > 0 else -1
    ax.set_ylim(y_min, y_max)

    # X-axis configuration - show all labels for short periods
    ax.set_xticks(x_pos)
    ax.set_xticklabels(week_labels, rotation=45, ha='right', fontsize=9)

    # Calculate immature cutoff week (2 weeks prior for renewals)
    immature_year, immature_week, immature_cutoff_key = calculate_target_iso_week(today_iso, weeks_back=0)

    _log(f"Immature cutoff at: {immature_cutoff_key}")

    immature_weeks = []
    for i, week_key in enumerate(iso_week_keys):
        # Compare ISO weeks directly
        if week_key >= immature_cutoff_key:
            immature_weeks.append(i)

    if immature_weeks:
        start_idx = min(immature_weeks) - 0.4
        end_idx = max(immature_weeks) + 0.5
        ax.axvspan(start_idx, end_idx, alpha=0.2, color='gray',
                   label='Current week not ended', zorder=0)
        _log(f"Immature period: {len(immature_weeks)} recent weeks")

    start_date = week_dates[0].strftime("%d-%m-%Y") if week_dates else "N/A"
    end_date = week_dates[-1].strftime("%d-%m-%Y") if week_dates else "N/A"
    period_text = f'{num_weeks} last ISO weeks (from {start_date} to {end_date})'

    ax.set_title(f'WEEKLY RENEWAL FLOW\nRenewals & Churn (Refund + Post-Renewal)\n{period_text}',
                 fontsize=16, fontweight='bold', pad=20)

    # Legends
    ax.legend(loc='best', fontsize=10)

    _log("\n=== CALCULATING RENEWAL METRICS ===")

    total_y1_to_y2 = weekly_renewals_y1_to_y2.sum()
    total_y2_to_y3 = weekly_renewals_y2_to_y3.sum()
    total_churn_post_renewal = weekly_total_churn_post_renewal.sum()
    total_churn_refund_renewal = weekly_total_churn_refund_renewal.sum()

    # Derived metrics calculations
    total_renewals = total_y1_to_y2 + total_y2_to_y3
    total_churn = total_churn_post_renewal + total_churn_refund_renewal
    net_renewals = total_renewals - total_churn

    # Weekly averages
    avg_renewals_per_week = total_renewals / num_weeks if num_weeks > 0 else 0
    avg_churn_per_week = total_churn / num_weeks if num_weeks > 0 else 0
    avg_refund_per_week = total_churn_refund_renewal / num_weeks if num_weeks > 0 else 0
    avg_post_churn_per_week = total_churn_post_renewal / num_weeks if num_weeks > 0 else 0

    _log(f"Total Y1→Y2 renewals ({num_weeks} weeks): {total_y1_to_y2:,}")
    _log(f"Total Y2→Y3 renewals ({num_weeks} weeks): {total_y2_to_y3:,}")
    _log(f"Total renewals ({num_weeks} weeks): {total_renewals:,}")
    _log(f"Total post-renewal churn ({num_weeks} weeks): {total_churn_post_renewal:,}")
    _log(f"Total refund churn ({num_weeks} weeks): {total_churn_refund_renewal:,}")
    _log(f"Total churn ({num_weeks} weeks): {total_churn:,}")
    _log(f"Net renewal growth ({num_weeks} weeks): {net_renewals:,}")
    _log(f"Avg renewals per week: {avg_renewals_per_week:.1f}")
    _log(f"Avg churn per week: {avg_churn_per_week:.1f}")

    # Churn rate
    churn_rate = 0
    if total_renewals > 0:
        churn_rate = (total_churn / total_renewals * 100)
        _log(f"Renewal churn rate: {churn_rate:.1f}%")

    plt.tight_layout()



    return fig, {
        'renewals_y1_to_y2': total_y1_to_y2,
        'renewals_y2_to_y3': total_y2_to_y3,
        'total_renewals': total_renewals,
        'churn_post_renewal': total_churn_post_renewal,
        'churn_refund_renewal': total_churn_refund_renewal,
        'total_churn': total_churn,
        'net_renewals': net_renewals,
        'churn_rate': churn_rate,
        'num_weeks': num_weeks,
        'avg_renewals_per_week': avg_renewals_per_week,
        'avg_churn_per_week': avg_churn_per_week,
        'weekly_renewals_y1_to_y2': weekly_renewals_y1_to_y2,
        'weekly_renewals_y2_to_y3': weekly_renewals_y2_to_y3,
        'weekly_churn_post_renewal': weekly_total_churn_post_renewal,
        'weekly_churn_refund_renewal': weekly_total_churn_refund_renewal,
        'iso_week_keys': iso_week_keys,
        'week_labels': week_labels,
        'week_dates': week_dates,
        'avg_refund_per_week': avg_refund_per_week,
        'avg_post_churn_per_week': avg_post_churn_per_week
    }


def weekly_renewal_flow_all_time(sub_df, today_date, today_iso):
    """
    Plot weekly renewal metrics for ALL TIME using ISO calendar
    FOCUS: Renewals only (Y1→Y2, Y2→Y3) and churn during refund + churn AFTER renewals
    North: Y1→Y2 Renewals + Y2→Y3 Renewals (stacked)
    South: Churn of renewed members only

    """
    sub_df = sub_df[~sub_df['is_gifted_member']].copy()

    # Obtain renewal data
    renewal_dict = cus_renewal(sub_df, today_date)

    renewed_to_y2_df = renewal_dict['renewed_to_y2_df']  # Customers who renewed to Y2
    renewed_to_y3_df = renewal_dict['renewed_to_y3_df']  # Customers who renewed to Y3
    customers_in_y2 = renewal_dict['customer_in_y2_df']
    customers_in_y3 = renewal_dict['customer_in_y3_df']

    _log("Creating RENEWAL-FOCUSED weekly flow analysis using ISO calendar...")

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

    _log("Adding ISO week columns...")

    # RENEWALS: Moment they become renewed members (end of refund period)
    y1_to_y2_renewals = add_iso_week_columns(renewed_to_y2_df.copy(), 'refund_period_end_utc')
    y2_to_y3_renewals = add_iso_week_columns(renewed_to_y3_df.copy(), 'refund_period_end_utc')

    # CHURN: Only renewed members who later churned
    # For Y2 renewals that churned
    churn_after_y2_renewal = renewed_to_y2_df[renewed_to_y2_df['canceled_at_utc'].notna()].copy()
    churn_after_y2_renewal = add_iso_week_columns(churn_after_y2_renewal, 'canceled_at_utc')

    # For Y3 renewals that churned
    churn_after_y3_renewal = renewed_to_y3_df[renewed_to_y3_df['canceled_at_utc'].notna()].copy()
    churn_after_y3_renewal = add_iso_week_columns(churn_after_y3_renewal, 'canceled_at_utc')

    # For Y2 churn during refund period
    churn_during_y2_renewal = customers_in_y2[
        (customers_in_y2['canceled_at_utc'].notna()) &
        (customers_in_y2['canceled_during_refund_period'])
    ].copy()
    churn_during_y2_renewal = add_iso_week_columns(churn_during_y2_renewal, 'canceled_at_utc')

    # For Y3 churn during refund period
    churn_during_y3_renewal = customers_in_y3[
        (customers_in_y3['canceled_at_utc'].notna()) &
        (customers_in_y3['canceled_during_refund_period'])
    ].copy()
    churn_during_y3_renewal = add_iso_week_columns(churn_during_y3_renewal, 'canceled_at_utc')

    _log("Calculating renewal metrics...")

    # RENEWALS (gains)
    weekly_renewals_y1_to_y2 = y1_to_y2_renewals[y1_to_y2_renewals['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_renewals_y2_to_y3 = y2_to_y3_renewals[y2_to_y3_renewals['iso_week_key'].notna()].groupby('iso_week_key').size()

    # CHURN post-renewal (losses)
    weekly_churn_post_y2 = churn_after_y2_renewal[churn_after_y2_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_churn_post_y3 = churn_after_y3_renewal[churn_after_y3_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()

    # CHURN during refund period (losses)
    weekly_churn_refund_y2 = churn_during_y2_renewal[churn_during_y2_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()
    weekly_churn_refund_y3 = churn_during_y3_renewal[churn_during_y3_renewal['iso_week_key'].notna()].groupby('iso_week_key').size()

    all_iso_weeks = set()

    # Collect all weeks from all series
    for series in [weekly_renewals_y1_to_y2, weekly_renewals_y2_to_y3,
                   weekly_churn_post_y2, weekly_churn_post_y3,
                   weekly_churn_refund_y2, weekly_churn_refund_y3]:
        if len(series) > 0:
            # Filter valid values
            valid_weeks = [week for week in series.index.tolist()
                          if pd.notna(week) and week != '<NA>' and isinstance(week, str)]
            all_iso_weeks.update(valid_weeks)

    if not all_iso_weeks:
        _log("No valid renewal data found")
        return {}

    def sort_iso_weeks(week_keys):
        """Sort ISO week keys by year and week"""
        def parse_week(week_key):
            try:
                if pd.isna(week_key) or week_key == '<NA>' or not isinstance(week_key, str):
                    return (0, 0)
                year, week = week_key.split('-W')
                return (int(year), int(week))
            except (ValueError, AttributeError):
                _log(f"Invalid week key ignored: {week_key}")
                return (0, 0)

        valid_weeks = [week for week in week_keys
                      if pd.notna(week) and week != '<NA>' and isinstance(week, str) and '-W' in str(week)]
        return sorted(valid_weeks, key=parse_week)

    sorted_iso_weeks = sort_iso_weeks(list(all_iso_weeks))

    if not sorted_iso_weeks:
        _log("No valid ISO weeks after filtering")
        return {}

    first_week_key = sorted_iso_weeks[0]
    last_week_key = sorted_iso_weeks[-1]

    _log(f"Renewal analysis from {first_week_key} to {last_week_key} ({len(sorted_iso_weeks)} ISO weeks)")

    weekly_renewals_y1_to_y2 = weekly_renewals_y1_to_y2.reindex(sorted_iso_weeks, fill_value=0)
    weekly_renewals_y2_to_y3 = weekly_renewals_y2_to_y3.reindex(sorted_iso_weeks, fill_value=0)
    weekly_churn_post_y2 = weekly_churn_post_y2.reindex(sorted_iso_weeks, fill_value=0)
    weekly_churn_post_y3 = weekly_churn_post_y3.reindex(sorted_iso_weeks, fill_value=0)
    weekly_churn_refund_y2 = weekly_churn_refund_y2.reindex(sorted_iso_weeks, fill_value=0)
    weekly_churn_refund_y3 = weekly_churn_refund_y3.reindex(sorted_iso_weeks, fill_value=0)

    # Combine total churn
    weekly_total_churn_post_renewal = weekly_churn_post_y2 + weekly_churn_post_y3
    weekly_total_churn_refund_renewal = weekly_churn_refund_y2 + weekly_churn_refund_y3

    week_labels = []
    week_dates = []

    for week_key in sorted_iso_weeks:
        try:
            year, week = week_key.split('-W')
            year, week = int(year), int(week)

            # USE STANDARDIZED get_iso_week_bounds FUNCTION
            monday, sunday = get_iso_week_bounds(year, week)

            week_labels.append(f"{monday.strftime('%d-%m-%y')} > {sunday.strftime('%d-%m-%y')}")
            week_dates.append(monday)

        except Exception as e:
            _log(f"Error processing week {week_key}: {e}")
            week_labels.append(week_key)
            week_dates.append(today_date)  # Fallback

    x_pos = range(len(sorted_iso_weeks))

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    ax.bar(x_pos, weekly_renewals_y1_to_y2, label='Renewals Y1→Y2', color='lightgreen', alpha=0.8)
    ax.bar(x_pos, weekly_renewals_y2_to_y3, bottom=weekly_renewals_y1_to_y2,
           label='Renewals Y2→Y3', color='green', alpha=0.8)

    ax.bar(x_pos, -weekly_total_churn_post_renewal,
           label='Churn (Post-Renewal)', color='coral', alpha=0.8)

    ax.bar(x_pos, -weekly_total_churn_refund_renewal,
           bottom=-weekly_total_churn_post_renewal,
           label='Churn (During Refund)', color='darkred', alpha=0.8)

    ax.set_ylabel('Renewed Members per week\n(Positive: Renewals | Negative: Churn)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Weeks (Monday - Sunday)', fontsize=12, fontweight='bold')

    for i, (ren1, ren2, churn1, churn2) in enumerate(zip(
        weekly_renewals_y1_to_y2, weekly_renewals_y2_to_y3,
        weekly_total_churn_post_renewal, weekly_total_churn_refund_renewal)):

        total_renewals = ren1 + ren2
        if total_renewals > 0:
            # Protection against empty series
            max_positive = max(weekly_renewals_y1_to_y2 + weekly_renewals_y2_to_y3) if len(weekly_renewals_y1_to_y2) > 0 else 1
            ax.text(i, total_renewals + max_positive * 0.02, str(int(total_renewals)),
                   ha='center', va='bottom', fontsize=7, color='darkgreen', fontweight='bold')

        total_churn = churn1 + churn2
        if total_churn > 0:
            # Protection against empty series
            max_negative = max(weekly_total_churn_post_renewal + weekly_total_churn_refund_renewal) if len(weekly_total_churn_post_renewal) > 0 else 1
            ax.text(i, -total_churn - max_negative * 0.02, str(int(total_churn)),
                   ha='center', va='top', fontsize=7, color='darkred', fontweight='bold')

    ax.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xlim(-0.5, len(x_pos) - 0.5)

    max_positive = max(weekly_renewals_y1_to_y2 + weekly_renewals_y2_to_y3) if len(weekly_renewals_y1_to_y2) > 0 else 1
    max_negative = max(weekly_total_churn_post_renewal + weekly_total_churn_refund_renewal) if len(weekly_total_churn_post_renewal) > 0 else 0

    y_max = max_positive * 1.2
    y_min = -max_negative * 1.2 if max_negative > 0 else -1
    ax.set_ylim(y_min, y_max)

    # X-axis configuration - reduce labels for long periods
    step = max(1, len(x_pos) // 10)
    ax.set_xticks(x_pos[::step])
    ax.set_xticklabels([week_labels[i] for i in x_pos[::step]],
                       rotation=45, ha='right', fontsize=9)

    # Calculate immature cutoff week (2 weeks prior for renewals)
    immature_year, immature_week, immature_cutoff_key = calculate_target_iso_week(today_iso, weeks_back=0)

    _log(f"Immature cutoff at: {immature_cutoff_key}")

    immature_weeks = []
    for i, week_key in enumerate(sorted_iso_weeks):
        # Compare ISO weeks directly
        if week_key >= immature_cutoff_key:
            immature_weeks.append(i)

    if immature_weeks:
        start_idx = min(immature_weeks) - 0.4
        end_idx = max(immature_weeks) + 0.5
        ax.axvspan(start_idx, end_idx, alpha=0.15, color='gray',
                   label='Current week not ended', zorder=0)
        _log(f"Immature period: {len(immature_weeks)} recent weeks")

    start_date = week_dates[0].strftime("%d-%m-%Y") if week_dates else "N/A"
    end_date = week_dates[-1].strftime("%d-%m-%Y") if week_dates else "N/A"
    period_text = f'(from {start_date} to {end_date})'
    ax.set_title(f'WEEKLY RENEWAL FLOW - ALL TIME\nRenewals & Churn (Refund + Post-Renewal)\n{period_text}',
                 fontsize=16, fontweight='bold', pad=25)

    # Legends
    lines1, labels1 = ax.get_legend_handles_labels()
    ax.legend(lines1, labels1, loc='upper left', fontsize=10)

    _log("\n=== RENEWAL METRICS SUMMARY ===")

    total_y1_to_y2 = weekly_renewals_y1_to_y2.sum()
    total_y2_to_y3 = weekly_renewals_y2_to_y3.sum()
    total_churn_post_renewal = weekly_total_churn_post_renewal.sum()
    total_churn_refund_renewal = weekly_total_churn_refund_renewal.sum()

    # Derived metrics calculations
    total_renewals = total_y1_to_y2 + total_y2_to_y3
    total_churn = total_churn_post_renewal + total_churn_refund_renewal
    net_renewal_growth = total_renewals - total_churn

    # Weekly averages
    avg_renewals_per_week = total_renewals / len(sorted_iso_weeks) if len(sorted_iso_weeks) > 0 else 0
    avg_churn_per_week = total_churn / len(sorted_iso_weeks) if len(sorted_iso_weeks) > 0 else 0
    avg_refund_per_week = total_churn_refund_renewal / len(sorted_iso_weeks) if len(sorted_iso_weeks) > 0 else 0
    avg_post_churn_per_week = total_churn_post_renewal / len(sorted_iso_weeks) if len(sorted_iso_weeks) > 0 else 0

    _log(f"Total Y1→Y2 renewals: {total_y1_to_y2:,}")
    _log(f"Total Y2→Y3 renewals: {total_y2_to_y3:,}")
    _log(f"Total renewals: {total_renewals:,}")
    _log(f"Total post-renewal churn: {total_churn_post_renewal:,}")
    _log(f"Total refund churn: {total_churn_refund_renewal:,}")
    _log(f"Total churn: {total_churn:,}")
    _log(f"Net renewal growth: {net_renewal_growth:,}")

    # Churn rate
    churn_rate = 0
    if total_renewals > 0:
        churn_rate = (total_churn / total_renewals * 100)
        _log(f"Renewal churn rate: {churn_rate:.1f}%")

    plt.tight_layout()



    return fig, {
        'avg_renewals_per_week': avg_renewals_per_week,
        'avg_churn_per_week': avg_churn_per_week,
        'avg_refund_per_week': avg_refund_per_week,
        'avg_post_churn_per_week': avg_post_churn_per_week,
        'weekly_renewals_y1_to_y2': weekly_renewals_y1_to_y2,
        'weekly_renewals_y2_to_y3': weekly_renewals_y2_to_y3,
        'weekly_churn_post_renewal': weekly_total_churn_post_renewal,
        'weekly_churn_refund_renewal': weekly_total_churn_refund_renewal,
        'total_y1_to_y2': total_y1_to_y2,
        'total_y2_to_y3': total_y2_to_y3,
        'total_renewals': total_renewals,
        'total_churn_post_renewal': total_churn_post_renewal,
        'total_churn_refund_renewal': total_churn_refund_renewal,
        'total_churn': total_churn,
        'net_renewal_growth': net_renewal_growth,
        'churn_rate': churn_rate,
        'iso_weeks': sorted_iso_weeks,
        'week_dates': week_dates,
        'num_weeks': len(sorted_iso_weeks)
    }
__all__ = [
    "calculate_target_iso_week",
    "get_iso_week_bounds",
    "get_weeks_in_iso_year",
    "plot_weekly_trials_8_weeks",
    "plot_weekly_trials_all_time",
    "weekly_flow_8_weeks",
    "weekly_flow_all_time",
    "weekly_renewal_flow_8_weeks",
    "weekly_renewal_flow_all_time",
]
