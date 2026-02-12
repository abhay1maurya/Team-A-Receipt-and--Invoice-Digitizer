"""Insight helpers for dashboard charts.

This module returns short, user-friendly sentences derived from chart data.
It contains no Streamlit or plotting code.
"""

import pandas as pd
from typing import Optional


# Small formatting helpers to keep insight text consistent.


def _format_currency(value: float, decimals: int = 2) -> str:
	return f"${value:,.{decimals}f}"


def _safe_pct(part: float, total: float) -> float:
	return (part / total * 100) if total else 0.0


def monthly_spending_insight(monthly_df: pd.DataFrame) -> Optional[str]:
	if monthly_df.empty or "total_amount" not in monthly_df.columns:
		return None

	# Highlight the peak month and compare the most recent month to the prior one.
	df = monthly_df.sort_values("month")
	top_row = df.loc[df["total_amount"].idxmax()]
	insight = (
		f"Highest spending month: {top_row['month']} at "
		f"{_format_currency(top_row['total_amount'])}."
	)

	if len(df) >= 2:
		last = df.iloc[-1]["total_amount"]
		prev = df.iloc[-2]["total_amount"]
		delta = last - prev
		if prev > 0:
			trend = "up" if delta > 0 else "down" if delta < 0 else "flat"
			insight += f" Last month is {trend} {abs(delta / prev * 100):.1f}% vs prior month."
		elif delta != 0:
			insight += f" Last month changed by {_format_currency(delta)} vs prior month."

	return insight


def monthly_transactions_insight(monthly_counts_df: pd.DataFrame) -> Optional[str]:
	if monthly_counts_df.empty or "transactions" not in monthly_counts_df.columns:
		return None

	# Point out the busiest month and typical monthly volume.
	df = monthly_counts_df.sort_values("month")
	top_row = df.loc[df["transactions"].idxmax()]
	avg = df["transactions"].mean()
	return (
		f"Busiest month: {top_row['month']} with {int(top_row['transactions'])} bills. "
		f"Average volume is {avg:.1f} bills per month."
	)


def tax_vs_subtotal_insight(monthly_tax_df: pd.DataFrame) -> Optional[str]:
	if monthly_tax_df.empty or "tax_amount" not in monthly_tax_df.columns:
		return None

	# Summarize the overall tax rate and the peak tax month when available.
	total_tax = monthly_tax_df["tax_amount"].sum()
	total_amount = monthly_tax_df["total_amount"].sum()
	avg_rate = _safe_pct(total_tax, total_amount)

	if "tax_percentage" in monthly_tax_df.columns:
		top_row = monthly_tax_df.loc[monthly_tax_df["tax_percentage"].idxmax()]
		return (
			f"Average tax rate is {avg_rate:.1f}%. "
			f"Highest tax share was {top_row['tax_percentage']:.1f}% in {top_row['month']}."
		)

	return f"Average tax rate is {avg_rate:.1f}%."


def cumulative_spending_insight(monthly_df: pd.DataFrame) -> Optional[str]:
	if monthly_df.empty or "total_amount" not in monthly_df.columns:
		return None

	# Give a snapshot of total and average monthly spend.
	total = monthly_df["total_amount"].sum()
	avg = monthly_df["total_amount"].mean()
	return (
		f"Total spend to date is {_format_currency(total)} "
		f"with an average of {_format_currency(avg)} per month."
	)


def yoy_insight(df: pd.DataFrame) -> Optional[str]:
	if df.empty or "purchase_date_dt" not in df.columns:
		return None

	# Only report if we have at least two years of data.
	data = df.dropna(subset=["purchase_date_dt"]).copy()
	data["year"] = data["purchase_date_dt"].dt.year
	yearly = data.groupby("year")["total_amount"].sum().reset_index()

	if yearly["year"].nunique() < 2:
		return None

	top_year = yearly.loc[yearly["total_amount"].idxmax()]
	return f"Strongest year is {int(top_year['year'])} at {_format_currency(top_year['total_amount'])}."


def vendor_insight(vendor_df: pd.DataFrame) -> Optional[str]:
	if vendor_df.empty or "total_spent" not in vendor_df.columns:
		return None

	# Emphasize the top vendor and its share of total spend.
	total = vendor_df["total_spent"].sum()
	top_row = vendor_df.loc[vendor_df["total_spent"].idxmax()]
	share = _safe_pct(top_row["total_spent"], total)
	return (
		f"Top vendor is {top_row['vendor_name']} at {_format_currency(top_row['total_spent'])} "
		f"({share:.1f}% of spend)."
	)


def payment_insight(payment_df: pd.DataFrame) -> Optional[str]:
	if payment_df.empty or "total_amount" not in payment_df.columns:
		return None

	# Emphasize the most used payment method and its share.
	total = payment_df["total_amount"].sum()
	top_row = payment_df.loc[payment_df["total_amount"].idxmax()]
	share = _safe_pct(top_row["total_amount"], total)
	return (
		f"Most used method is {top_row['payment_method']} at {_format_currency(top_row['total_amount'])} "
		f"({share:.1f}% of spend)."
	)


def transaction_histogram_insight(df: pd.DataFrame) -> Optional[str]:
	if df.empty or "total_amount" not in df.columns:
		return None

	# Use median and mean to summarize typical bill size.
	mean_val = df["total_amount"].mean()
	median_val = df["total_amount"].median()
	return (
		f"Typical bill is around {_format_currency(median_val)} with an average of "
		f"{_format_currency(mean_val)}."
	)


def day_of_week_insight(df: pd.DataFrame) -> Optional[str]:
	if df.empty or "purchase_date_dt" not in df.columns:
		return None

	# Identify the day with the highest total spend.
	data = df.dropna(subset=["purchase_date_dt"]).copy()
	data["day_name"] = data["purchase_date_dt"].dt.day_name()
	day_totals = data.groupby("day_name")["total_amount"].sum()
	if day_totals.empty:
		return None

	top_day = day_totals.idxmax()
	top_total = day_totals.max()
	return f"Highest spend day is {top_day} at {_format_currency(top_total)}."


def top_items_insight(items_df: pd.DataFrame) -> Optional[str]:
	if items_df.empty or "item_total" not in items_df.columns:
		return None

	# Call out the single largest contributor to item spend.
	total = items_df["item_total"].sum()
	top_row = items_df.loc[items_df["item_total"].idxmax()]
	share = _safe_pct(top_row["item_total"], total)
	return (
		f"Top item by spend is {top_row['item_name']} at {_format_currency(top_row['item_total'])} "
		f"({share:.1f}% of item spend)."
	)


def frequent_items_insight(freq_df: pd.DataFrame) -> Optional[str]:
	if freq_df.empty or "purchase_count" not in freq_df.columns:
		return None

	# Call out the most frequently purchased item and its share of counts.
	total = freq_df["purchase_count"].sum()
	top_row = freq_df.loc[freq_df["purchase_count"].idxmax()]
	share = _safe_pct(top_row["purchase_count"], total)
	return (
		f"Most purchased item is {top_row['item_name']} with {int(top_row['purchase_count'])} purchases "
		f"({share:.1f}% of item counts)."
	)
