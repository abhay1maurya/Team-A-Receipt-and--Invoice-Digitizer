"""Dashboard page module.

Provides the main spending analytics view, including cached data loading,
summary KPIs, filters, and detailed bill tables for interactive exploration.

Data flow overview:
- Load cached bills and items from the database.
- Normalize bills into a DataFrame with parsed dates.
- Compute KPIs and month-over-month deltas.
- Apply user filters to build focused views and charts.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.database import get_all_bills, get_bill_items
from src.dashboard import analytics as dashboard_analytics
from src.dashboard import charts as dashboard_charts


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

    This function is intentionally UI-focused and delegates data logic to
    src.dashboard.analytics and chart rendering to src.dashboard.charts.
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

    # Normalize bills to a DataFrame and parse dates for time-based analysis.
    bills_df = dashboard_analytics.prepare_bills_dataframe(bills)

    # Aggregate headline metrics used by KPI cards.
    kpis = dashboard_analytics.calculate_kpis(bills_df)
    total_spent = kpis.get("total_spent", 0)
    transactions_count = kpis.get("transactions", 0)
    avg_transaction = kpis.get("avg_transaction", 0)
    vendors_count = kpis.get("vendors_count", 0)
    avg_per_month = kpis.get("avg_per_month", 0)

    # Compute current and previous month windows.
    current_month = datetime.now().replace(day=1)
    prev_month = (current_month - timedelta(days=1)).replace(day=1)

    # Split the dataset into current and previous month windows for deltas.
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

    # KPI cards for quick insights, with deltas vs previous month.
    current_month_bills = len(current_month_data)
    prev_month_bills = len(prev_month_data)
    current_avg_bill = (
        current_month_data["total_amount"].mean() if current_month_bills else 0
    )
    prev_avg_bill = (
        prev_month_data["total_amount"].mean() if prev_month_bills else 0
    )
    current_vendor_count = current_month_data["vendor_name"].nunique()
    prev_vendor_count = prev_month_data["vendor_name"].nunique()

    current_month_median = (
        current_month_data["total_amount"].median() if current_month_bills else 0
    )
    prev_month_median = (
        prev_month_data["total_amount"].median() if prev_month_bills else 0
    )
    current_month_max = (
        current_month_data["total_amount"].max() if current_month_bills else 0
    )
    prev_month_max = (
        prev_month_data["total_amount"].max() if prev_month_bills else 0
    )
    current_month_tax_rate = (
        (current_month_data["tax_amount"].sum() / current_month_spend * 100)
        if current_month_spend > 0
        else 0
    )
    prev_month_tax_rate = (
        (prev_month_data["tax_amount"].sum() / prev_month_spend * 100)
        if prev_month_spend > 0
        else 0
    )

    bill_delta = current_month_bills - prev_month_bills
    avg_bill_delta = current_avg_bill - prev_avg_bill
    vendor_delta = current_vendor_count - prev_vendor_count
    median_delta = current_month_median - prev_month_median
    max_delta = current_month_max - prev_month_max
    tax_rate_delta = current_month_tax_rate - prev_month_tax_rate

    avg_bill_delta_pct = (
        (avg_bill_delta / prev_avg_bill * 100) if prev_avg_bill > 0 else None
    )
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="💰 Total Spend",
            value=f"${total_spent:,.2f}",
            delta=(
                f"{spend_delta_pct:+.1f}% vs last month"
                if prev_month_spend > 0
                else f"${spend_delta:,.2f} vs last month"
            ),
            delta_color="inverse",
        )
    with col2:
        st.metric(
            label="🧾 Total Bills",
            value=str(transactions_count),
            delta=f"{bill_delta:+d} vs last month",
        )
    with col3:
        st.metric(
            label="💵 Avg Bill Value",
            value=f"${avg_transaction:,.2f}",
            delta=(
                f"{avg_bill_delta_pct:+.1f}% vs last month"
                if avg_bill_delta_pct is not None
                else f"${avg_bill_delta:,.2f} vs last month"
            ),
            delta_color="inverse",
        )
    with col4:
        st.metric(
            label="🏪 Unique Vendors",
            value=str(vendors_count),
            delta=f"{vendor_delta:+d} vs last month",
        )
    with col5:
        st.metric(label="📊 Monthly Avg", value=f"${avg_per_month:,.2f}")

    # Quick insights summary for non-technical users.
    insights = []
    if spend_delta > 0:
        insights.append(f"Spending is up ${spend_delta:,.0f} vs last month.")
    elif spend_delta < 0:
        insights.append(f"Spending is down ${abs(spend_delta):,.0f} vs last month.")
    if bill_delta != 0:
        insights.append(f"You have {bill_delta:+d} bills compared to last month.")
    if vendor_delta != 0:
        insights.append(f"You visited {vendor_delta:+d} vendors compared to last month.")

    if insights:
        st.info("  ".join(insights[:3]))

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

    # Charts and Analytics
    st.markdown("### 📊 Insights & Trends")

    monthly_df = dashboard_analytics.monthly_spending(filtered_df)
    monthly_tax_df = dashboard_analytics.monthly_tax_breakdown(filtered_df)
    monthly_counts_df = dashboard_analytics.monthly_transaction_counts(filtered_df)
    vendor_df = dashboard_analytics.top_vendors(filtered_df)
    payment_df = dashboard_analytics.payment_distribution(filtered_df)

    # Tabbed chart sections for simpler navigation
    # Segment charts by theme to keep the page scannable.
    tab_overview, tab_vendors, tab_patterns, tab_items = st.tabs([
        "📌 Overview",
        "🏪 Vendors & Payments",
        "📅 Spending Patterns",
        "🧾 Item Insights",
    ])

    # ---- TAB 1: Overview ----
    with tab_overview:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            if not monthly_df.empty:
                st.plotly_chart(
                    dashboard_charts.monthly_spending_line(monthly_df),
                    width='content',
                )
                st.caption("Total spending by month. Look for peaks to spot high-cost periods.")
            else:
                st.info("No monthly spending data available for this range.")
        with chart_col2:
            if not monthly_counts_df.empty:
                st.plotly_chart(
                    dashboard_charts.monthly_transactions_bar(monthly_counts_df),
                    width='content',
                )
                st.caption("How many bills you had each month.")
            else:
                st.info("No monthly bill count data available for this range.")

        chart_col_a, chart_col_b = st.columns(2)
        with chart_col_a:
            if not monthly_tax_df.empty:
                st.plotly_chart(
                    dashboard_charts.tax_vs_subtotal_bar(monthly_tax_df),
                    width='content',
                )
                st.caption("Breakdown of subtotal vs tax for each month.")
        with chart_col_b:
            if not monthly_df.empty:
                st.plotly_chart(
                    dashboard_charts.cumulative_spending_line(monthly_df),
                    width='content',
                )
                st.caption("Running total of spending over time.")

        # Year-over-year (only shows if data spans multiple years)
        yoy_fig = dashboard_charts.yoy_comparison(filtered_df)
        if yoy_fig.data:
            st.plotly_chart(yoy_fig, width='content')
            st.caption("Compare the same months across different years.")

    # ---- TAB 2: Vendors & Payments ----
    with tab_vendors:
        chart_col3, chart_col4 = st.columns(2)
        with chart_col3:
            if not vendor_df.empty:
                st.plotly_chart(
                    dashboard_charts.vendor_bar_chart(vendor_df),
                    width='content',
                )
                st.caption("Top vendors by total spending.")
            else:
                st.info("No vendor data available for this range.")
        with chart_col4:
            if not vendor_df.empty:
                st.plotly_chart(
                    dashboard_charts.vendor_pie_chart(vendor_df),
                    width='content',
                )
                st.caption("Share of spending by vendor.")

        chart_col_e, chart_col_f = st.columns(2)
        with chart_col_e:
            if not payment_df.empty:
                st.plotly_chart(
                    dashboard_charts.payment_method_bar(payment_df),
                    width='content',
                )
                st.caption("Total spending by payment method.")
            else:
                st.info("No payment method data available for this range.")
        with chart_col_f:
            if not payment_df.empty:
                st.plotly_chart(
                    dashboard_charts.payment_method_pie(payment_df),
                    width='content',
                )
                st.caption("Payment method share of total spending.")

    # ---- TAB 3: Spending Patterns ----
    with tab_patterns:
        chart_col5, chart_col6 = st.columns(2)
        with chart_col5:
            st.plotly_chart(
                dashboard_charts.transaction_histogram(filtered_df),
                width='content',
            )
            st.caption("Distribution of bill sizes. Most bills cluster near the center.")
        with chart_col6:
            st.plotly_chart(
                dashboard_charts.day_of_week_bar(filtered_df),
                width='content',
            )
            st.caption("Total spending by day of the week.")

    # ---- TAB 4: Item Insights ----
    with tab_items:
        all_items = _cached_items(bills)
        items_df = dashboard_analytics.prepare_items_dataframe(all_items)
        if not items_df.empty and "bill_id" in items_df.columns and "id" in filtered_df.columns:
            items_df = items_df[items_df["bill_id"].isin(filtered_df["id"])].copy()

        top_items_df = dashboard_analytics.top_items_by_spend(items_df)
        frequent_items_df = dashboard_analytics.most_frequent_items(items_df)

        item_col1, item_col2 = st.columns(2)
        with item_col1:
            if not top_items_df.empty:
                st.plotly_chart(
                    dashboard_charts.top_items_bar(top_items_df),
                    width='content',
                )
                st.caption("Items that cost the most overall.")
            else:
                st.info("No item spend data available for this range.")
        with item_col2:
            if not frequent_items_df.empty:
                st.plotly_chart(
                    dashboard_charts.frequent_items_bar(frequent_items_df),
                    width='content',
                )
                st.caption("Items you buy most often.")
            else:
                st.info("No item frequency data available for this range.")
