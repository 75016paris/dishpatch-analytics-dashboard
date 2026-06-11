"""Order behaviour and exploratory chart functions."""

from .common import *
from .orders import split_by_full_member_status

def plot_first_order(df):

    # Separate full & not full members
    after_sub_plus7_df_full, after_sub_plus7_df_notfull = split_by_full_member_status(df)


    # Get normalized vendor distributions
    full_counts = after_sub_plus7_df_full['vendor'].value_counts(normalize=True)
    notfull_counts = after_sub_plus7_df_notfull['vendor'].value_counts(normalize=True)

    # Sort vendors by proportion (descending) for full members
    vendors_sorted = full_counts.sort_values(ascending=False).index.tolist()

    # Ensure all vendors are present (even if absent in one group)
    all_vendors = list(vendors_sorted)
    for v in notfull_counts.index:
        if v not in all_vendors:
            all_vendors.append(v)

    # Get values in sorted order and convert to percentage
    full_vals = [full_counts.get(v, 0) * 100 for v in all_vendors]
    notfull_vals = [notfull_counts.get(v, 0) * 100 for v in all_vendors]

    x = range(len(all_vendors))
    width = 0.4



    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))
    # Plot bars for Full Members
    full_bars = ax.bar([i - width/2 for i in x], full_vals, width=width, label='Full Member', color='blue', alpha=0.7)
    # Plot bars for Not Full Members
    notfull_bars = ax.bar([i + width/2 for i in x], notfull_vals, width=width, label='Not Full Member', color='red', alpha=0.7)

    # Add percentage labels above the bars
    for i, bar in enumerate(full_bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.1, f'{full_vals[i]:.1f}%',
                ha='center', va='bottom', fontsize=10, rotation=50, color='blue', alpha=0.7)

    for i, bar in enumerate(notfull_bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.1, f'{notfull_vals[i]:.1f}%',
                ha='center', va='bottom', fontsize=10, rotation=50, color='red', alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels(all_vendors, rotation=90)
    ax.set_xlabel('Vendor')
    ax.set_ylabel('Percentage (%)')
    ax.set_title('FIRST ORDER AFTER SUBSCRIPTION (+7 days) by Vendors')
    ax.legend()

    return fig


def plot_first_order_1(after_sub_7_df):
    # WHAT IS THE FIRST ORDER FOR EACH CUSTOMER AFTER THEY SUBSCRIBE (+7 DAYS).

    # # Select only orders placed after the subscription date, and within 7 days after subscription
    # after_sub_7_df = merged_df[
    #     (merged_df['date'] >= merged_df['created_utc']) &
    #     (merged_df['date'] <= (merged_df['created_utc'] + pd.Timedelta(days=7)))
    # ]


    after_sub_7_df = after_sub_7_df.groupby('customer_name').agg({'vendor': 'first', 'is_full_member': 'first', 'date':'first', 'is_gift':'first', 'have_note':'first'})

    # Get the first order after subscription (+7 days) for each customer
    after_sub_plus7_df = after_sub_7_df.sort_values('date')

    # Separate full & not full members
    after_sub_plus7_df_full = after_sub_7_df[after_sub_7_df['is_full_member'] == True]
    after_sub_plus7_df_notfull = after_sub_7_df[after_sub_7_df['is_full_member'] == False]

    # Get absolute vendor counts
    full_counts = after_sub_plus7_df_full['vendor'].value_counts()
    notfull_counts = after_sub_plus7_df_notfull['vendor'].value_counts()

    # Sort vendors by count (descending) for full members
    vendors_sorted = full_counts.sort_values(ascending=False).index.tolist()

    # Ensure all vendors are present (even if absent in one group)
    all_vendors = list(vendors_sorted)
    for v in notfull_counts.index:
        if v not in all_vendors:
            all_vendors.append(v)

    if not all_vendors:
        return empty_chart('No first-order vendor data found')

    # Get values in sorted order
    full_vals = [full_counts.get(v, 0) for v in all_vendors]
    notfull_vals = [notfull_counts.get(v, 0) for v in all_vendors]

    x = range(len(all_vendors))
    width = 0.4

    fig = plt.figure(figsize=(12, 6))
    # Plot bars for Full Members
    full_bars = plt.bar([i - width/2 for i in x], full_vals, width=width, label='Full Member', color='blue', alpha=0.7)
    # Plot bars for Not Full Members
    notfull_bars = plt.bar([i + width/2 for i in x], notfull_vals, width=width, label='Not Full Member', color='red', alpha=0.7)

    # Add absolute value labels above the bars
    for i, bar in enumerate(full_bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height + 0.1, f'{int(full_vals[i])}',
                ha='center', va='bottom', fontsize=10, rotation=50, color='blue', alpha=0.7 )

    for i, bar in enumerate(notfull_bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2 + 0.1, height + 0.1, f'{int(notfull_vals[i])}',
                ha='center', va='bottom', fontsize=10, rotation=50, color='red', alpha=0.7)

    plt.xticks(x, all_vendors, rotation=90)
    plt.xlabel('Vendor')
    plt.ylabel('Count')
    plt.title('WHERE CUSTOMERS ORDER THEIR FIRST ITEMS AFTER THEIR SUBSCRIPTION (+7 Days) \n distribution by Vendors (Full Member vs Trial)')
    plt.legend()
    plt.tight_layout()

    return fig


def plot_first_order_2(after_sub_7_df):
    # WHAT IS THE FIRST ORDER FOR EACH CUSTOMER AFTER THEY SUBSCRIBE (+7 DAYS).

    # # Select only orders placed after the subscription date, and within 7 days after subscription
    # after_sub_7_df = merged_df[
    #     (merged_df['date'] >= merged_df['created_utc']) &
    #     (merged_df['date'] <= (merged_df['created_utc'] + pd.Timedelta(days=7)))
    # ]

    after_sub_7_df = after_sub_7_df.groupby('customer_name').agg({'vendor': 'first', 'is_full_member': 'first', 'date':'first', 'is_gift':'first', 'have_note':'first'})

    # Get the first order after subscription (+7 days) for each customer
    after_sub_plus7_df = after_sub_7_df.sort_values('date')

    # Separate full & not full members
    after_sub_plus7_df_full = after_sub_7_df[after_sub_7_df['is_full_member'] == True]
    after_sub_plus7_df_notfull = after_sub_7_df[after_sub_7_df['is_full_member'] == False]

    # Get absolute vendor counts
    full_counts = after_sub_plus7_df_full['vendor'].value_counts()
    notfull_counts = after_sub_plus7_df_notfull['vendor'].value_counts()

    # Combine counts to get totals per vendor
    all_vendors = set(full_counts.index).union(set(notfull_counts.index))
    totals = {v: full_counts.get(v, 0) + notfull_counts.get(v, 0) for v in all_vendors}

    # Sort vendors by total count descending
    vendors_sorted = sorted(totals, key=totals.get, reverse=True)

    if not vendors_sorted:
        return empty_chart('No first-order vendor data found')

    # Get values
    full_vals = [full_counts.get(v, 0) for v in vendors_sorted]
    notfull_vals = [notfull_counts.get(v, 0) for v in vendors_sorted]
    total_vals = [totals.get(v, 0) for v in vendors_sorted]

    # Calculate percentages per vendor
    full_percents = [ (full_vals[i] / total_vals[i] * 100) if total_vals[i] > 0 else 0 for i in range(len(vendors_sorted)) ]
    notfull_percents = [ (notfull_vals[i] / total_vals[i] * 100) if total_vals[i] > 0 else 0 for i in range(len(vendors_sorted)) ]

    x = range(len(vendors_sorted))
    width = 0.8  # Wider bars for stacked

    fig = plt.figure(figsize=(12, 6))

    # Plot stacked bars: Full Members at bottom, Not Full on top
    full_bars = plt.bar(x, full_vals, width=width, label='Full Member', color='blue', alpha=0.7)
    notfull_bars = plt.bar(x, notfull_vals, width=width, bottom=full_vals, label='Not Full Member', color='red', alpha=0.7)

    # Add labels with count and percentage inside the bars
    for i, height in enumerate(full_vals):
        if height > 0:
            label = f"{int(height)}\n{full_percents[i]:.1f}%"
            plt.text(x[i], full_vals[i]/2, label, ha='center', va='center', fontsize=9, color='white', fontweight='bold')

    for i, height in enumerate(notfull_vals):
        if height > 0:
            label = f"{int(height)}\n{notfull_percents[i]:.1f}%"
            plt.text(x[i], full_vals[i] + notfull_vals[i]/2, label, ha='center', va='center', fontsize=9, color='white', fontweight='bold')

    plt.xticks(x, vendors_sorted, rotation=90)
    plt.xlabel('Vendor')
    plt.ylabel('Count')
    plt.title('WHERE CUSTOMERS ORDER THEIR FIRST ITEMS AFTER THEIR SUBSCRIPTION (+7 Days) \n Stacked Distribution by Vendors (Full Member vs Trial) with Percentage Split')
    plt.legend()
    plt.tight_layout()

    return fig


def plot_first_order_3(after_sub_7_df):
    # WHAT IS THE FIRST ORDER FOR EACH CUSTOMER AFTER THEY SUBSCRIBE (+7 DAYS).

    # # Select only orders placed after the subscription date, and within 7 days after subscription
    # after_sub_7_df = merged_df[
    #     (merged_df['date'] >= merged_df['created_utc']) &
    #     (merged_df['date'] <= (merged_df['created_utc'] + pd.Timedelta(days=7)))
    # ]

    after_sub_7_df = after_sub_7_df.groupby('customer_name').agg({'vendor': 'first', 'is_full_member': 'first', 'date':'first', 'is_gift':'first', 'have_note':'first'})

    # Get the first order after subscription (+7 days) for each customer
    after_sub_plus7_df = after_sub_7_df.sort_values('date')

    # Separate full & not full members
    after_sub_plus7_df_full = after_sub_7_df[after_sub_7_df['is_full_member'] == True]
    after_sub_plus7_df_notfull = after_sub_7_df[after_sub_7_df['is_full_member'] == False]

    # Get absolute vendor counts
    full_counts = after_sub_plus7_df_full['vendor'].value_counts()
    notfull_counts = after_sub_plus7_df_notfull['vendor'].value_counts()

    # Combine counts to get totals per vendor
    all_vendors = set(full_counts.index).union(set(notfull_counts.index))
    totals = {v: full_counts.get(v, 0) + notfull_counts.get(v, 0) for v in all_vendors}

    # Sort vendors by total count descending and keep only top 10
    vendors_sorted = sorted(totals, key=totals.get, reverse=True)[:10]

    if not vendors_sorted:
        return empty_chart('No first-order vendor data found')

    # Get values for top 10
    full_vals = [full_counts.get(v, 0) for v in vendors_sorted]
    notfull_vals = [notfull_counts.get(v, 0) for v in vendors_sorted]
    total_vals = [totals.get(v, 0) for v in vendors_sorted]

    # Calculate percentages per vendor
    full_percents = [ (full_vals[i] / total_vals[i] * 100) if total_vals[i] > 0 else 0 for i in range(len(vendors_sorted)) ]
    notfull_percents = [ (notfull_vals[i] / total_vals[i] * 100) if total_vals[i] > 0 else 0 for i in range(len(vendors_sorted)) ]

    # Calculate widths proportional to total_vals
    total_sum = sum(total_vals)
    if total_sum == 0:
        total_sum = 1  # Avoid division by zero
    widths = [val / total_sum * 100 for val in total_vals]  # Scale to 100 for easier positioning

    # Calculate cumulative positions for bar starts
    positions = [0]
    for w in widths[:-1]:
        positions.append(positions[-1] + w)

    fig = plt.figure(figsize=(12, 6))

    # Plot stacked bars with variable widths
    for i in range(len(vendors_sorted)):
        # Full Member segment
        full_bar = plt.bar(positions[i], full_percents[i], width=widths[i], bottom=0, color='blue', alpha=0.7, label='Full Member' if i == 0 else None, align='edge', edgecolor='white', linewidth=1)

        # Not Full Member segment
        notfull_bar = plt.bar(positions[i], notfull_percents[i], width=widths[i], bottom=full_percents[i], color='red', alpha=0.7, label='Not Full Member' if i == 0 else None, align='edge', edgecolor='white', linewidth=1)

        # Add labels with count and percentage inside the segments
        if full_vals[i] > 0:
            label = f"{int(full_vals[i])}\n{full_percents[i]:.1f}%"
            plt.text(positions[i] + widths[i]/2, full_percents[i]/2, label, ha='center', va='center', fontsize=9, color='white', fontweight='bold')

        if notfull_vals[i] > 0:
            label = f"{int(notfull_vals[i])}\n{notfull_percents[i]:.1f}%"
            plt.text(positions[i] + widths[i]/2, full_percents[i] + notfull_percents[i]/2, label, ha='center', va='center', fontsize=9, color='white', fontweight='bold')

        # Add total count above the bar
        plt.text(positions[i] + widths[i]/2, 100 + 1, f"Total: {int(total_vals[i])}", ha='center', va='bottom', fontsize=9)

    # Set x-ticks at the center of each bar
    tick_positions = [positions[i] + widths[i]/2 for i in range(len(vendors_sorted))]
    plt.xticks(tick_positions, vendors_sorted, rotation=65, ha='right', fontsize=9)

    plt.xlabel('Vendor')
    plt.ylabel('Percentage')
    plt.ylim(0, 110)  # Extra space for total labels
    plt.title('WHERE CUSTOMERS ORDER THEIR FIRST ITEMS AFTER THEIR SUBSCRIPTION (+7 Days) \n Mekko Chart: Distribution by TOP 10 Vendors')
    plt.legend()
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])

    return fig


def plot_first_order_4(after_sub_7_df):
    # WHAT IS THE FIRST ORDER FOR EACH CUSTOMER AFTER THEY SUBSCRIBE (+7 DAYS).

    # # Select only orders placed after the subscription date, and within 7 days after subscription
    # after_sub_7_df = merged_df[
    #     (merged_df['date'] >= merged_df['created_utc']) &
    #     (merged_df['date'] <= (merged_df['created_utc'] + pd.Timedelta(days=7)))
    # ]

    after_sub_7_df = after_sub_7_df.groupby('customer_name').agg({'vendor': 'first', 'is_full_member': 'first', 'date':'first', 'is_gift':'first', 'have_note':'first'})

    # Get the first order after subscription (+7 days) for each customer
    after_sub_plus7_df = after_sub_7_df.sort_values('date')

    # Separate full & not full members
    after_sub_plus7_df_full = after_sub_7_df[after_sub_7_df['is_full_member'] == True]
    after_sub_plus7_df_notfull = after_sub_7_df[after_sub_7_df['is_full_member'] == False]

    # Get absolute vendor counts
    full_counts = after_sub_plus7_df_full['vendor'].value_counts()
    notfull_counts = after_sub_plus7_df_notfull['vendor'].value_counts()

    # Combine counts to get totals per vendor
    all_vendors = set(full_counts.index).union(set(notfull_counts.index))
    totals = {v: full_counts.get(v, 0) + notfull_counts.get(v, 0) for v in all_vendors}

    # Sort vendors by total count descending and show vendors outside the top 10
    vendors_sorted = sorted(totals, key=totals.get, reverse=True)[10:]

    if not vendors_sorted:
        return empty_chart('No long-tail first-order vendor data found')

    # Get values for long-tail vendors
    full_vals = [full_counts.get(v, 0) for v in vendors_sorted]
    notfull_vals = [notfull_counts.get(v, 0) for v in vendors_sorted]
    total_vals = [totals.get(v, 0) for v in vendors_sorted]

    # Calculate percentages per vendor
    full_percents = [ (full_vals[i] / total_vals[i] * 100) if total_vals[i] > 0 else 0 for i in range(len(vendors_sorted)) ]
    notfull_percents = [ (notfull_vals[i] / total_vals[i] * 100) if total_vals[i] > 0 else 0 for i in range(len(vendors_sorted)) ]

    # Calculate widths proportional to total_vals
    total_sum = sum(total_vals)
    if total_sum == 0:
        total_sum = 1  # Avoid division by zero
    widths = [val / total_sum * 100 for val in total_vals]  # Scale to 100 for easier positioning

    # Calculate cumulative positions for bar starts
    positions = [0]
    for w in widths[:-1]:
        positions.append(positions[-1] + w)

    fig = plt.figure(figsize=(12, 6))

    # Plot stacked bars with variable widths
    for i in range(len(vendors_sorted)):
        # Full Member segment
        full_bar = plt.bar(positions[i], full_percents[i], width=widths[i], bottom=0, color='blue', alpha=0.7, label='Full Member' if i == 0 else None, align='edge', edgecolor='white', linewidth=1)

        # Not Full Member segment
        notfull_bar = plt.bar(positions[i], notfull_percents[i], width=widths[i], bottom=full_percents[i], color='red', alpha=0.7, label='Not Full Member' if i == 0 else None, align='edge', edgecolor='white', linewidth=1)

        # Add labels with count and percentage inside the segments
        if full_vals[i] > 0:
            label = f"{int(full_vals[i])}\n{full_percents[i]:.1f}%"
            plt.text(positions[i] + widths[i]/2, full_percents[i]/2, label, ha='center', va='center', fontsize=9, color='white', fontweight='bold')

        if notfull_vals[i] > 0:
            label = f"{int(notfull_vals[i])}\n{notfull_percents[i]:.1f}%"
            plt.text(positions[i] + widths[i]/2, full_percents[i] + notfull_percents[i]/2, label, ha='center', va='center', fontsize=9, color='white', fontweight='bold')

        # Add total count above the bar
        plt.text(positions[i] + widths[i]/2, 100 + 1, f"Total: {int(total_vals[i])}", ha='center', va='bottom', fontsize=9)

    # Set x-ticks at the center of each bar
    tick_positions = [positions[i] + widths[i]/2 for i in range(len(vendors_sorted))]
    plt.xticks(tick_positions, vendors_sorted, rotation=45, ha='right')

    plt.xlabel('Vendor')
    plt.ylabel('Percentage')
    plt.ylim(0, 110)  # Extra space for total labels
    plt.title('WHERE CUSTOMERS ORDER THEIR FIRST ITEMS AFTER THEIR SUBSCRIPTION (+7 Days) \n Mekko Chart: Distribution by Vendors')
    plt.legend()
    plt.tight_layout()

    return fig


def discount_vendor(merged_df):
    NB_OF_DISCOUNT_VOUCHER = 4

    # Filter for trial members
    notfull_discount_df = merged_df[merged_df['is_full_member'] == False]

    # Sort by customer and date to ensure chronological order
    notfull_discount_df = notfull_discount_df.sort_values(by=['customer_name', 'date'])

    # Take the first N orders per customer
    notfull_discount_df = notfull_discount_df.groupby('customer_name').head(NB_OF_DISCOUNT_VOUCHER)

    # Count vendor appearances across all first N orders
    vendor_counts = notfull_discount_df['vendor'].value_counts()
    vendor_proportions = notfull_discount_df['vendor'].value_counts(normalize=True) * 100

    if vendor_counts.empty:
        return empty_chart(f'No trial-member orders found in the first {NB_OF_DISCOUNT_VOUCHER} orders')

    # Plot bar chart and annotate bars with counts
    fig, ax = plt.subplots(figsize=(12, 6))
    vendor_counts.head(12).plot.bar(color='red', alpha=0.7, ax=ax)
    ax.tick_params(axis='x', rotation=65, labelsize=9)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment('right')
    plt.xlabel('Vendor')
    plt.ylabel('Count')
    plt.title(f'Vendor Counts in First {NB_OF_DISCOUNT_VOUCHER} Orders (Trial Members)')

    for i, bar in enumerate(ax.patches):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.1,
            f'{int(height)}',
            ha='center',
            va='bottom',
            fontsize=10,
            color='red',
            alpha=0.7,
            rotation=30
        )

    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    return fig


def plot_how_many_days_after_sub(df):
    # df['days_since_subscription'] = (df['date'] - df['created_utc']).dt.days
    df['days_since_subscription'] = df.apply(
        lambda row: (row['date'] - row['created_utc']).days
        if pd.notnull(row['date']) and pd.notnull(row['created_utc'])
        else None,
        axis=1
    )

    # Filter for orders within 0 to 7 days after subscription
    days_since_subscription_df = df[(df['days_since_subscription'] <= 7) & (df['days_since_subscription'] >= 0)]

    # Get the first days_since_subscription for each customer
    # #### 'days_since_subscription': 'min' OR 'first' ?? ####
    days_since_subscription_df = days_since_subscription_df.groupby('customer_name').agg({'days_since_subscription': 'min', 'is_full_member':'first'})

    # Calculate the frequency and normalize to percentages
    counts = days_since_subscription_df['days_since_subscription'].value_counts(normalize=True).sort_index() * 100

    if counts.empty:
        return empty_chart('No orders found within 0–7 days after subscription')

    # Plot the bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    counts.plot.bar(ax=ax)

    # Add percentage labels above the bars
    for i, bar in enumerate(ax.patches):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.1,
            f'{counts.iloc[i]:.1f}%',
            ha='center',
            va='bottom',
            fontsize=10,
        )

    plt.xlabel('Days Since Subscription')
    plt.xticks(rotation=0)
    plt.ylabel('Percentage of Customers (%)')
    plt.title('How many days before first order after subscription')
    #plt.show()
    return fig


def plot_gift_and_not(df, sub_df):
    first_order_full_df_gift, first_order_notfull_df_gift = split_by_full_member_status(df)

    # Get value counts for first orders
    is_gift_first = df['is_gift'].value_counts()
    have_note_first = df['have_note'].value_counts()

    is_gift_full_first = first_order_full_df_gift['is_gift'].value_counts()
    is_gift_notfull_first = first_order_notfull_df_gift['is_gift'].value_counts()

    have_note_full_first = first_order_full_df_gift['have_note'].value_counts()
    have_note_notfull_first = first_order_notfull_df_gift['have_note'].value_counts()

    groups = ['Is Gift? (First Orders)', 'Have Note? (First Orders)']

    # Convert value counts to lists, handling missing True/False
    # is_gift_first_list = [is_gift_first.get(False, 0), is_gift_first.get(True, 0)]
    is_gift_full_first_list = [is_gift_full_first.get(False, 0), is_gift_full_first.get(True, 0)]
    is_gift_notfull_first_list = [is_gift_notfull_first.get(False, 0), is_gift_notfull_first.get(True, 0)]

    # have_note_first_list = [have_note_first.get(False, 0), have_note_first.get(True, 0)]
    have_note_full_first_list = [have_note_full_first.get(False, 0), have_note_full_first.get(True, 0)]
    have_note_notfull_first_list = [have_note_notfull_first.get(False, 0), have_note_notfull_first.get(True, 0)]

    # Calculate percentages for full and not-full members
    full_member_percs = [
        is_gift_full_first_list[1] / (is_gift_full_first_list[1] + is_gift_full_first_list[0]) * 100 if (is_gift_full_first_list[1] + is_gift_full_first_list[0]) > 0 else 0,
        have_note_full_first_list[1] / (have_note_full_first_list[1] + have_note_full_first_list[0]) * 100 if (have_note_full_first_list[1] + have_note_full_first_list[0]) > 0 else 0
    ]
    notfull_member_percs = [
        is_gift_notfull_first_list[1] / (is_gift_notfull_first_list[1] + is_gift_notfull_first_list[0]) * 100 if (is_gift_notfull_first_list[1] + is_gift_notfull_first_list[0]) > 0 else 0,
        have_note_notfull_first_list[1] / (have_note_notfull_first_list[1] + have_note_notfull_first_list[0]) * 100 if (have_note_notfull_first_list[1] + have_note_notfull_first_list[0]) > 0 else 0
    ]

    # Raw counts for True values
    full_member_counts = [is_gift_full_first_list[1], have_note_full_first_list[1]]
    notfull_member_counts = [is_gift_notfull_first_list[1], have_note_notfull_first_list[1]]

    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 8), gridspec_kw={'width_ratios': [2, 1]})

    # Left Plot: Gift and Note Distribution
    x = np.arange(len(groups))
    width = 0.35

    # Plot bars side by side
    bars1 = ax1.bar(x - width/2, full_member_percs, width, color='blue', alpha=0.7, label='Full Member')
    bars2 = ax1.bar(x + width/2, notfull_member_percs, width, color='red', alpha=0.7, label='Not Full Member')

    # Add percentage labels above bars
    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height, f'{full_member_percs[i]:.1f}%',
                ha='center', va='bottom', fontsize=10)

    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height, f'{notfull_member_percs[i]:.1f}%',
                ha='center', va='bottom', fontsize=10)

    # Add raw counts inside bars
    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height/2, f'{int(full_member_counts[i])}',
                ha='center', va='center', fontsize=10, color='white', weight='bold')

    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height/2, f'{int(notfull_member_counts[i])}',
                ha='center', va='center', fontsize=10, color='white', weight='bold')

    # Add conversion rates inside/above bars
    for i, bar in enumerate(bars1):
        total = full_member_counts[i] + notfull_member_counts[i]
        conv_rate = full_member_counts[i] / total * 100 if total > 0 else 0
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{conv_rate:.1f}%', ha='center', va='bottom', fontsize=9, color='blue')

    for i, bar in enumerate(bars2):
        total = full_member_counts[i] + notfull_member_counts[i]
        conv_rate = notfull_member_counts[i] / total * 100 if total > 0 else 0
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{conv_rate:.1f}%', ha='center', va='bottom', fontsize=9, color='red')

    # Customize the left plot
    ax1.set_title('Distribution of Gift and Note (First Orders)')
    total_first_orders = sum(is_gift_full_first_list) + sum(is_gift_notfull_first_list)
    ax1.set_xlabel(f'First Orders: {total_first_orders}')
    ax1.set_ylabel('% of Orders')
    ax1.set_xticks(x)
    ax1.set_xticklabels(groups, rotation=0, ha='center')
    ax1.legend()
    ax1.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax1.set_ylim(0, 8)  # Set y-axis limit


    # Right Plot: Full vs Not-Full Member Distribution
    full_or_not = sub_df.groupby('customer_name').agg({'is_full_member': 'any'})
    member_counts = full_or_not['is_full_member'].value_counts(normalize=True) * 100
    member_counts = member_counts.reindex([True, False], fill_value=0)  # Ensure both True/False are present


    # x2 = np.arange(2)
    # bars = ax2.bar(x2, [member_counts[True], member_counts[False]],
    #             width=0.35, color=['blue', 'red'], alpha=0.7)

    # for i, bar in enumerate(bars):
    #     height = bar.get_height()
    #     ax2.text(bar.get_x() + bar.get_width()/2, height + 0.1, f'{height:.1f}%',
    #             ha='center', va='bottom', fontsize=10)

    #     raw_count = int(height / 100 * len(full_or_not))
    #     ax2.text(bar.get_x() + bar.get_width()/2, height / 2, f'{raw_count}',
    #             ha='center', va='center', fontsize=10, color='white', weight='bold')

    x2 = np.arange(2)
    bars = ax2.bar(x2 - 0.25, [member_counts[True], member_counts[False]],
                   width=0.5, color=['blue', 'red'], alpha=0.7)

    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height + 0.1, f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10)

        raw_count = int(height / 100 * len(full_or_not))
        ax2.text(bar.get_x() + bar.get_width()/2, height / 2, f'{raw_count}',
                ha='center', va='center', fontsize=10, color='white', weight='bold')


    # Customize the right plot
    ax2.set_title('Conversion rate')
    ax2.set_xlabel(f'Total Customers: {len(full_or_not)}')
    ax2.set_ylabel('% of Customers')
    ax2.set_xticks(x2)
    ax2.set_xticklabels(['Full Member', 'Not Full Member'], rotation=0, ha='center')
    ax2.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax2.set_ylim(0, 80)  # Set y-axis limit

    # Adjust layout to prevent overlap
    plt.tight_layout()
    #plt.show()
    return fig


def plot_price_distribution(df):
    df = df[df['items_price'].notna()].copy()
    if df.empty:
        return empty_chart('No priced order data available')

    first_value = df[
        (df['date'] >= df['created_utc']) &
        (df['date'] <= (df['created_utc'] + pd.Timedelta(days=7)))]


    first_value = first_value.groupby('cmd').agg({'items_price': 'sum', 'customer_name': 'first', 'is_full_member': 'first', 'date': 'first'})

    if first_value.empty:
        return empty_chart('No first-order price data found within 0–7 days after subscription')

    first_value = first_value.sort_values('date')

    def price_category(x):
        if x < 90:
            return '<90£'
        elif x < 180:
            return '>=90£ & <=180£'
        else:
            return '>180£'

    first_value['order_values'] = first_value['items_price'].apply(price_category)

    first_value = first_value.groupby('customer_name').agg({'is_full_member': 'first', 'items_price': 'first', 'order_values': 'first'})

    first_value_full = first_value[first_value['is_full_member'] == True]
    order_counts_full = first_value_full['order_values'].value_counts()

    first_value_notfull = first_value[first_value['is_full_member'] == False]
    order_counts_notfull = first_value_notfull['order_values'].value_counts()




    order_counts_full = first_value_full['order_values'].value_counts()
    order_counts_notfull = first_value_notfull['order_values'].value_counts()

    # Ensure both have the same index (categories: 'small', 'med', 'big')
    categories = ['<90£', '>=90£ & <=180£', '>180£']
    order_counts_full = order_counts_full.reindex(categories, fill_value=0)
    order_counts_notfull = order_counts_notfull.reindex(categories, fill_value=0)

    # Set up bar positions
    x = np.arange(len(categories))  # [0, 1, 2]
    width = 0.35  # Width of each bar

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot bars
    bars_full = ax.bar(x - width/2, order_counts_full, width, color='blue', alpha=0.7, label='Full Member')
    bars_notfull = ax.bar(x + width/2, order_counts_notfull, width, color='red', alpha=0.7, label='Not Full Member')

    # Total counts (for percentage calculation)
    total_full = order_counts_full.sum()
    total_notfull = order_counts_notfull.sum()

    # Add absolute values inside bars and percentages above
    for i, bar in enumerate(bars_full):
        height = bar.get_height()
        # Absolute value (inside bar)
        ax.text(bar.get_x() + bar.get_width()/2, height / 2,
                f'{int(height)}', ha='center', va='center',
                fontsize=10, color='white', weight='bold')
        # Percentage (above bar)
        perc = (height / total_full * 100) if total_full > 0 else 0
        ax.text(bar.get_x() + bar.get_width()/2, height + 1,
                f'{perc:.1f}%', ha='center', va='bottom',
                fontsize=10, color='blue')

    for i, bar in enumerate(bars_notfull):
        height = bar.get_height()
        # Absolute value (inside bar)
        ax.text(bar.get_x() + bar.get_width()/2, height / 2,
                f'{int(height)}', ha='center', va='center',
                fontsize=10, color='white', weight='bold')
        # Percentage (above bar)
        perc = (height / total_notfull * 100) if total_notfull > 0 else 0
        ax.text(bar.get_x() + bar.get_width()/2, height + 1,
                f'{perc:.1f}%', ha='center', va='bottom',
                fontsize=10, color='red')

    # Customize plot
    ax.set_title("Distribution orders by price category (first order after subscription + 7days)")
    ax.set_ylabel("Number of Orders")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()


    #plt.show()
    return fig


def plot_simple_and_complex_order(merged_df):
    if merged_df.empty:
        return empty_chart('No order complexity data found')

    # Utiliser set pour obtenir les valeurs uniques dans les listes
    agg_df = merged_df.groupby('cmd').agg({
        'delivery_date': lambda x: list(set(x)),
        'vendor': lambda x: list(set(x))
    })
    agg_df['delivery_date_nb'] = agg_df['delivery_date'].apply(lambda x: len(x))
    agg_df['delivery_date_complex'] = agg_df['delivery_date_nb'] > 1
    agg_df['vendor_nb'] = agg_df['vendor'].apply(lambda x: len(x))
    agg_df['vendor_complex'] = agg_df['vendor_nb'] > 1
    agg_df['total_nb'] = agg_df['delivery_date_nb'] + agg_df['vendor_nb']
    agg_df['complex'] = agg_df['total_nb'] > 2
    agg_df['double_complex'] = agg_df['delivery_date_complex'] & agg_df['vendor_complex']
    agg_df

    # Fix: axes from plt.subplots(2, 2, ...) is a 2D numpy array, not a flat list.
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))

    # Flatten axes for easy indexing
    axes_flat = axes.flatten()

    # Helper to ensure correct label order for value_counts
    def plot_pie(series, ax, title, colors):
        # Ensure 'Simple' is False, 'Complex' is True
        counts = series.value_counts().reindex([False, True], fill_value=0)
        labels = ['Simple', 'Complex']
        counts.plot.pie(
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            ax=ax
        )
        ax.set_title(title, fontsize=12)  # Reduced font size
        ax.set_ylabel('')

    # Delivery Date Complexity Pie
    plot_pie(
        agg_df['delivery_date_complex'],
        axes_flat[0],
        '% of orders with multiple delivery dates',
        ['#66b3ff', '#ff9999']
    )

    # Vendor Complexity Pie
    plot_pie(
        agg_df['vendor_complex'],
        axes_flat[1],
        '% of orders with multiple vendors',
        ['#99ff99', '#ffcc99']
    )

    # Overall Complexity Pie
    plot_pie(
        agg_df['complex'],
        axes_flat[2],
        '% of orders with multiple vendors OR delivery dates',
        ['#c2c2f0', '#ffb3e6']
    )

    # Double Complexity Pie
    plot_pie(
        agg_df['double_complex'],
        axes_flat[3],
        '% of orders with multiple vendors AND delivery dates',
        ['#46b1ff', '#ff5939']
    )

    plt.tight_layout()
    return fig


def plot_nb_cmd_by_customer_10_less(df):
    nb_cmd_alltime_df = df

    def group_cmd(cmd):
        return str(cmd) if cmd <= 10 else '>10'

    # Apply grouping to both full and not-full datasets
    nb_cmd_alltime_df['cmd_grouped'] = nb_cmd_alltime_df['total_cmd'].apply(group_cmd)

    # Split by full member status
    full_df, notfull_df = split_by_full_member_status(nb_cmd_alltime_df)

    # Get value counts for cmd_grouped and sort
    full_counts = full_df['cmd_grouped'].value_counts().sort_index(key=lambda x: x.map(lambda v: int(v) if v != '>10' else 11))
    notfull_counts = notfull_df['cmd_grouped'].value_counts().sort_index(key=lambda x: x.map(lambda v: int(v) if v != '>10' else 11))

    # Ensure both share the same categories
    all_indexes = sorted(set(full_counts.index).union(set(notfull_counts.index)), key=lambda x: int(x) if x != '>10' else 11)
    full_counts = full_counts.reindex(all_indexes, fill_value=0)
    notfull_counts = notfull_counts.reindex(all_indexes, fill_value=0)

    # Create DataFrame for plotting
    combined_df = pd.DataFrame({
        'cmd': all_indexes,
        'Full Member': full_counts.values,
        'Not Full Member': notfull_counts.values
    })

    # Melt to long format for seaborn
    plot_df = combined_df.melt(id_vars='cmd', var_name='Membership', value_name='Count')

    # Define custom colors with alpha
    palette = {
        'Full Member': (0.2, 0.4, 1.0, 0.7),  # Blue
        'Not Full Member': (1.0, 0.2, 0.2, 0.7)  # Red
    }

    # Plot
    fig = plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=plot_df, x='cmd', y='Count', hue='Membership', palette=palette)

    # Customization
    plt.xlabel('Number of Orders (all time)')
    plt.ylabel(f'Number of Customers \n Total : {len(nb_cmd_alltime_df)}')
    plt.title('Number of Orders by Customer')

    return fig


def plot_nb_cmd_by_customer_10_more(df):
    nb_cmd_alltime_df = df.copy()

    nb_cmd_alltime_df = nb_cmd_alltime_df[nb_cmd_alltime_df['total_cmd'] > 10]

    def group_cmd(cmd):
        return str(cmd) if cmd <= 20 else '>20'

    nb_cmd_alltime_df['cmd_grouped'] = nb_cmd_alltime_df['total_cmd'].apply(group_cmd)

    # Split by full member status
    full_df, notfull_df = split_by_full_member_status(nb_cmd_alltime_df)

    # Get value counts for grouped order counts and sort
    sort_key = lambda x: x.map(lambda v: int(v) if v != '>20' else 21)
    full_counts = full_df['cmd_grouped'].value_counts().sort_index(key=sort_key)
    notfull_counts = notfull_df['cmd_grouped'].value_counts().sort_index(key=sort_key)

    # Ensure both share the same categories
    all_indexes = sorted(set(full_counts.index).union(set(notfull_counts.index)), key=lambda x: int(x) if x != '>20' else 21)
    if not all_indexes:
        return empty_chart('No customers with more than 10 orders found')

    full_counts = full_counts.reindex(all_indexes, fill_value=0)
    notfull_counts = notfull_counts.reindex(all_indexes, fill_value=0)

    # Create DataFrame for plotting
    combined_df = pd.DataFrame({
        'cmd': all_indexes,
        'Full Member': full_counts.values,
        'Not Full Member': notfull_counts.values
    })

    # Melt to long format for seaborn
    plot_df = combined_df.melt(id_vars='cmd', var_name='Membership', value_name='Count')

    # Define custom colors with alpha
    palette = {
        'Full Member': (0.2, 0.4, 1.0, 0.7),  # Blue
        'Not Full Member': (1.0, 0.2, 0.2, 0.7)  # Red
    }

    # Plot
    fig = plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=plot_df, x='cmd', y='Count', hue='Membership', palette=palette)

    # Customization
    plt.xlabel(f'Number of Orders (all time)')
    plt.ylabel(f'Number of Customers \n Total : {len(nb_cmd_alltime_df)}')
    plt.title('Number of Orders by Customer (more than 10 orders)')

    # plt.show()
    return fig


def plot_nb_cmd_by_customer_y1_y2(merged_df, status):
    status_title = status

    if status == 'Full Member':
        status = True
        status_color = 'blue'
    else:
        status = False
        status_color = 'red'

    merged_df = merged_df[merged_df['is_full_member'] == status]

    y1_df = merged_df[merged_df['in_y1'] == True]
    y1_df = y1_df[y1_df['from_created_to_today'] > 364]
    y1_df = y1_df.groupby('cmd').agg({'customer_name':'first', 'cmd':'first'})
    y1_df = y1_df.groupby('customer_name').agg({'cmd':'count'})
    y1_df['customer_name'] = y1_df.index
    y1_df_cus = len(y1_df)
    y1_df_nb_cmd = y1_df['cmd'].sum()

    y2_df = merged_df[merged_df['in_y2'] == True]
    y2_df = y2_df[y2_df['from_created_to_today'] > 364]
    y2_df = y2_df.groupby('cmd').agg({'customer_name':'first', 'cmd':'first'})
    y2_df = y2_df.groupby('customer_name').agg({'cmd':'count'})
    y2_df['customer_name'] = y2_df.index
    y2_df_cus = len(y2_df)
    y2_df_nb_cmd = y2_df['cmd'].sum()


    def group_cmd(cmd):
        return cmd if cmd <= 10 else '>10'

    # Apply grouping to both Year 1 and Year 2 datasets
    y1_df['cmd_grouped'] = y1_df['cmd'].apply(group_cmd)
    y2_df['cmd_grouped'] = y2_df['cmd'].apply(group_cmd)

    # Get value counts for each group
    y1_counts = y1_df['cmd_grouped'].value_counts().sort_index(key=lambda x: x.map(lambda v: int(v) if v != '>10' else 11))
    y2_counts = y2_df['cmd_grouped'].value_counts().sort_index(key=lambda x: x.map(lambda v: int(v) if v != '>10' else 11))

    # Ensure both share the same categories
    all_indexes = sorted(set(y1_counts.index).union(set(y2_counts.index)), key=lambda x: int(x) if x != '>10' else 11)
    if not all_indexes:
        return empty_chart(f'No Year 1 / Year 2 order data found for {status_title}')

    y1_counts = y1_counts.reindex(all_indexes, fill_value=0)
    y2_counts = y2_counts.reindex(all_indexes, fill_value=0)

    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), sharey=False)

    # Plot for Year 1
    sns.barplot(x=all_indexes, y=y1_counts.values, color=status_color, alpha=0.7, ax=ax1)
    ax1.set_title(f'{status_title}\nCompleted Year 1', fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel(f'Number of Orders - {y1_df_nb_cmd}')
    ax1.set_ylabel(f'Number of Customers - {y1_df_cus}')
    ax1.tick_params(axis='x', rotation=45)

    # Add raw counts and percentages for Year 1
    total_y1 = y1_counts.sum()
    for i, bar in enumerate(ax1.patches):
        height = bar.get_height()
        # Raw count inside bar
        ax1.text(bar.get_x() + bar.get_width()/2, height/2, f'{int(height)}',
                ha='center', va='center', fontsize=10, color='white', weight='bold')
        # Percentage above bar
        if total_y1 > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, height + 0.1, f'{height/total_y1*100:.1f}%',
                    ha='center', va='bottom', fontsize=10, color=status_color)

    # Plot for Year 2
    sns.barplot(x=all_indexes, y=y2_counts.values, color=status_color, alpha=0.7, ax=ax2)
    ax2.set_title(f'{status_title}\nYear 2 observed to date', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel(f'Number of Orders - {y2_df_nb_cmd}')
    ax2.set_ylabel(f'Number of Customers - {y2_df_cus}')
    ax2.tick_params(axis='x', rotation=45)

    # Add raw counts and percentages for Year 2
    total_y2 = y2_counts.sum()
    for i, bar in enumerate(ax2.patches):
        height = bar.get_height()
        # Raw count inside bar
        ax2.text(bar.get_x() + bar.get_width()/2, height/2, f'{int(height)}',
                ha='center', va='center', fontsize=10, color='white', weight='bold')
        # Percentage above bar
        if total_y2 > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, height + 0.1, f'{height/total_y2*100:.1f}%',
                    ha='center', va='bottom', fontsize=10, color=status_color)


    # Adjust layout to prevent overlap
    fig.tight_layout(pad=2.0, w_pad=3.0)
    #plt.show()
    return fig


def plot_renew_churn_metrics(df):
    # ISOLATING ORDER FROM 1ST YEAR
    merged_y1_df = df[df['in_y1'] == True]

    # ISOLATING RENEW AND CHURN
    renew_y2_df = merged_y1_df[merged_y1_df['renewed_to_y2'] == True]
    churn_y2_df = merged_y1_df[merged_y1_df['churn_to_y2'] == True]

    # Initialize metrics
    metrics = {
        'Mean Number of Orders': {'Renew': 0.0, 'Churn': 0.0},
        'Mean Order Value': {'Renew': 0.0, 'Churn': 0.0}
    }
    top_restaurants_renew = pd.Series(dtype=float)
    top_restaurants_churn = pd.Series(dtype=float)

    # Compute metrics for Renew
    if not renew_y2_df.empty:
        grp_renew_y2_df = renew_y2_df.groupby('customer_name').agg({'cmd': 'count', 'items_price': 'mean'})
        metrics['Mean Number of Orders']['Renew'] = round(grp_renew_y2_df['cmd'].mean(), 2)
        metrics['Mean Order Value']['Renew'] = round(grp_renew_y2_df['items_price'].mean(), 2)
        top_restaurants_renew = renew_y2_df.groupby('customer_name').agg({'vendor': 'last'})['vendor'].value_counts(normalize=True).head(5) * 100

    # Compute metrics for Churn
    if not churn_y2_df.empty:
        grp_churn_y2_df = churn_y2_df.groupby('customer_name').agg({'cmd': 'count', 'items_price': 'mean'})
        metrics['Mean Number of Orders']['Churn'] = round(grp_churn_y2_df['cmd'].mean(), 2)
        metrics['Mean Order Value']['Churn'] = round(grp_churn_y2_df['items_price'].mean(), 2)
        top_restaurants_churn = churn_y2_df.groupby('customer_name').agg({'vendor': 'last'})['vendor'].value_counts(normalize=True).head(5) * 100

    # Create figure with four subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 8))

    # Subplot 1: Mean Number of Orders
    renew_value_orders = metrics['Mean Number of Orders']['Renew']
    churn_value_orders = metrics['Mean Number of Orders']['Churn']
    ax1.bar([0], renew_value_orders, width=0.45, label='Renew', color='blue', alpha=0.7)
    ax1.bar([0.5], churn_value_orders, width=0.45, label='Churn', color='red', alpha=0.7)

    # Add value labels
    ax1.text(0, renew_value_orders + 0.5, f'{renew_value_orders:.2f}', ha='center', va='bottom', fontsize=10)
    ax1.text(0.5, churn_value_orders + 0.5, f'{churn_value_orders:.2f}', ha='center', va='bottom', fontsize=10)

    ax1.set_title('Mean Number of Orders')
    ax1.set_ylabel('Orders')
    ax1.set_xticks([0, 0.5])
    ax1.set_xticklabels(['Renew', 'Churn'])
    ax1.legend()
    ax1.grid(True, axis='y', linestyle='--', alpha=0.7)
    max_value_orders = max(renew_value_orders, churn_value_orders)
    y_max1 = np.ceil(max_value_orders / 5) * 5
    ax1.set_ylim(0, y_max1 + 5)
    ax1.set_yticks(np.arange(0, y_max1 + 6, 5))

    # Subplot 2: Mean Order Value
    renew_value_price = metrics['Mean Order Value']['Renew']
    churn_value_price = metrics['Mean Order Value']['Churn']
    ax2.bar([0], renew_value_price, width=0.45, label='Renew', color='blue', alpha=0.7)
    ax2.bar([0.5], churn_value_price, width=0.45, label='Churn', color='red', alpha=0.7)

    # Add value labels
    ax2.text(0, renew_value_price + 0.5, f'{renew_value_price:.2f}', ha='center', va='bottom', fontsize=10)
    ax2.text(0.5, churn_value_price + 0.5, f'{churn_value_price:.2f}', ha='center', va='bottom', fontsize=10)

    ax2.set_title('Mean Order Value')
    ax2.set_ylabel('Value ($)')
    ax2.set_xticks([0, 0.5])
    ax2.set_xticklabels(['Renew', 'Churn'])
    ax2.legend()
    ax2.grid(True, axis='y', linestyle='--', alpha=0.7)
    max_value_price = max(renew_value_price, churn_value_price)
    y_max2 = np.ceil(max_value_price / 10) * 10
    ax2.set_ylim(0, y_max2 + 5)
    ax2.set_yticks(np.arange(0, y_max2 + 6, 10))

    # Subplot 3: Top 5 Restaurants (Renew)
    if not top_restaurants_renew.empty:
        sns.barplot(x=top_restaurants_renew.index, y=top_restaurants_renew.values, color='blue', alpha=0.7, ax=ax3)
        for i, bar in enumerate(ax3.patches):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
    ax3.set_title('Top 5 vendors Leading to Renew')
    ax3.set_ylabel('Percentage of Customers')
    ax3.tick_params(axis='x', rotation=45)
    max_value_renew = top_restaurants_renew.max() if not top_restaurants_renew.empty else 100
    y_max3 = np.ceil(max_value_renew / 10) * 10
    ax3.set_ylim(0, y_max3 + 5)
    ax3.set_yticks(np.arange(0, y_max3 + 6, 10))
    ax3.grid(True, axis='y', linestyle='--', alpha=0.7)

    # Subplot 4: Top 5 Restaurants (Churn)
    if not top_restaurants_churn.empty:
        sns.barplot(x=top_restaurants_churn.index, y=top_restaurants_churn.values, color='red', alpha=0.7, ax=ax4)
        for i, bar in enumerate(ax4.patches):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
    ax4.set_title('Top 5 vendors Leading to Cancellation')
    ax4.set_ylabel('Percentage of Customers')
    ax4.tick_params(axis='x', rotation=45)
    max_value_churn = top_restaurants_churn.max() if not top_restaurants_churn.empty else 100
    y_max4 = np.ceil(max_value_churn / 10) * 10
    ax4.set_ylim(0, y_max4 + 5)
    ax4.set_yticks(np.arange(0, y_max4 + 6, 10))
    ax4.grid(True, axis='y', linestyle='--', alpha=0.7)


    # plt.show()
    return fig
__all__ = [
    "plot_first_order",
    "plot_first_order_1",
    "plot_first_order_2",
    "plot_first_order_3",
    "plot_first_order_4",
    "discount_vendor",
    "plot_how_many_days_after_sub",
    "plot_gift_and_not",
    "plot_price_distribution",
    "plot_simple_and_complex_order",
    "plot_nb_cmd_by_customer_10_less",
    "plot_nb_cmd_by_customer_10_more",
    "plot_nb_cmd_by_customer_y1_y2",
    "plot_renew_churn_metrics",
]
