"""Analytics helpers for KPI and trend calculations."""

import pandas as pd
from datetime import datetime, timedelta


def calculate_kpis(bills_df):
    df = bills_df.copy()

    df["purchase_date_dt"] = pd.to_datetime(
        df.get("purchase_date"), errors="coerce"
    )

    total_spent = df["total_amount"].sum()
    months_active = df["purchase_date_dt"].dt.to_period("M").nunique() or 1
    avg_per_month = total_spent / months_active
    vendors_count = df["vendor_name"].nunique()
    transactions_count = len(df)

    avg_transaction = (
        total_spent / transactions_count if transactions_count > 0 else 0
    )

    return {
        "total_spent": total_spent,
        "avg_per_month": avg_per_month,
        "vendors_count": vendors_count,
        "transactions_count": transactions_count,
        "avg_transaction": avg_transaction,
    }


def calculate_month_comparison(bills_df):
    df = bills_df.copy()

    df["purchase_date_dt"] = pd.to_datetime(
        df.get("purchase_date"), errors="coerce"
    )

    current_month = datetime.now().replace(day=1)
    prev_month = (current_month - timedelta(days=1)).replace(day=1)

    current_month_data = df[df["purchase_date_dt"] >= current_month]
    prev_month_data = df[
        (df["purchase_date_dt"] >= prev_month)
        & (df["purchase_date_dt"] < current_month)
    ]

    current_month_spend = current_month_data["total_amount"].sum()
    prev_month_spend = prev_month_data["total_amount"].sum()

    spend_delta = current_month_spend - prev_month_spend
    spend_delta_pct = (
        (spend_delta / prev_month_spend * 100)
        if prev_month_spend > 0 else 0
    )

    return {
        "current_month_spend": current_month_spend,
        "prev_month_spend": prev_month_spend,
        "spend_delta_pct": spend_delta_pct,
    }
