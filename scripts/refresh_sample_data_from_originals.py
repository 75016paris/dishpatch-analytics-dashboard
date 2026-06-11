#!/usr/bin/env python3
"""Build public sample CSVs from local sanitized source exports.

The source files stay outside the repository. This script writes only the
portfolio-safe, anonymized, date-shifted CSVs under sample_data/.
"""

import argparse
import os
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "sample_data"

SUBSCRIPTION_COLUMNS = [
    "id",
    "Customer Name",
    "Customer ID",
    "Status",
    "Cancellation Reason",
    "Created (UTC)",
    "Start (UTC)",
    "Current Period Start (UTC)",
    "Current Period End (UTC)",
    "Trial Start (UTC)",
    "Trial End (UTC)",
    "Canceled At (UTC)",
    "Ended At (UTC)",
    "senderShopifyCustomerId (metadata)",
]

ORDER_COLUMNS = [
    "Name",
    "Paid at",
    "Subtotal",
    "Discount Amount",
    "Note Attributes",
    "Lineitem quantity",
    "Vendor",
    "Lookup",
    "Lineitem name",
]

PRODUCT_COLUMNS = ["Title", "Vendor", "Variant Price", "Option1 Value", "Status"]

SUBSCRIPTION_DATE_COLUMNS = [
    "Created (UTC)",
    "Start (UTC)",
    "Current Period Start (UTC)",
    "Current Period End (UTC)",
    "Trial Start (UTC)",
    "Trial End (UTC)",
    "Canceled At (UTC)",
    "Ended At (UTC)",
]

ANCHOR_DATE_COLUMNS = [
    "Created (UTC)",
    "Start (UTC)",
    "Current Period Start (UTC)",
    "Canceled At (UTC)",
    "Ended At (UTC)",
]


def normalize_key(value):
    if pd.isna(value):
        return pd.NA
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value or pd.NA


def iso_or_blank(series):
    values = pd.to_datetime(series, errors="coerce", utc=True)
    return values.map(lambda value: value.isoformat() if pd.notna(value) else pd.NA)


def make_mapping(values, prefix, width=5):
    cleaned = []
    seen = set()
    for value in values:
        if pd.isna(value):
            continue
        value = str(value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return {value: f"{prefix} {index:0{width}d}" for index, value in enumerate(cleaned, start=1)}


def item_base(value):
    if pd.isna(value):
        return pd.NA
    value = str(value).strip()
    if " - " in value:
        return value.rsplit(" - ", 1)[0].strip()
    return value


def shift_possible_date_text(text, day_offset):
    if pd.isna(text) or " - " not in str(text):
        return text
    base, suffix = str(text).rsplit(" - ", 1)
    parsed = pd.to_datetime(suffix, errors="coerce", dayfirst=True)
    if pd.isna(parsed) or parsed.year < 2000:
        return text
    shifted = parsed + pd.Timedelta(days=day_offset)
    return f"{base} - {shifted.strftime('%d %B %Y')}"


def shift_date_columns(df, columns, day_offset):
    df = df.copy()
    for column in columns:
        if column in df.columns:
            shifted = pd.to_datetime(df[column], errors="coerce", utc=True) + pd.Timedelta(days=day_offset)
            df[column] = shifted.map(lambda value: value.isoformat() if pd.notna(value) else pd.NA)
    return df


def latest_subscription_event_date(subscriptions):
    dates = []
    for column in ANCHOR_DATE_COLUMNS:
        if column in subscriptions.columns:
            parsed = pd.to_datetime(subscriptions[column], errors="coerce", utc=True)
            if parsed.notna().any():
                dates.append(parsed.max())
    if not dates:
        raise ValueError("No usable subscription event dates found")
    return max(dates)


def anonymize_customer_fields(subscriptions, orders):
    sub_keys = subscriptions["Customer Name"].map(normalize_key)
    order_keys = orders["Lookup"].map(normalize_key)
    keys = pd.concat([sub_keys, order_keys], ignore_index=True).dropna().drop_duplicates().tolist()
    customer_map = {key: f"Customer {index:05d}" for index, key in enumerate(keys, start=1)}

    subscriptions = subscriptions.copy()
    orders = orders.copy()
    subscriptions["Customer Name"] = sub_keys.map(customer_map)
    orders["Lookup"] = order_keys.map(customer_map)

    id_values = subscriptions["Customer ID"].dropna().astype(str).drop_duplicates().tolist()
    id_map = {value: f"cus_{index:05d}" for index, value in enumerate(id_values, start=1)}
    subscriptions["Customer ID"] = subscriptions["Customer ID"].astype(str).map(id_map)

    sub_id_values = subscriptions["id"].dropna().astype(str).drop_duplicates().tolist()
    sub_id_map = {value: f"sub_{index:05d}" for index, value in enumerate(sub_id_values, start=1)}
    subscriptions["id"] = subscriptions["id"].astype(str).map(sub_id_map)

    order_values = orders["Name"].dropna().astype(str).drop_duplicates().tolist()
    order_map = {value: f"#{100000 + index}" for index, value in enumerate(order_values, start=1)}
    orders["Name"] = orders["Name"].astype(str).map(order_map)

    gift_column = "senderShopifyCustomerId (metadata)"
    subscriptions[gift_column] = subscriptions[gift_column].astype("object")
    gifted = subscriptions[gift_column].notna()
    subscriptions.loc[gifted, gift_column] = [
        f"gift_{index:05d}" for index in range(1, int(gifted.sum()) + 1)
    ]
    subscriptions.loc[~gifted, gift_column] = pd.NA

    return subscriptions, orders


def sanitize_note_attributes(value):
    text = "" if pd.isna(value) else str(value)
    is_gift = "isGift: true" in text
    has_message = "giftMessage:" in text and "giftMessage: false" not in text
    return f"isGift: {'true' if is_gift else 'false'}\ngiftMessage: {'true' if has_message else 'false'}"


def anonymize_products_and_items(orders, products):
    orders = orders.copy()
    products = products.copy()

    product_titles = products["Title"].dropna().astype(str).tolist()
    order_bases = orders["Lineitem name"].map(item_base).dropna().astype(str).tolist()
    title_map = make_mapping(product_titles + order_bases, "Meal Kit", width=4)

    vendor_values = pd.concat([orders["Vendor"], products["Vendor"]], ignore_index=True)
    vendor_map = make_mapping(vendor_values, "Vendor", width=2)

    orders["Vendor"] = orders["Vendor"].astype(str).map(vendor_map)
    products["Vendor"] = products["Vendor"].astype(str).map(vendor_map)

    def anonymize_lineitem(value):
        base = item_base(value)
        if pd.isna(base):
            return value
        anonymized_base = title_map.get(str(base), str(base))
        if pd.isna(value) or " - " not in str(value):
            return anonymized_base
        suffix = str(value).rsplit(" - ", 1)[1]
        return f"{anonymized_base} - {suffix}"

    orders["Lineitem name"] = orders["Lineitem name"].map(anonymize_lineitem)
    products["Title"] = products["Title"].astype(str).map(title_map)

    missing_titles = sorted(set(orders["Lineitem name"].map(item_base).dropna()) - set(products["Title"].dropna()))
    if missing_titles:
        fallback_prices = orders.assign(_base=orders["Lineitem name"].map(item_base)).groupby("_base")["Subtotal"].median()
        extra_products = pd.DataFrame(
            {
                "Title": missing_titles,
                "Vendor": "Vendor 00",
                "Variant Price": [float(fallback_prices.get(title, 50.0)) for title in missing_titles],
                "Option1 Value": "Default",
                "Status": "active",
            }
        )
        products = pd.concat([products, extra_products], ignore_index=True)

    products = products.dropna(subset=["Title"]).drop_duplicates(subset=["Title"], keep="first")
    return orders, products


def build_sample_data(subscription_source, orders_source, products_source, target_date=None):
    for path in (subscription_source, orders_source, products_source):
        if not path.exists():
            raise FileNotFoundError(path)

    subscriptions = pd.read_csv(subscription_source, low_memory=False)[SUBSCRIPTION_COLUMNS].copy()
    orders = pd.read_csv(orders_source, low_memory=False)[ORDER_COLUMNS].copy()
    products = pd.read_csv(products_source, low_memory=False)[PRODUCT_COLUMNS].copy()

    subscription_anchor = latest_subscription_event_date(subscriptions)
    order_paid_at = pd.to_datetime(orders["Paid at"], errors="coerce", utc=True)
    if order_paid_at.notna().any():
        order_anchor = order_paid_at.max()
    else:
        order_anchor = subscription_anchor

    target = pd.Timestamp(target_date or pd.Timestamp.now(tz="UTC")).tz_convert("UTC").normalize()
    subscription_day_offset = int((target - subscription_anchor.normalize()).days)
    order_day_offset = int((target - order_anchor.normalize()).days)

    subscriptions = shift_date_columns(subscriptions, SUBSCRIPTION_DATE_COLUMNS, subscription_day_offset)
    orders = shift_date_columns(orders, ["Paid at"], order_day_offset)
    orders["Lineitem name"] = orders["Lineitem name"].map(lambda value: shift_possible_date_text(value, order_day_offset))

    subscriptions, orders = anonymize_customer_fields(subscriptions, orders)
    orders, products = anonymize_products_and_items(orders, products)
    orders["Note Attributes"] = orders["Note Attributes"].map(sanitize_note_attributes)

    subscriptions = subscriptions[SUBSCRIPTION_COLUMNS]
    orders = orders[ORDER_COLUMNS]
    products = products[PRODUCT_COLUMNS]

    return subscriptions, orders, products, subscription_day_offset, order_day_offset, subscription_anchor, order_anchor


def source_path(value):
    return Path(value).expanduser() if value else None


def parse_args():
    parser = argparse.ArgumentParser(description="Refresh anonymized public sample CSVs from local source exports.")
    parser.add_argument("--subscriptions", default=os.getenv("SOURCE_SUBSCRIPTIONS_CSV"), help="Local subscription export CSV")
    parser.add_argument("--orders", default=os.getenv("SOURCE_ORDERS_CSV"), help="Local orders export CSV")
    parser.add_argument("--products", default=os.getenv("SOURCE_PRODUCTS_CSV"), help="Local products export CSV")
    return parser.parse_args()


def main():
    args = parse_args()
    subscription_source = source_path(args.subscriptions)
    orders_source = source_path(args.orders)
    products_source = source_path(args.products)
    if not all([subscription_source, orders_source, products_source]):
        raise SystemExit("Provide --subscriptions, --orders, and --products paths, or set SOURCE_*_CSV env vars.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    subscriptions, orders, products, subscription_day_offset, order_day_offset, subscription_anchor, order_anchor = build_sample_data(subscription_source, orders_source, products_source)
    subscriptions.to_csv(OUTPUT_DIR / "subscriptions.csv", index=False)
    orders.to_csv(OUTPUT_DIR / "orders.csv", index=False)
    products.to_csv(OUTPUT_DIR / "products.csv", index=False)

    print("Sample data refreshed from anonymized source exports")
    print(f"Subscription anchor: {subscription_anchor.date()} ({subscription_day_offset:+d} days)")
    print(f"Order anchor: {order_anchor.date()} ({order_day_offset:+d} days)")
    print(f"Subscriptions: {len(subscriptions):,}")
    print(f"Order rows: {len(orders):,}")
    print(f"Products: {len(products):,}")


if __name__ == "__main__":
    sys.exit(main())
