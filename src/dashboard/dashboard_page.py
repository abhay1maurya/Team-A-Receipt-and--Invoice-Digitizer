"""Dashboard page module.

Provides the main spending analytics view, including cached data loading,
summary KPIs, filters, and detailed bill tables for interactive exploration.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.database import get_all_bills, get_bill_items


@st.cache_data(ttl=60, show_spinner=False)
def _cached_bills():
    """Fetch all bills from the database with a short-lived cache.

    Returns:
        List of bill dictionaries, or an empty list on failure.
    """
    try:
        return get_all_bills() or []
    except Exception as exc:
        st.warning(f"Could not load bills: {exc}")
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _cached_items(bills):
    """Fetch line items for each bill and enrich with bill metadata.

    Args:
        bills: List of bill dictionaries with id and metadata fields.

    Returns:
        List of line item dictionaries including bill metadata.
    """
    items = []
    for bill in bills:
        try:
            bill_items = get_bill_items(bill.get("id"))
        except Exception:
            bill_items = []
        for item in bill_items:
            items.append(
                {
                    **item,
                    "bill_id": bill.get("id"),
                    "vendor_name": bill.get("vendor_name"),
                    "purchase_date": bill.get("purchase_date"),
                }
            )
    return items


def page_dashboard():
    """Render the main spending dashboard with metrics, filters, and tables.

    Builds the UI layout, computes KPI summaries, applies filters, and shows
    filtered bill data with guidance when no results are available.
    """

    # Basic styling for KPI cards.
    st.markdown(
        """
        <style>
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Page title and subtitle.
    st.markdown(
        "<h1 style='color: #2c3e50;'>📊 Financial Dashboard</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #7f8c8d; font-size: 1.1rem;'>"
        "Comprehensive insights into your spending patterns</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # Load cached bills data.
    bills = _cached_bills()
    if not bills:
        st.markdown(
            """
            <div style='text-align: center; padding: 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 10px; color: white;'>
                <h2>📭 No Data Available</h2>
                <p style='font-size: 1.2rem;'>Upload and save your first bill to unlock powerful insights!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Normalize bills to a DataFrame and parse dates.
    bills_df = pd.DataFrame(bills)
    bills_df["purchase_date_dt"] = pd.to_datetime(
        bills_df.get("purchase_date"), errors="coerce"
    )

    # Aggregate headline metrics.
    total_spent = bills_df["total_amount"].sum()
    months_active = bills_df["purchase_date_dt"].dt.to_period("M").nunique() or 1
    avg_per_month = total_spent / months_active
    vendors_count = bills_df["vendor_name"].nunique()
    transactions_count = len(bills_df)
    avg_transaction = total_spent / transactions_count if transactions_count > 0 else 0

    # Compute current and previous month windows.
    current_month = datetime.now().replace(day=1)
    prev_month = (current_month - timedelta(days=1)).replace(day=1)

    current_month_data = bills_df[bills_df["purchase_date_dt"] >= current_month]
    prev_month_data = bills_df[
        (bills_df["purchase_date_dt"] >= prev_month)
        & (bills_df["purchase_date_dt"] < current_month)
    ]

    current_month_spend = current_month_data["total_amount"].sum()
    prev_month_spend = prev_month_data["total_amount"].sum()

    spend_delta = current_month_spend - prev_month_spend
    spend_delta_pct = (
        (spend_delta / prev_month_spend * 100) if prev_month_spend > 0 else 0
    )

    # KPI cards for quick insights.
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="💰 Total Spend",
            value=f"${total_spent:,.2f}",
            delta=f"{spend_delta_pct:+.1f}% vs last month" if prev_month_spend > 0 else None,
        )
    with col2:
        bill_delta = len(current_month_data) - len(prev_month_data)
        st.metric(
            label="🧾 Total Bills",
            value=str(transactions_count),
            delta=f"{bill_delta:+d} this month" if len(prev_month_data) > 0 else None,
        )
    with col3:
        st.metric(label="💵 Avg Bill Value", value=f"${avg_transaction:,.2f}")
    with col4:
        st.metric(label="🏪 Unique Vendors", value=str(vendors_count))
    with col5:
        st.metric(label="📊 Monthly Avg", value=f"${avg_per_month:,.2f}")

    st.divider()

    # Filter controls for date, vendor, amount, and payment method.
    st.markdown("### 🔍 Smart Filters")

    preset_col, custom_col = st.columns([1, 3])
    with preset_col:
        date_preset = st.selectbox(
            "Quick Select",
            [
                "Custom Range",
                "Last 7 Days",
                "Last 30 Days",
                "Last 3 Months",
                "Last 6 Months",
                "This Year",
                "All Time",
            ],
            key="date_preset",
        )

    # Translate date presets into concrete ranges.
    if date_preset == "Last 7 Days":
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
    elif date_preset == "Last 30 Days":
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
    elif date_preset == "Last 3 Months":
        start_date = datetime.now() - timedelta(days=90)
        end_date = datetime.now()
    elif date_preset == "Last 6 Months":
        start_date = datetime.now() - timedelta(days=180)
        end_date = datetime.now()
    elif date_preset == "This Year":
        start_date = datetime.now().replace(month=1, day=1)
        end_date = datetime.now()
    elif date_preset == "All Time":
        start_date = bills_df["purchase_date_dt"].min()
        end_date = bills_df["purchase_date_dt"].max()
    else:
        start_date = bills_df["purchase_date_dt"].min()
        end_date = bills_df["purchase_date_dt"].max()

    # Filter widgets laid out in four columns.
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        if date_preset == "Custom Range":
            date_range = st.date_input(
                "📅 Date Range",
                value=(
                    bills_df["purchase_date_dt"].min().date(),
                    bills_df["purchase_date_dt"].max().date(),
                ),
                key="date_range_filter",
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
        else:
            st.markdown("**📅 Date Range**")
            st.caption(f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    with filter_col2:
        all_vendors = ["All Vendors"] + sorted(
            bills_df["vendor_name"].dropna().unique().tolist()
        )
        selected_vendor = st.selectbox("🏪 Vendor", options=all_vendors, key="vendor_filter")

    with filter_col3:
        min_amount = bills_df["total_amount"].min()
        max_amount = bills_df["total_amount"].max()
        amount_range = st.slider(
            "💵 Amount Range ($)",
            min_value=float(min_amount),
            max_value=float(max_amount),
            value=(float(min_amount), float(max_amount)),
            step=10.0,
            key="amount_filter",
        )

    with filter_col4:
        payment_methods = bills_df[bills_df["payment_method"].notna()][
            "payment_method"
        ].unique().tolist()
        all_payments = ["All Methods"] + sorted(payment_methods)
        selected_payment = st.selectbox(
            "💳 Payment Method", options=all_payments, key="payment_filter"
        )

    # Apply the active filters to the bills data.
    filtered_df = bills_df[
        (bills_df["purchase_date_dt"] >= start_date)
        & (bills_df["purchase_date_dt"] <= end_date)
        & (bills_df["total_amount"] >= amount_range[0])
        & (bills_df["total_amount"] <= amount_range[1])
    ].copy()

    if selected_vendor != "All Vendors":
        filtered_df = filtered_df[filtered_df["vendor_name"] == selected_vendor]

    if selected_payment != "All Methods":
        filtered_df = filtered_df[filtered_df["payment_method"] == selected_payment]

    # Filter summary and callout.
    summary_col1, summary_col2 = st.columns([3, 1])
    with summary_col1:
        if len(filtered_df) < len(bills_df):
            st.success(
                f"✅ Showing **{len(filtered_df)}** of **{len(bills_df)}** bills | "
                f"Total: **${filtered_df['total_amount'].sum():,.2f}**"
            )
        else:
            st.info(
                f"📊 Showing all **{len(bills_df)}** bills | "
                f"Total: **${filtered_df['total_amount'].sum():,.2f}**"
            )

    with summary_col2:
        st.markdown("")

    # Stop early when filters produce no results.
    if filtered_df.empty:
        st.warning("⚠️ No data matches your current filters. Try adjusting the filter criteria.")
        return

    st.divider()
