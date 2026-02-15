"""Gemini-powered insight generation for the dashboard.

This module prepares compact summaries of the user's data and asks Gemini
to produce concise, user-friendly insights and actions.
"""

from __future__ import annotations

from typing import Dict, Any, List
import hashlib
import json
from textwrap import dedent

import pandas as pd
from google import genai


def _safe_float(value: Any) -> float:
	try:
		converted = float(value)
		return 0.0 if pd.isna(converted) else converted
	except (TypeError, ValueError):
		return 0.0


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
	if df is None or column not in df.columns:
		return pd.Series(dtype="float64")
	return pd.to_numeric(df[column], errors="coerce")


def _count_missing(df: pd.DataFrame, column: str) -> int:
	if df is None or column not in df.columns:
		return 0
	return int(df[column].isna().sum())


def _pct(part: float, total: float) -> float:
	if not total:
		return 0.0
	return (part / total) * 100


def build_summary(
	bills_df: pd.DataFrame,
	vendor_df: pd.DataFrame,
	payment_df: pd.DataFrame,
	items_df: pd.DataFrame,
	top_n: int = 5,
) -> Dict[str, Any]:
	"""Build a compact, serializable summary for AI insight generation."""
	summary: Dict[str, Any] = {
		"totals": {},
		"date_range": {},
		"top_vendors": [],
		"top_payments": [],
		"top_items": [],
		"frequent_items": [],
		"data_quality": {},
	}

	if bills_df is None or bills_df.empty:
		return summary

	amounts = _numeric_series(bills_df, "total_amount")
	vendor_names = bills_df["vendor_name"] if "vendor_name" in bills_df.columns else None
	payment_methods = bills_df["payment_method"] if "payment_method" in bills_df.columns else None

	totals = {
		"total_spend": _safe_float(amounts.sum()),
		"transactions": int(len(bills_df)),
		"avg_bill": _safe_float(amounts.mean()),
		"median_bill": _safe_float(amounts.median()),
		"max_bill": _safe_float(amounts.max()),
		"vendors": int(vendor_names.nunique()) if vendor_names is not None else 0,
	}
	summary["totals"] = totals

	if "purchase_date_dt" in bills_df.columns:
		min_date = bills_df["purchase_date_dt"].min()
		max_date = bills_df["purchase_date_dt"].max()
		summary["date_range"] = {
			"start": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
			"end": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
		}

	if vendor_df is not None and not vendor_df.empty:
		total_spend = totals.get("total_spend", 0.0)
		for _, row in vendor_df.head(top_n).iterrows():
			spent = _safe_float(row.get("total_spent"))
			summary["top_vendors"].append(
				{
					"name": str(row.get("vendor_name") or ""),
					"spend": spent,
					"share_pct": round(_pct(spent, total_spend), 1),
				}
			)

	if payment_df is not None and not payment_df.empty:
		total_spend = totals.get("total_spend", 0.0)
		for _, row in payment_df.head(top_n).iterrows():
			spent = _safe_float(row.get("total_amount"))
			summary["top_payments"].append(
				{
					"method": str(row.get("payment_method") or ""),
					"spend": spent,
					"share_pct": round(_pct(spent, total_spend), 1),
				}
			)

	if items_df is not None and not items_df.empty:
		if "item_total" in items_df.columns and "item_name" in items_df.columns:
			item_spend = (
				items_df.groupby("item_name")["item_total"]
				.sum()
				.sort_values(ascending=False)
				.head(top_n)
			)
			total_item_spend = _safe_float(pd.to_numeric(items_df["item_total"], errors="coerce").sum())
			for name, spent in item_spend.items():
				summary["top_items"].append(
					{
						"name": str(name or ""),
						"spend": _safe_float(spent),
						"share_pct": round(_pct(_safe_float(spent), total_item_spend), 1),
					}
				)

		if "item_name" in items_df.columns:
			item_freq = (
				items_df.groupby("item_name")
				.size()
				.sort_values(ascending=False)
				.head(top_n)
			)
			total_item_count = int(items_df.shape[0])
			for name, count in item_freq.items():
				summary["frequent_items"].append(
					{
						"name": str(name or ""),
						"count": int(count),
						"share_pct": round(_pct(int(count), total_item_count), 1),
					}
				)

	summary["data_quality"] = {
		"missing_payment_method": _count_missing(bills_df, "payment_method"),
		"missing_vendor_name": _count_missing(bills_df, "vendor_name"),
	}

	return summary


def summary_hash(summary: Dict[str, Any]) -> str:
	"""Create a stable hash of the summary for cache/session comparisons."""
	payload = json.dumps(summary, sort_keys=True, default=str).encode("utf-8")
	return hashlib.sha256(payload).hexdigest()


def generate_ai_insights(summary: Dict[str, Any], api_key: str) -> Dict[str, Any]:
	"""Generate insights using Gemini based on the provided summary."""
	if not api_key or not api_key.strip():
		return {"error": "API key is required to generate AI insights."}

	if not summary or not summary.get("totals"):
		return {"error": "Not enough data to generate insights."}

	client = genai.Client(api_key=api_key)

	prompt = dedent(
		"""
		You are a spending analytics assistant.
		Use ONLY the provided JSON summary to write insights.
		Return polished Markdown with the exact section headers and emojis below:
		## ✨ AI Insights
		## 🔎 Key Patterns
		## ⚠️ Risk/Anomaly Flags
		## ✅ Action Plan
		## 🧾 Data Quality Notes
		Style rules:
		- Under each section, add a 1-line italic lead-in sentence.
		- Then use bullet points with bold labels followed by an em dash and 2 to 4 sentences.
		- Use subtle separators like '---' between sections.
		- Keep formatting clean and easy to scan (no tables).
		- Keep tone confident, concise, and visually appealing.
		Length and detail:
		- AI Insights: 8 to 12 bullets
		- Key Patterns: 5 to 8 bullets
		- Risk/Anomaly Flags: 3 to 6 bullets
		- Action Plan: 6 to 10 bullets
		- Data Quality Notes: 2 to 4 bullets
		Guardrails:
		- Do not add new numbers or speculate beyond the data.
		- If a section has insufficient data, write a single bullet saying 'Not enough data.'

		Summary JSON:
		"""
	).strip() + f"\n{json.dumps(summary, sort_keys=True)}"

	try:
		response = client.models.generate_content(
			model="gemini-2.5-flash",
			contents=[prompt],
			config={
				"temperature": 0.2,
				"max_output_tokens": 3200,
			},
		)
	except Exception as exc:
		return {"error": f"Gemini request failed: {exc}"}

	text = (response.text or "").strip()
	if not text:
		return {"error": "Gemini returned an empty response."}

	return {"text": text}
