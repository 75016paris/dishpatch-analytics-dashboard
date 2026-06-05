# Data schema

All sample files in this public mirror are synthetic.

## `sample_data/subscriptions.csv`

Main columns:

- `id` — synthetic subscription id.
- `Customer Name` — synthetic customer label.
- `Customer ID` — synthetic customer id.
- `Status` — subscription status such as `active`, `trialing`, or `canceled`.
- `Cancellation Reason` — optional synthetic cancellation reason.
- `Created (UTC)`, `Start (UTC)`, `Trial Start (UTC)`, `Trial End (UTC)`, `Canceled At (UTC)`, `Ended At (UTC)` — subscription lifecycle dates.
- `senderShopifyCustomerId (metadata)` — used by the original notebook/app logic as a gift-member flag.

## `sample_data/orders.csv`

Main columns:

- `Name` — synthetic order number.
- `Paid at` — synthetic paid timestamp.
- `Subtotal`, `Discount Amount` — synthetic amounts.
- `Note Attributes` — gift/note metadata string.
- `Lineitem quantity`, `Vendor`, `Lookup`, `Lineitem name` — line-item fields used to aggregate orders and join subscriptions.

## `sample_data/products.csv`

Main columns:

- `Title` — product title matching order line items.
- `Vendor` — synthetic vendor/chef label.
- `Variant Price` — synthetic unit price.
- `Option1 Value`, `Status` — product metadata kept for shape compatibility.
