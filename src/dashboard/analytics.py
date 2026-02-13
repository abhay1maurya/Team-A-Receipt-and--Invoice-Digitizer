"""Analytics helpers for the dashboard."""
"""
Analytics module for financial dashboard.

This file contains pure data-processing logic.
No Streamlit UI code should exist here.
"""

import pandas as pd
from datetime import datetime, timedelta

# DATA PREPARATION

def prepare_bills_dataframe(bills: list) -> pd.DataFrame:
    """
    Convert raw bills list into cleaned DataFrame.
    """
    if not bills:
        return pd.DataFrame()

    df = pd.DataFrame(bills)

    # Standardize numeric columns so downstream math is reliable.
    numeric_cols = ["subtotal", "tax_amount", "total_amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Parse dates into a dedicated datetime column for time series views.
    if "purchase_date" in df.columns:
        df["purchase_date_dt"] = pd.to_datetime(
            df["purchase_date"], errors="coerce"
        )

    return df


# KPI METRICS
def calculate_kpis(df: pd.DataFrame) -> dict:
    """
    Calculate dashboard KPIs.
    """
    if df.empty:
        return {}

    total_spent = df["total_amount"].sum()
    transactions = len(df)
    avg_transaction = total_spent / transactions if transactions else 0
    vendors_count = df["vendor_name"].nunique()

    # Fall back to 1 month to avoid divide-by-zero when dates are missing.
    months_active = df["purchase_date_dt"].dt.to_period("M").nunique() or 1
    avg_per_month = total_spent / months_active

    return {
        "total_spent": total_spent,
        "transactions": transactions,
        "avg_transaction": avg_transaction,
        "vendors_count": vendors_count,
        "avg_per_month": avg_per_month,
    }


# MONTHLY ANALYTICS

def monthly_spending(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate total spending per month.
    """
    if df.empty:
        return pd.DataFrame()

    monthly = (
        df.dropna(subset=["purchase_date_dt"])
        .groupby(df["purchase_date_dt"].dt.to_period("M"))["total_amount"]
        .sum()
        .reset_index()
    )

    # Keep a formatted month label for chart axes.
    monthly["month"] = monthly["purchase_date_dt"].dt.strftime("%Y-%m")
    return monthly


def monthly_transaction_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count number of bills per month.
    """
    if df.empty:
        return pd.DataFrame()

    monthly_counts = (
        df.dropna(subset=["purchase_date_dt"])
        .groupby(df["purchase_date_dt"].dt.to_period("M"))
        .size()
        .reset_index(name="transactions")
    )

    # Keep a formatted month label for chart axes.
    monthly_counts["month"] = monthly_counts["purchase_date_dt"].dt.strftime("%Y-%m")
    return monthly_counts


def monthly_tax_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly subtotal and tax breakdown.
    """
    if df.empty:
        return pd.DataFrame()

    # Aggregate by calendar month using the parsed datetime column.
    monthly = (
        df.dropna(subset=["purchase_date_dt"])
        .groupby(df["purchase_date_dt"].dt.to_period("M"))
        .agg({
            "total_amount": "sum",
            "tax_amount": "sum"
        })
        .reset_index()
    )

    # Keep a formatted month label for chart axes.
    monthly["month"] = monthly["purchase_date_dt"].dt.strftime("%Y-%m")
    monthly["subtotal"] = monthly["total_amount"] - monthly["tax_amount"]
    monthly["tax_percentage"] = (
        (monthly["tax_amount"] / monthly["total_amount"]) * 100
    ).round(2)

    return monthly


# VENDOR ANALYTICS
def top_vendors(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Top vendors by total spend.
    """
    if df.empty:
        return pd.DataFrame()

    vendor_df = (
        df.groupby("vendor_name")
        .agg({
            "total_amount": ["sum", "count", "mean"]
        })
        .reset_index()
    )

    # Flatten the MultiIndex columns created by the aggregation.
    vendor_df.columns = [
        "vendor_name",
        "total_spent",
        "transactions",
        "avg_per_bill",
    ]

    return vendor_df.sort_values(
        "total_spent", ascending=False
    ).head(top_n)


# PAYMENT METHOD ANALYTICS

def payment_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Spending by payment method.
    """
    if df.empty or "payment_method" not in df.columns:
        return pd.DataFrame()

    return (
        df[df["payment_method"].notna()]
        .groupby("payment_method")["total_amount"]
        .sum()
        .reset_index()
    )


# HIGH VALUE TRANSACTIONS

def high_value_transactions(df: pd.DataFrame, threshold: float = 100.0) -> pd.DataFrame:
    """
    Return bills above given threshold.
    """
    if df.empty:
        return pd.DataFrame()

    return df[df["total_amount"] >= threshold].sort_values(
        "total_amount", ascending=False
    )


# ITEM LEVEL ANALYTICS
def prepare_items_dataframe(items: list) -> pd.DataFrame:
    """
    Convert items list to cleaned DataFrame.
    """
    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)

    numeric_cols = ["quantity", "unit_price", "item_total"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def top_items_by_spend(items_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Top items by total spending.
    """
    if items_df.empty:
        return pd.DataFrame()

    result = (
        items_df.groupby("item_name")["item_total"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )

    return result


def most_frequent_items(items_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Most frequently purchased items.
    """
    if items_df.empty:
        return pd.DataFrame()

    result = (
        items_df.groupby("item_name")
        .size()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index(name="purchase_count")
    )

    return result
