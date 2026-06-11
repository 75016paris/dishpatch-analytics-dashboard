"""Shared imports, constants, and small helpers for analytics modules."""

import glob
import os
import re
import shutil
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

pd.set_option("display.max_columns", None)

plt.rcParams.update({"font.size": 11, "axes.labelsize": 10, "axes.titlesize": 16})
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["axes.edgecolor"] = "black"
plt.rcParams["xtick.color"] = "black"
plt.rcParams["ytick.color"] = "black"
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.color"] = "lightgray"
plt.rcParams["grid.alpha"] = 0.5
plt.rcParams["axes.axisbelow"] = True
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.titlecolor"] = "black"
plt.rcParams["axes.labelcolor"] = "black"
plt.rcParams["legend.labelcolor"] = "black"
plt.rcParams["legend.facecolor"] = "white"
plt.rcParams["legend.edgecolor"] = "gray"
plt.rcParams["text.color"] = "black"
sns.set_palette("viridis")

REFUND_PERIOD_DAYS = 14
HIGH_VOLUME_THRESHOLD = 4
DUPLICATE_THRESHOLD_MINUTES = 15


def _log(*_args, **_kwargs):
    """Internal no-op logger for optional diagnostic messages."""
    return None


def empty_chart(message, figsize=(10, 5)):
    """Return a simple placeholder figure when a chart has no data."""
    fig, ax = plt.subplots(figsize=figsize)
    ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12, wrap=True)
    ax.axis('off')
    fig.tight_layout()
    return fig


def normalize_customer_key(value):
    """Normalize sanitized customer labels so 'Customer 5019' matches 'Customer5019'."""
    if pd.isna(value):
        return pd.NA
    value = str(value).strip().lower()
    value = re.sub(r'[^a-z0-9]+', '', value)
    return value or pd.NA


def get_iso_week_bounds(year, week):
    jan_4 = datetime(year, 1, 4)
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    target_monday = week_1_monday + timedelta(weeks=week-1)
    target_sunday = target_monday + timedelta(days=6)

    return target_monday, target_sunday


def get_weeks_in_iso_year(year):
    dec_28 = datetime(year, 12, 28)

    return dec_28.isocalendar().week


def calculate_target_iso_week(today_iso, weeks_back):

    target_year, target_week = today_iso.year, today_iso.week

    # Recalculate X weeks
    for _ in range(weeks_back):
        target_week -= 1
        if target_week <= 0:
            target_year -= 1
            weeks_in_prev_year = get_weeks_in_iso_year(target_year)
            target_week = weeks_in_prev_year

    iso_week_key = f"{target_year}-W{target_week:02d}"

    return target_year, target_week, iso_week_key
__all__ = [
    "glob",
    "os",
    "re",
    "shutil",
    "datetime",
    "timedelta",
    "plt",
    "np",
    "pd",
    "sns",
    "REFUND_PERIOD_DAYS",
    "HIGH_VOLUME_THRESHOLD",
    "DUPLICATE_THRESHOLD_MINUTES",
    "_log",
    "empty_chart",
    "normalize_customer_key",
    "get_iso_week_bounds",
    "get_weeks_in_iso_year",
    "calculate_target_iso_week",
]
