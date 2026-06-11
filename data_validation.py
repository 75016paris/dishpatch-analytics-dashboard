"""Lightweight CSV schema checks for the dashboard inputs."""

REQUIRED_COLUMNS = {
    "subscription CSV": {
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
    },
    "orders CSV": {
        "Name",
        "Paid at",
        "Subtotal",
        "Discount Amount",
        "Note Attributes",
        "Lineitem quantity",
        "Vendor",
        "Lookup",
        "Lineitem name",
    },
    "product CSV": {
        "Title",
        "Vendor",
        "Variant Price",
        "Option1 Value",
        "Status",
    },
}


def missing_required_columns(df, required_columns):
    """Return required columns that are missing from a dataframe."""
    return sorted(set(required_columns) - set(df.columns))


def validate_dashboard_inputs(subscription_df, orders_df, products_df):
    """Return a dict of input names to missing columns."""
    dataframes = {
        "subscription CSV": subscription_df,
        "orders CSV": orders_df,
        "product CSV": products_df,
    }
    missing_by_file = {}
    for name, df in dataframes.items():
        missing = missing_required_columns(df, REQUIRED_COLUMNS[name])
        if missing:
            missing_by_file[name] = missing
    return missing_by_file
