"""Subscription lifecycle cleaning and membership metrics."""

from .common import *

def preprocess_data(input_df):
    """Clean and preprocess the subscription data"""
    df = input_df.copy()

    # Date conversion
    date_cols = [col for col in df.columns if '(UTC)' in col]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)

    df = df.sort_values(by='Created (UTC)')

    # Column selection and renaming
    columns_to_keep = [
        'id', 'Customer Name', 'Customer ID', 'Status', 'Cancellation Reason',
        'Created (UTC)', 'Start (UTC)', 'Current Period Start (UTC)',
        'Current Period End (UTC)', 'Trial Start (UTC)', 'Trial End (UTC)',
        'Canceled At (UTC)', 'Ended At (UTC)', 'senderShopifyCustomerId (metadata)'
    ]

    df = df[columns_to_keep]

    df.rename(columns={
        'id': 'subscription_id',
        'Customer ID': 'customer_id',
        'Customer Name': 'customer_name',
        'Status': 'status',
        'Cancellation Reason': 'cancellation_reason',
        'Created (UTC)': 'created_utc',
        'Start (UTC)': 'start_utc',
        'Current Period Start (UTC)': 'current_period_start_utc',
        'Current Period End (UTC)': 'current_period_end_utc',
        'Trial Start (UTC)': 'trial_start_utc',
        'Trial End (UTC)': 'trial_end_utc',
        'Canceled At (UTC)': 'canceled_at_utc',
        'Ended At (UTC)': 'ended_at_utc',
        'senderShopifyCustomerId (metadata)': 'is_gifted_member'
    }, inplace=True)

    df['customer_join_key'] = df['customer_name'].apply(normalize_customer_key)

    # Convert is_gifted_member to boolean
    df['is_gifted_member'] = df['is_gifted_member'].notna()
    df['was_gifted_member'] = False


    return df


def remove_multi_subscriptions(df):
    """Remove customers with multiple subscriptions and return a new DataFrame"""
    df = df.copy()

    # Count subscriptions per customer
    subscription_counts = df['customer_id'].value_counts()

    # Get customers with more than one subscription
    multi_sub_customers = subscription_counts[subscription_counts > 1].index.tolist()

    # Filter out these customers from the main DataFrame
    single_sub_df = df[~df['customer_id'].isin(multi_sub_customers)]

    # Create a new DataFrame for multi-subscription customers
    multi_sub_df = df[df['customer_id'].isin(multi_sub_customers)]

    _log(f"Removed {len(multi_sub_customers)} customers with multiple subscriptions.")
    _log(f"Total single_sub_df: {len(single_sub_df)}, with {len(single_sub_df['customer_id'].unique())} unique customers")
    _log(f"Total multi_sub_df: {len(multi_sub_df)}, with {len(multi_sub_df['customer_id'].unique())} unique customers")


    return single_sub_df, multi_sub_df


def remove_high_volume_customers(df, threshold=HIGH_VOLUME_THRESHOLD):
    """Remove customers with more than a specified number of subscriptions"""
    df = df.copy()

    original_count = len(df)

    customer_counts = df['customer_id'].value_counts()
    high_volume_customers = customer_counts[customer_counts > threshold].index

    df = df[~df['customer_id'].isin(high_volume_customers)]

    _log(f'{original_count - len(df)} subscriptions removed from \
{len(high_volume_customers)} customers with more than {threshold} subscriptions')
    _log('***************************************************')

    return df


def clean_inconsistent_statuses(df):
    """
    Fixes inconsistent statuses (active but canceled_at exists)
    """
    df = df.copy()

    # If canceled_at exists AND status='active' → force status='canceled'
    inconsistent_mask = (
        (df['canceled_at_utc'].notna()) &
        (df['status'] == 'active')
    )

    _log(f"Fixing {inconsistent_mask.sum()} inconsistent subscriptions")
    df.loc[inconsistent_mask, 'status'] = 'canceled'

    return df


def custom_multisub_aggregation(df):
    """
    Robust version that handles NaT in date columns
    """

    def safe_get_first_trial_start(group):
        """If multiple trials exist, take the first one - handles NaT"""
        try:
            trial_starts = group['trial_start_utc'].dropna()
            if len(trial_starts) > 0:
                return trial_starts.iloc[0]
            else:
                return pd.NaT
        except (KeyError, IndexError, AttributeError):
            return pd.NaT

    def safe_get_first_trial_end(group):
        """If multiple trials exist, take the first one - handles NaT"""
        try:
            trial_ends = group['trial_end_utc'].dropna()
            if len(trial_ends) > 0:
                return trial_ends.iloc[0]
            else:
                return pd.NaT
        except (KeyError, IndexError, AttributeError):
            return pd.NaT

    def safe_get_smart_canceled_at(group):
        """Smart logic for canceled_at - handles NaT"""
        try:
            group_sorted = group.sort_values('created_utc')

            # If only one subscription
            if len(group_sorted) == 1:
                return group_sorted['canceled_at_utc'].iloc[0]

            # Check for overlaps
            for i in range(len(group_sorted) - 1):
                current_canceled = group_sorted.iloc[i]['canceled_at_utc']
                next_period_start = group_sorted.iloc[i + 1]['current_period_start_utc']

                if pd.notna(current_canceled) and pd.notna(next_period_start):
                    if current_canceled == next_period_start:
                        return group['canceled_at_utc'].max()

            # Check if canceled_at > current_period_start
            for _, row in group_sorted.iterrows():
                canceled_at = row['canceled_at_utc']
                period_start = row['current_period_start_utc']

                if pd.notna(canceled_at) and pd.notna(period_start):
                    if canceled_at > period_start:
                        return canceled_at

            # Otherwise first non-null
            canceled_dates = group['canceled_at_utc'].dropna()
            if len(canceled_dates) > 0:
                return canceled_dates.iloc[0]
            else:
                return pd.NaT

        except (KeyError, IndexError, AttributeError):
            return pd.NaT

    def safe_get_smart_ended_at(group):
        """Smart logic for ended_at - handles NaT"""
        try:
            group_sorted = group.sort_values('created_utc')

            # If only one subscription
            if len(group_sorted) == 1:
                return group_sorted['ended_at_utc'].iloc[0]

            # Check for overlaps
            for i in range(len(group_sorted) - 1):
                current_ended = group_sorted.iloc[i]['ended_at_utc']
                next_period_start = group_sorted.iloc[i + 1]['current_period_start_utc']

                if pd.notna(current_ended) and pd.notna(next_period_start):
                    if current_ended == next_period_start:
                        return group['ended_at_utc'].max()

            # Check if ended_at > current_period_start
            for _, row in group_sorted.iterrows():
                ended_at = row['ended_at_utc']
                period_start = row['current_period_start_utc']

                if pd.notna(ended_at) and pd.notna(period_start):
                    if ended_at > period_start:
                        return ended_at

            # Otherwise first non-null
            ended_dates = group['ended_at_utc'].dropna()
            if len(ended_dates) > 0:
                return ended_dates.iloc[0]
            else:
                return pd.NaT

        except (KeyError, IndexError, AttributeError):
            return pd.NaT

    def safe_was_ever_gifted(group):
        """Check if the customer was ever gifted - handles errors"""
        try:
            return group['is_gifted_member'].any()
        except (KeyError, AttributeError):
            return False

    # Clean inconsistent statuses
    df_clean = clean_inconsistent_statuses(df)

    _log("Aggregating multi-subscription customers...")

    # Aggregation with lambda to avoid pandas errors
    result = df_clean.groupby('customer_id').agg({
        'subscription_id': 'last',
        'customer_name': 'last',
        'status': 'last',
        'cancellation_reason': 'last',
        'created_utc': 'first',
        'current_period_start_utc': 'last',
        'current_period_end_utc': 'last',
        'trial_start_utc': lambda x: safe_get_first_trial_start(x.to_frame().assign(**{col: df_clean.loc[x.index, col] for col in df_clean.columns})),
        'trial_end_utc': lambda x: safe_get_first_trial_end(x.to_frame().assign(**{col: df_clean.loc[x.index, col] for col in df_clean.columns})),
        'canceled_at_utc': lambda x: safe_get_smart_canceled_at(x.to_frame().assign(**{col: df_clean.loc[x.index, col] for col in df_clean.columns})),
        'ended_at_utc': lambda x: safe_get_smart_ended_at(x.to_frame().assign(**{col: df_clean.loc[x.index, col] for col in df_clean.columns})),
        'is_gifted_member': 'last'
    }).reset_index()

    # Add was_gifted_member separately
    try:
        result['was_gifted_member'] = df_clean.groupby('customer_id')['is_gifted_member'].apply(lambda x: x.any()).values
    except:
        result['was_gifted_member'] = False

    # Add start_utc and metadata
    result['customer_join_key'] = result['customer_name'].apply(normalize_customer_key)
    result['start_utc'] = result['created_utc']
    subscription_counts = df_clean.groupby('customer_id').size()
    result['subscription_count'] = result['customer_id'].map(subscription_counts)
    result['is_multi_subscription'] = True

    _log(f"Robust aggregation completed: {len(result)} customers")

    return result


def prepare_multisub_for_integration(multisub_df, sub_df):
    """
    Prepares multisub_df to have the same columns as sub_df
    """

    _log("COLUMN COMPARISON:")
    _log(f"   sub_df: {len(sub_df.columns)} columns")
    _log(f"   multisub_df: {len(multisub_df.columns)} columns")

    # Columns in sub_df but not in multisub
    missing_in_multisub = set(sub_df.columns) - set(multisub_df.columns)

    # Columns in multisub but not in sub_df
    extra_in_multisub = set(multisub_df.columns) - set(sub_df.columns)

    _log(f"\nMISSING COLUMNS in multisub_df: {len(missing_in_multisub)}")
    for col in sorted(missing_in_multisub):
        _log(f"   - {col}")

    _log(f"\nEXTRA COLUMNS in multisub_df: {len(extra_in_multisub)}")
    for col in sorted(extra_in_multisub):
        _log(f"   - {col}")

    # Create a copy for modification
    multisub_prepared = multisub_df.copy()

    _log(f"\nADDING MISSING COLUMNS...")

    for col in missing_in_multisub:
        if 'duration' in col.lower():
            # Duration columns: default to 0
            multisub_prepared[col] = 0
            _log(f"    {col} = 0 (duration)")

        elif col.startswith('canceled_during') or col.startswith('is_') or col.startswith('trial_only'):
            # Boolean columns: default to False
            multisub_prepared[col] = False
            _log(f"    {col} = False (boolean)")

        elif 'refund_period' in col:
            # Refund period columns: calculate or NaT
            multisub_prepared[col] = pd.NaT
            _log(f"    {col} = NaT (date)")

        elif col in ['end_in', 'paid_duration', 'gift_duration']:
            # Specific columns
            multisub_prepared[col] = 0
            _log(f"    {col} = 0 (numeric)")

        else:
            # Other columns: NaN/NaT depending on type
            sample_type = sub_df[col].dtype
            if 'datetime' in str(sample_type):
                multisub_prepared[col] = pd.NaT
                _log(f"    {col} = NaT (datetime)")
            elif 'bool' in str(sample_type):
                multisub_prepared[col] = False
                _log(f"    {col} = False (bool)")
            elif 'int' in str(sample_type) or 'float' in str(sample_type):
                multisub_prepared[col] = 0
                _log(f"    {col} = 0 (numeric)")
            else:
                multisub_prepared[col] = None
                _log(f"    {col} = None (other)")

    _log(f"\nREORGANIZING COLUMNS...")

    # Take all columns from sub_df + extra columns from multisub
    target_columns = list(sub_df.columns) + [col for col in extra_in_multisub]

    # Keep only columns that exist now
    available_columns = [col for col in target_columns if col in multisub_prepared.columns]

    multisub_prepared = multisub_prepared[available_columns]

    _log(f"    Columns reorganized: {len(multisub_prepared.columns)}")

    return multisub_prepared


def integrate_with_subdf(sub_df, multisub_df):
    """
    Intelligently integrates multisub_df with sub_df
    """

    _log("PREPARING INTEGRATION...")

    # Prepare multisub for integration
    multisub_prepared = prepare_multisub_for_integration(multisub_df, sub_df)

    # Add differentiation columns
    sub_df_prepared = sub_df.copy()
    sub_df_prepared['is_multi_subscription'] = False
    sub_df_prepared['subscription_count'] = 1

    # Add was_gifted_member if missing in sub_df
    if 'was_gifted_member' not in sub_df_prepared.columns:
        sub_df_prepared['was_gifted_member'] = sub_df_prepared['is_gifted_member']

    _log(f"\nBEFORE INTEGRATION:")
    _log(f"   sub_df_prepared: {sub_df_prepared.shape}")
    _log(f"   multisub_prepared: {multisub_prepared.shape}")

    # Check that columns match now
    common_columns = set(sub_df_prepared.columns) & set(multisub_prepared.columns)
    _log(f"   Common columns: {len(common_columns)}")

    # Take only common columns for integration
    common_columns_list = sorted(list(common_columns))

    sub_df_final = sub_df_prepared[common_columns_list]
    multisub_final = multisub_prepared[common_columns_list]

    # Concatenate
    combined_df = pd.concat([sub_df_final, multisub_final], ignore_index=True)

    _log(f"\nINTEGRATION COMPLETED:")
    _log(f"   Combined DataFrame: {combined_df.shape}")
    _log(f"   Single-sub customers: {len(sub_df_final)}")
    _log(f"   Multi-sub customers: {len(multisub_final)}")
    _log(f"   Total customers: {len(combined_df)}")
    _log(f"   Total unique customer_ids: {combined_df['customer_id'].nunique()}")

    # Check for duplicates
    duplicated_customers = combined_df['customer_id'].duplicated().sum()
    if duplicated_customers > 0:
        _log(f"     {duplicated_customers} duplicated customer_ids detected!")
    else:
        _log(f"    No customer_id duplicates")

    return combined_df


def cancel_during_trial(df):
    """Check if a member canceled during their trial period"""
    df =df.copy()

    df['canceled_during_trial'] = (
        (df['canceled_at_utc'].notna()) &
        (df['trial_end_utc'] > df['canceled_at_utc'])
    )
    return df


def refund_period_end_utc(df, REFUND_PERIOD_DAYS):
    df = df.copy()
    df['refund_period_end_utc'] = np.where(
        df['trial_start_utc'].notna() &
        (df['trial_end_utc'] > df['current_period_start_utc']),
        df['trial_end_utc'] + pd.Timedelta(days=REFUND_PERIOD_DAYS),
        df['current_period_start_utc'] + pd.Timedelta(days=REFUND_PERIOD_DAYS)
    )
    return df


def canceled_during_refund_period(df):
    """Check if a member canceled during their refund period"""
    df = df.copy()

    df['canceled_during_refund_period'] = (
        (df['canceled_at_utc'].notna()) &
        (df['canceled_during_trial'] == False) &
        (df['refund_period_end_utc'] > df['canceled_at_utc'])
    )
    return df


def full_member_status(df, today_date=None):
    """Determine if a customer is a full member based on business logic"""
    df = df.copy()

    if today_date is None:
        today_date = pd.Timestamp.now(tz='UTC')

    # Full member if:
    # 1. Not canceled during trial
    # 2. Not canceled during refund period
    # 3. Not gifted
    # 4. Trial ended more than 14 days ago (if no trial, current_period_start_utc > 14 days ago)

    no_early_cancellation = (
        (~df['canceled_during_trial']) &
        (~df['canceled_during_refund_period'])
    )

    not_gifted = (~df['is_gifted_member'])

    refund_period_passed = (
            (today_date >= df['refund_period_end_utc'])
            )

    df['is_full_member'] = (
        no_early_cancellation &
        not_gifted &
        refund_period_passed
    )

    return df


def paying_members(df):
    """Determine if a customer is a paying member"""
    df = df.copy()

    # Paying member if:
    # 1. Not canceled
    # 2. Not gifted

    no_early_cancellation = ~df['canceled_during_trial']

    not_gifted = (~df['is_gifted_member'])


    df['is_paying_member'] = (
        no_early_cancellation &
        not_gifted
    )

    return df


def add_ended_at_utc(df, today_date):
    """add ended_at_utc when needed"""
    df = df.copy()

    # if canceled during trial, set ended_at_utc to trial_end_utc
    df['ended_at_utc'] = np.where(
        (df['ended_at_utc'].isna()) & (df['canceled_during_trial']),
        df['trial_end_utc'],
        df['ended_at_utc']
    )

    # if canceled during refund period, set ended_at_utc to canceled_at_utc
    df['ended_at_utc'] = np.where(
        (df['ended_at_utc'].isna()) &
        (df['canceled_during_refund_period']) &
        (~df['canceled_during_trial']),
        df['canceled_at_utc'],
        df['ended_at_utc']
    )

    # if canceled after refund period, set ended_at_utc to current_period_end_utc
    df['ended_at_utc'] = np.where(
        (df['ended_at_utc'].isna()) &
        (df['canceled_at_utc'].notna()) &
        (~df['canceled_during_refund_period']) &
        (~df['canceled_during_trial']),
        np.minimum(df['current_period_end_utc'], today_date),
        df['ended_at_utc']
    )

    # if cancel_at_utc == current_period_start_utc, ended_at_utc = cancel_at_utc
    df['ended_at_utc'] = np.where(
        (df['ended_at_utc'].isna()) &
        (df['canceled_at_utc'].notna()) &
        (df['current_period_start_utc'] == df['canceled_at_utc']),
        df['canceled_at_utc'],
        df['ended_at_utc']
    )

    return df


def calculate_duration(df, today_date):  # ← ADD today_date as parameter
    """Calculate various durations in days with proper business logic"""

    # Trial duration (if trial exists)
    df['trial_duration'] = (df['trial_end_utc'] - df['trial_start_utc']).dt.days.fillna(0)
    # df['trial_duration_planned'] = (df['trial_end_utc'] - df['trial_start_utc']).dt.days.fillna(0)

    # # For cancellations during trial, limit trial_duration to actual usage
    # df['trial_duration'] = np.where(
    #     df['ended_at_utc'] < df['trial_end_utc'],  # Canceled during trial
    #     np.maximum(0, (df['ended_at_utc'] - df['trial_start_utc']).dt.days),  # Actual duration
    #     df['trial_duration_planned']  # Otherwise planned duration
    # )

    # Current period duration
    df['current_period_duration'] = (df['current_period_end_utc'] - df['current_period_start_utc']).dt.days

    # Trial-only subscription
    df['trial_only_subscription'] = (
        df['trial_start_utc'].notna() &
        df['trial_end_utc'].notna() &
        (df['trial_duration'] == df['current_period_duration'])
    )

    # Gift duration (only for gifted members)
    df['gift_duration'] = df['current_period_duration'].where(df['is_gifted_member'], 0)

    # Days until end for active subscriptions
    df['end_in'] = ((df['current_period_end_utc'] - today_date).dt.days).where(df['status'] == 'active', np.nan)


    df['real_duration'] = np.where(
        df['ended_at_utc'].notna(),
        #df['ended_at_utc'].notna() & (df['status'] != 'trialing'),
        (df['ended_at_utc'] - df['created_utc']).dt.days,
        (today_date - df['created_utc']).dt.days
    )


    max_possible = (today_date - df['created_utc'].min()).days
    df['real_duration'] = np.minimum(df['real_duration'], max_possible)

    df['paid_duration'] = df['real_duration'] - df['trial_duration']

    return df


def get_full_members_count(df):
    """Count the number of full members"""
    df = df.copy()

    df = df[df['is_full_member'] == True]
    df_active = df[df['status'] == 'active']
    df_not_active = df[df['status'] != 'active']


    dict_full_members = {'active': len(df_active),
                         'not_active': len(df_not_active),
                         'total': len(df)
                         }

    _log(f"Total Active full member: {dict_full_members['active']}")
    _log(f"Total not active full member: {dict_full_members['not_active']}")
    _log(f"Total full member: {dict_full_members['total']}")


    return dict_full_members


def get_new_trial_last_week(df, today_iso, weeks_back=None):
    results = {}
    df = df[~df['is_gifted_member']].copy()

    df['iso_year'] = df['trial_start_utc'].dt.isocalendar().year
    df['iso_week'] = df['trial_start_utc'].dt.isocalendar().week
    df['iso_week_key'] = df['iso_year'].astype(str) + '-W' + df['iso_week'].astype(str).str.zfill(2)

    target_year, target_week, target_week_key = calculate_target_iso_week(today_iso, weeks_back)
    monday, sunday = get_iso_week_bounds(target_year, target_week)

    target_trials = df[df['iso_week_key'] == target_week_key]
    trials_count = len(target_trials)

    results = {
        'trials_count': trials_count,
        'iso_week_key': target_week_key,
        'monday': monday,
        'sunday': sunday,
        'period_label': f"{monday.strftime('%d-%m-%Y')} > {sunday.strftime('%d-%m-%Y')}"
    }


    return results


def get_conversion_rate_last_weeks(df, today_iso, weeks_back, refund_period_days=REFUND_PERIOD_DAYS):
    results = {}
    df = df[~df['is_gifted_member']].copy()

    target_year, target_week, target_week_key = calculate_target_iso_week(today_iso, weeks_back)
    monday, sunday = get_iso_week_bounds(target_year, target_week)

    new_trials_only = df[df['trial_start_utc'].notna()].copy()

    new_trials_only['expected_maturity_date'] = (new_trials_only['trial_end_utc'] + pd.Timedelta(days=refund_period_days)).copy()

    week_end = sunday + timedelta(days=1)
    week_start_utc = pd.Timestamp(monday).tz_localize('UTC')
    week_end_utc = pd.Timestamp(week_end).tz_localize('UTC')

    mature_trials_this_week = new_trials_only[
        (new_trials_only['expected_maturity_date'] >= week_start_utc) &
        (new_trials_only['expected_maturity_date'] < week_end_utc)
    ].copy()

    total_trials = len(mature_trials_this_week)
    conversions = len(mature_trials_this_week[mature_trials_this_week['is_full_member'] == True]) if total_trials > 0 else 0
    conversion_rate = (conversions / total_trials * 100) if total_trials > 0 else 0.0

    results = {
        'conversion_rate': round(conversion_rate, 2),
        'total_trials': total_trials,
        'conversions': conversions,
        'iso_week_key': target_week_key,
        'week_start': monday,
        'week_end': sunday,
        'monday': monday,
        'sunday': sunday,
        'period': f"{monday.strftime('%d-%m-%Y')} > {sunday.strftime('%d-%m-%Y')}"}

    return results


def get_churn_members_last_week(df, today_iso, weeks_back=1):
    df = df[~df['is_gifted_member']].copy()

    target_year, target_week, target_week_key = calculate_target_iso_week(today_iso, weeks_back)
    week_start, week_end = get_iso_week_bounds(target_year, target_week)

    week_start_utc = pd.Timestamp(week_start).tz_localize('UTC')
    week_end_utc = pd.Timestamp(week_end + timedelta(days=1)).tz_localize('UTC')

    churned_members_mask = (
        (df['canceled_at_utc'] >= week_start_utc) &
        (df['canceled_at_utc'] < week_end_utc) &
        (df['is_full_member'] == True)
    )

    churned_members = df[churned_members_mask].copy()
    count = len(churned_members)

    results = {
        'count': count,
        'iso_week_key': target_week_key,
        'week_start': week_start,
        'week_end': week_end,
        'monday': week_start,
        'sunday': week_end,
        'period': f"{week_start.strftime('%d-%m-%Y')} > {week_end.strftime('%d-%m-%Y')}"
    }

    return results


def cus_renewal(df, today_date=None, refund_period_days=REFUND_PERIOD_DAYS):
    if today_date is None:
        today_date = pd.Timestamp.now(tz='UTC')

    df = df[~df['is_gifted_member']].copy()

    # number of customers who had trial
    all_customers = df

    all_active_full_member = all_customers[(all_customers['is_full_member']) & (all_customers['status'] == 'active')]

    # number of customers who became full members (from trial)
    trial_to_full_member = all_customers[
        (~all_customers['canceled_during_trial']) &
        (all_customers['paid_duration'] > refund_period_days) &
        (all_customers['refund_period_end_utc'] < today_date)]


    # trial > full member conversion rate
    conversion_rate = (len(trial_to_full_member) / len(all_customers) * 100) if len(all_customers) > 0 else 0


    # 1st year customers
    customers_in_y1 = trial_to_full_member[trial_to_full_member['paid_duration'] < 365]

    # active in 1st year
    active_in_y1 = customers_in_y1[customers_in_y1['status'] == 'active']

    # chrun during 1st year
    canceled_during_y1 = customers_in_y1[customers_in_y1['canceled_at_utc'].notna()]

    # cancelation rate during y1
    y1_cancelation_rate = (len(canceled_during_y1) / len(customers_in_y1) * 100) if len(customers_in_y1) > 0 else 0





    # customers eligible to year 2
    eligible_for_y2 = trial_to_full_member[trial_to_full_member['paid_duration'] >= 365]

    # customer currently in year 2
    customers_in_y2 = trial_to_full_member[
        (trial_to_full_member['paid_duration'] >= 365) &
        (trial_to_full_member['paid_duration'] <= 730)
    ]

    # Cancel during refund period y2
    refund_during_y2 = customers_in_y2[(customers_in_y2['canceled_at_utc'].notna()) & (customers_in_y2['paid_duration'] <= (365 + refund_period_days))]

    y2_refund_rate = (len(refund_during_y2) / len(customers_in_y2) * 100) if len(customers_in_y2) > 0 else 0

    # currently active in y2
    active_in_y2 = customers_in_y2[customers_in_y2['status'] == 'active']

    # customer who renewed for a second year
    renewed_to_y2 = eligible_for_y2[eligible_for_y2['paid_duration'] >= (365 + refund_period_days)]

    # customer who canceled in year 2
    canceled_during_y2 = renewed_to_y2[renewed_to_y2['canceled_at_utc'].notna()]

    # renewal rate from y1 to y2
    renewal_rate_y1_to_y2 = (len(renewed_to_y2) / len(eligible_for_y2) * 100) if len(eligible_for_y2) > 0 else 0

    # cancelation rate during y2
    y2_cancelation_rate = (len(canceled_during_y2) / len(renewed_to_y2) * 100) if len(renewed_to_y2) > 0 else 0





    # customers eligible to year 3
    eligible_for_y3 = trial_to_full_member[trial_to_full_member['paid_duration'] > 730]

    # customer currently in year 3
    customers_in_y3 = eligible_for_y3[eligible_for_y3['paid_duration'] <= 1095]

    # currently active in y3
    active_in_y3 = customers_in_y3[customers_in_y3['status'] == 'active']

    # Cancel during refund period y2
    refund_during_y3 = customers_in_y3[(customers_in_y3['canceled_at_utc'].notna()) & (customers_in_y3['paid_duration'] <= (730 + refund_period_days))]
    y3_refund_rate = (len(refund_during_y3) / len(customers_in_y3) * 100) if len(customers_in_y3) > 0 else 0

    # customer who renewed for a second year
    renewed_to_y3 = eligible_for_y3[eligible_for_y3['paid_duration'] >= (730 + refund_period_days)]

    # customer who canceled in year 3
    canceled_during_y3 = renewed_to_y3[renewed_to_y3['canceled_at_utc'].notna()]

    # renewal rate from y2 to y3
    renewal_rate_y2_to_y3 = (len(renewed_to_y3) / len(eligible_for_y3) * 100) if len(eligible_for_y3) > 0 else 0


    # cancelation rate during y3
    y3_cancelation_rate = (len(canceled_during_y3) / len(eligible_for_y3) * 100) if len(eligible_for_y3) > 0 else 0



    renewal_dict = {
        'all_customers_df' : all_customers,
        'all_customer' : len(all_customers),

        'trial_to_full_member_df' : trial_to_full_member,
        'trial_to_full_member' : len(trial_to_full_member),

        'conversion_rate' : round(conversion_rate, 2),

        'all_active_full_member_df' : all_active_full_member,
        'all_active_full_member' : len(all_active_full_member),

        'customers_in_y1_df' : customers_in_y1,
        'customers_in_y1' : len(customers_in_y1),

        'active_in_y1_df' : active_in_y1,
        'active_in_y1' : len(active_in_y1),

        'canceled_during_y1_df' : canceled_during_y1,
        'canceled_during_y1' : len(canceled_during_y1),

        'y1_cancelation_rate' : round(y1_cancelation_rate, 2),

        'eligible_for_y2_df' : eligible_for_y2,
        'eligible_for_y2' : len(eligible_for_y2),

        'customer_in_y2_df' : customers_in_y2,
        'customer_in_y2' : len(customers_in_y2),

        'active_in_y2_df' : active_in_y2,
        'active_in_y2' : len(active_in_y2),

        'renewed_to_y2_df' : renewed_to_y2,
        'renewed_to_y2' : len(renewed_to_y2),

        'canceled_during_y2_df' : canceled_during_y2,
        'canceled_during_y2' : len(canceled_during_y2),

        'refund_during_y2_df' : refund_during_y2,
        'refund_during_y2' : len(refund_during_y2),

        'refund_rate_y2': round(y2_refund_rate, 2),

        'y2_cancelation_rate' : y2_cancelation_rate,
        'renewal_rate_y1_to_y2' : round(renewal_rate_y1_to_y2, 2),

        'eligible_for_y3_df' : eligible_for_y3,
        'eligible_for_y3' : len(eligible_for_y3),

        'customer_in_y3_df' : customers_in_y3,
        'customer_in_y3' : len(customers_in_y3),

        'active_in_y3_df' : active_in_y3,
        'active_in_y3' : len(active_in_y3),

        'refund_during_y3_df': refund_during_y3,
        'refund_during_y3': len(refund_during_y3),

        'refund_rate_y3': round(y3_refund_rate, 2),

        'renewed_to_y3_df' : renewed_to_y3,
        'renewed_to_y3' : len(renewed_to_y3),

        'canceled_during_y3_df' : canceled_during_y3,
        'canceled_during_y3' : len(canceled_during_y3),

        'y3_cancelation_rate' : y3_cancelation_rate,
        'renewal_rate_y2_to_y3' : round(renewal_rate_y2_to_y3, 2)
        }

    return renewal_dict


def get_new_full_members_last_week(df, today_iso, weeks_back, refund_period_days, today_date=None):
    renewal_dict = cus_renewal(df, today_date, refund_period_days)
    trial_to_full_member_df = renewal_dict['trial_to_full_member_df']

    df = trial_to_full_member_df[~trial_to_full_member_df['is_gifted_member']].copy()

    target_year, target_week, target_week_key = calculate_target_iso_week(today_iso, weeks_back)
    week_start, week_end = get_iso_week_bounds(target_year, target_week)

    week_start_utc = pd.Timestamp(week_start).tz_localize('UTC')
    week_end_utc = pd.Timestamp(week_end + timedelta(days=1)).tz_localize('UTC')

    new_full_members_mask = (
        (df['refund_period_end_utc'] >= week_start_utc) &
        (df['refund_period_end_utc'] < week_end_utc)
    )


    new_full_members = df[new_full_members_mask].copy()
    count = len(new_full_members)

    results = {
        'count': count,
        'iso_week_key': target_week_key,
        'week_start': week_start,
        'week_end': week_end,
        'monday': week_start,
        'sunday': week_end,
        'period': f"{week_start.strftime('%d-%m-%Y')} > {week_end.strftime('%d-%m-%Y')}"
    }

    return results
__all__ = [
    "preprocess_data",
    "remove_multi_subscriptions",
    "remove_high_volume_customers",
    "clean_inconsistent_statuses",
    "custom_multisub_aggregation",
    "prepare_multisub_for_integration",
    "integrate_with_subdf",
    "cancel_during_trial",
    "refund_period_end_utc",
    "canceled_during_refund_period",
    "full_member_status",
    "paying_members",
    "add_ended_at_utc",
    "calculate_duration",
    "get_full_members_count",
    "get_new_trial_last_week",
    "get_conversion_rate_last_weeks",
    "get_churn_members_last_week",
    "cus_renewal",
    "get_new_full_members_last_week",
]
