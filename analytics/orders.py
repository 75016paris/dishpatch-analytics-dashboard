"""Order cleaning, pricing, subscription matching, and order-year flags."""

from .common import *

def preprocess_order(df):

    # Convertir les colonnes contenant '(UTC)' en datetime
    date_cols = [col for col in df.columns if '(UTC)' in col]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)

    # Sélectionner les colonnes pertinentes
    columns_to_keep = [
        'Name', 'Paid at', 'Subtotal', 'Discount Amount', 'Note Attributes',
        'Lineitem quantity', 'Vendor', 'Lookup', 'Lineitem name'
    ]

    df = df[columns_to_keep]

    # Renommer les colonnes
    df = df.rename(columns={
        'Paid at': 'date',
        'Subtotal': 'subtotal',
        'Discount Amount': 'discount',
        'Note Attributes': 'note',
        'Lineitem quantity': 'qty',
        'Vendor': 'vendor',
        'Lookup': 'customer_name',
        'Lineitem name': 'item',
        'Name': 'cmd'
    })

    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['customer_join_key'] = df['customer_name'].apply(normalize_customer_key)

    df = df[df['vendor'] != 'ClientBrand']
    df = df[df['vendor'].notna()]

    return df


def split_name_and_delivery(item_name):
    # Match the pattern: item_name - delivery_date
    match = re.match(r'^(.*?) - (.*)$', item_name)
    if match:
        item_clean = match.group(1).strip()  # Part before ' - '
        delivery_date = match.group(2).strip()  # Part after ' - '
        return item_clean, delivery_date
    else:
        # If no ' - ' is found, return the original name and None for delivery_date
        return item_name.strip(), None


def order_grouping(df):

    df['cmd_nb'] = 1

    order_group_cmd_df = df.groupby('cmd').agg({'date': 'first', 'note': 'first', 'cmd_nb': 'sum'})
    order_group_cmd_df = order_group_cmd_df[order_group_cmd_df['date'].notna()]

    df = df.merge(order_group_cmd_df, on='cmd', how='right')

    # Renaming columns after the merge
    df = df[['customer_name', 'customer_join_key', 'cmd', 'date_y', 'vendor', 'item', 'qty', 'note_y', 'cmd_nb_y']]
    df = df.rename(columns={'date_y': 'date', 'note_y': 'note', 'cmd_nb_y': 'cmd_nb'})

    df['is_complex'] = df['cmd_nb'] > 1

    return df


def flag_gift_and_note(df):
    # Flagging Gift & Note
    df['is_gift'] = df['note'].str.contains(r'isGift: true', na=False)
    df['have_note'] = df['note'].str.contains(r'isGift:\s*true\ngiftMessage:\s*\S+', na=False)
    # Override any "giftMessage: false" to False
    df.loc[df['note'].str.contains(r'\ngiftMessage:\s*false', na=False), 'have_note'] = False

    # Loosing the original note column
    df = df.drop(columns='note')

    return df


def clean_and_enrich_order_data(df):

    # Clean item name
    cleaned_data = [split_name_and_delivery(item) for item in df['item']]
    order_df_cleaned = pd.DataFrame(cleaned_data, columns=['item_name', 'delivery_date'])

    # Add the new columns to the original df
    df[['item_name', 'delivery_date']] = order_df_cleaned


    return df


def item_name_cleaning(df):
    # michel-roux-jr
    df.loc[df['item_name'] == 'Bouef Bourguignon Classique', 'item_name'] = 'Boeuf Bourguignon Classique'

    #michel roux consolidating (there were prices for both but seems to be the same)
    df.loc[df['item_name'] == "Valentine’s Dinner à Deux", 'item_name'] = "Valentine's Dinner à Deux"
    df.loc[df['item_name'] == "Michel’s French Feast", 'item_name'] = "Michel's French Feast"
    df.loc[df['item_name'] == "Easter Braised Lamb Banquet", 'item_name'] = "Easter Lamb Banquet"

    # cafe murano
    df.loc[df['item_name'] == 'Torta di Nocciole', 'item_name'] = 'Italian Chocolate & Hazelnut Torte'
    df.loc[df['item_name'] == 'Bistecca alla Fiorentina (delivering from 28th March)', 'item_name'] = 'Bistecca alla Fiorentina'
    df.loc[df['item_name'] == 'Bistecca alla Fiorentina (delivering from 13th June)', 'item_name'] = 'Bistecca alla Fiorentina'
    df.loc[df['item_name'] == 'Autumn Baked Gnocchi', 'item_name'] = 'Baked Gnocchi Supper'
    df.loc[df['item_name'] == 'Slow-Roast Pork & Fennel', 'item_name'] = 'Italian Porchetta Feast'
    df.loc[df['item_name'] == "Angela's Easter Porchetta", 'item_name'] = "Angela's Porchetta"

    #sabrina-ghayour
    df.loc[df['item_name'] == 'Spiced Feta & Chickpea Bastilla (delivering from 21st March)', 'item_name'] = 'Spiced Feta & Chickpea Bastilla'
    df.loc[df['item_name'] == 'A Celebration of Persiana', 'item_name'] = 'Persiana Summer Mezze'
    df.loc[df['item_name'] == 'Spiced Chickpea & Feta Bastilla', 'item_name'] = 'Spiced Feta & Chickpea Bastilla'

    # empire-empire
    df.loc[df['item_name'] == "Biryani Wazwan Feast (delivering from 4th April)", 'item_name'] = "Biryani Wazwan Feast"

    # Rick Stein
    df.loc[df['item_name'] == "Winter Seafood Supper", 'item_name'] = "Stein's Seafood Supper"
    # hard to find the equivalent for Tuna, just took Cornish Summer Sole as price almost same and similar product at Rick Stein
    df.loc[df['item_name'] == "Tuna Steaks & Scallops", 'item_name'] = "Cornish Summer Sole"
    df.loc[df['item_name'] == "Seared Tuna In Red Wine", 'item_name'] = "Cornish Summer Sole"

    # st-john
    df.loc[df['item_name'] == "St. JOHN Crémant de Limoux 2020", 'item_name'] = "St. JOHN Crémant de Limoux 2021"
    df.loc[df['item_name'] == "St. JOHN Picpoul 2022", 'item_name'] = "St. JOHN Picpoul de Pinet 2024"
    df.loc[df['item_name'] == "St. JOHN Picpoul de Pinet 2023", 'item_name'] = "St. JOHN Picpoul de Pinet 2024"
    df.loc[df['item_name'] == "St. JOHN Mâcon-Village 2020", 'item_name'] = "St. JOHN Mâcon-Village 2022"
    df.loc[df['item_name'] == "St. JOHN Festive Reds", 'item_name'] = "St. JOHN Summer Wines"

    #richard-corrigan
    df.loc[df['item_name'] == "Corrigan's Summertime Supper", 'item_name'] = "Corrigan's Springtime Supper"
    df.loc[df['item_name'] == "Corrigan's Autumn Pork", 'item_name'] = "Sugar Pit Pork"
    df.loc[df['item_name'] == "Springtime Irish Stew", 'item_name'] = "Spring Irish Lamb"

    #paul-ainsworth
    df.loc[df['item_name'] == "Shrimp Brown Butter Monkfish", 'item_name'] = "Shellfish Brown Butter Monkfish"

    #atul-kochhar
    df.loc[df['item_name'] == "Kadhai Chicken Feast", 'item_name'] = "Goan-Spiced Feast"

    #jose-pizarro
    df.loc[df['item_name'] == "x8 Jamón Croquetas (With oil)", 'item_name'] = "x8 Jamón Croquetas"
    df.loc[
        df['item_name'].str.contains(r"^Castilian Suckling Lamb \(delivering from", na=False),
        'item_name'
    ] = "Castilian Suckling Lamb"

    #georgina-hayden
    df.loc[df['item_name'] == "Trip To Greece", 'item_name'] = "The Greek Islands"

    #el-pastor
    df.loc[df['item_name'] == 'Taco Party: "Contramar" Sea Bream', 'item_name'] = 'Taco Party: Beef Short Rib'


    #andi-oliver
    df.loc[df['item_name'] == "Caribbean Rum & Ginger Pork", 'item_name'] = "Rum & Ginger Pork Belly"
    #additional special cases below

    return df


def preprocess_product(df):
    df = df[['Title', 'Vendor', 'Variant Price', 'Option1 Value', 'Status']]
    df = df.drop_duplicates(subset=['Title'], keep='first')

    return df


def pricing_items(order_df, product_df):
    product_df = preprocess_product(product_df)
    order_df = order_df.copy()

    order_df = order_df.merge(product_df[['Title', 'Variant Price']], left_on='item_name', right_on='Title', how='left')

    order_df['price'] = pd.to_numeric(order_df['Variant Price'], errors='coerce')
    order_df = order_df.drop(columns=['Title', 'Variant Price'])
    order_df['items_price'] = order_df['price'] * order_df['qty']

    return order_df


def renew_churn_status(df, renewal_dict):
    renewed_to_y2_df = renewal_dict['renewed_to_y2_df']
    customer_in_y2_df = renewal_dict['customer_in_y2_df']


    # Calculate churn_y2_df as those eligible for Y2 but not renewed to Y2
    churn_y2_df = customer_in_y2_df[~customer_in_y2_df['customer_name'].isin(renewed_to_y2_df['customer_name'])]


    df['renewed_to_y2'] = df['customer_name'].isin(renewed_to_y2_df['customer_name'])
    df['churn_to_y2'] = df['customer_name'].isin(churn_y2_df['customer_name'])



    return df


def creating_short_sub_df(sub_df):
    df = sub_df.copy()
    if 'customer_join_key' not in df.columns:
        df['customer_join_key'] = df['customer_name'].apply(normalize_customer_key)

    df = df.sort_values('created_utc', ascending=True)
    df = df.groupby('customer_join_key').agg({'customer_name': 'first',
                                          'created_utc':'first',
                                          'status': 'last',
                                          'is_full_member': 'last',
                                          'paid_duration': 'last',
                                          'renewed_to_y2':'any',
                                          'churn_to_y2':'any'})
    df = df.reset_index()

    df['created_utc'] = pd.to_datetime(df['created_utc']).dt.date

    return df


def merging_order_df_with_short_sub_df(order_df, short_sub_df):
    order_df = order_df.copy()
    short_sub_df = short_sub_df.copy()

    if 'customer_join_key' in order_df.columns and 'customer_join_key' in short_sub_df.columns:
        sub_lookup = short_sub_df.drop(columns=['customer_name'], errors='ignore')
        df = order_df.merge(sub_lookup, on='customer_join_key', how='left')
    else:
        # Fallback for older/preprocessed dataframes without normalized keys.
        df = order_df.merge(short_sub_df, on='customer_name', how='left')

    # Sort by date
    df = df.sort_values('date')

    # Fill NaN for columns from short_sub_df
    df['is_full_member'] = df['is_full_member'].fillna(False).astype(bool)
    df['status'] = df['status'].fillna('inactive')
    df['paid_duration'] = df['paid_duration'].fillna(0)
    df['renewed_to_y2'] = df['renewed_to_y2'].fillna(False).astype(bool)
    df['churn_to_y2'] = df['churn_to_y2'].fillna(False).astype(bool)

    df['created_utc'] = pd.to_datetime(df['created_utc'], errors='coerce')
    fallback_key = 'customer_join_key' if 'customer_join_key' in df.columns else 'customer_name'
    first_dates = df.groupby(fallback_key)['date'].first()
    df['created_utc'] = df['created_utc'].fillna(df[fallback_key].map(first_dates))

    df['created_utc'] = pd.to_datetime(df['created_utc']).dt.date

    return df


def add_subscription_age(df, today_date=None):
    if today_date is None:
        today_date = pd.Timestamp.now(tz='UTC')

    today = pd.Timestamp(today_date).normalize().tz_localize(None)
    created_dt = pd.to_datetime(df['created_utc'], errors='coerce')
    df['from_created_to_today'] = (today - created_dt).dt.days
    return df


def creating_year_col(df):
    # Sauvegarder les colonnes originales pour les restaurer à la fin
    original_date = df['date'].copy()
    original_created_utc = df['created_utc'].copy()

    # Convertir temporairement en datetime64[ns] pour les comparaisons
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['created_utc'] = pd.to_datetime(df['created_utc'], errors='coerce')

    # Créer start_y2 et start_y3
    df['start_y2'] = df['created_utc'] + pd.DateOffset(years=1)
    df['start_y3'] = df['created_utc'] + pd.DateOffset(years=2)

    # Effectuer les comparaisons et gérer les NaT
    df['before_sub'] = (df['date'] < df['created_utc']).fillna(False)
    df['in_y1'] = ((df['date'] < df['start_y2']) & (df['date'] >= df['created_utc'])).fillna(False)
    df['in_y2'] = ((df['date'] < df['start_y3']) & (df['date'] >= df['start_y2'])).fillna(False)
    df['in_y3'] = (df['date'] > df['start_y3']).fillna(False)

    # Restaurer les colonnes originales au format datetime.date
    df['date'] = original_date
    df['created_utc'] = original_created_utc

    return df


def split_by_year(df):
    in_y0 = df[df['before_sub'] == True]
    in_y1 = df[df['in_y1'] == True]
    in_y2 = df[df['in_y2'] == True]
    in_y3 = df[df['in_y3'] == True]

    return in_y0, in_y1, in_y2, in_y3


def split_by_full_member_status(df):
    df_full = df[df['is_full_member'] == True]
    df_not_full = df[df['is_full_member'] == False]

    return df_full, df_not_full


def after_sub_7(df):

    # Select only orders placed after the subscription date, and within 7 days after subscription
    after_sub_7_df = df[
        (df['date'] >= df['created_utc']) &
        (df['date'] <= (df['created_utc'] + pd.Timedelta(days=7)))]

    # Get the first order (vendor / gift / note) after subscription (+7 days) for each customer
    after_sub_7_df = after_sub_7_df.groupby('customer_name').agg({
        'vendor': 'first',
        'is_full_member': 'first',
        'date':'first',
        'is_gift':'first',
        'have_note':'first'})

    return after_sub_7_df


def find_nb_cmd(df):
    # First aggregation: Group by command to get order details
    nb_cmd_alltime_df = df.groupby('cmd').agg({
    'items_price': 'sum',
    'customer_name': 'first',
    'is_full_member': 'first',
    'before_sub': 'first',
    'in_y1': 'first',
    'in_y2': 'first',
    'in_y3': 'first',
    'from_created_to_today': 'first'
    })

    nb_cmd_alltime_df['cmd'] = nb_cmd_alltime_df.index

    # Second aggregation: Group by customer to get command counts and means
    nb_cmd_alltime_df = nb_cmd_alltime_df.groupby('customer_name').agg({
        'items_price': 'mean',
        'cmd': 'count',
        'is_full_member': 'first',
        'before_sub': 'first',
        'in_y1': 'first',
        'in_y2': 'first',
        'in_y3': 'first',
        'from_created_to_today': 'first'
    })

    nb_cmd_alltime_df = nb_cmd_alltime_df.rename(columns={'items_price': 'cmd_price_mean', 'cmd': 'total_cmd'})

    return nb_cmd_alltime_df
__all__ = [
    "preprocess_order",
    "split_name_and_delivery",
    "order_grouping",
    "flag_gift_and_note",
    "clean_and_enrich_order_data",
    "item_name_cleaning",
    "preprocess_product",
    "pricing_items",
    "renew_churn_status",
    "creating_short_sub_df",
    "merging_order_df_with_short_sub_df",
    "add_subscription_age",
    "creating_year_col",
    "split_by_year",
    "split_by_full_member_status",
    "after_sub_7",
    "find_nb_cmd",
]
