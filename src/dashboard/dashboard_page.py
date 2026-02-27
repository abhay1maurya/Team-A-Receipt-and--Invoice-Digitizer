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
import re

from src.database import get_all_bills, get_bill_items
from src.dashboard import analytics as dashboard_analytics
from src.dashboard import charts as dashboard_charts
from src.dashboard import insights as dashboard_insights
from src.dashboard import ai_insights as dashboard_ai_insights

from src.database import get_monthly_spending
from src.database import get_filtered_bills


import time


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


def _render_ai_insights(markdown_text: str) -> None:
    """Render AI insights with enhanced styling using simple markdown-to-HTML rules."""
    if not markdown_text:
        return

    html_lines = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    def format_inline(text: str) -> str:
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        return text

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            close_list()
            html_lines.append("<div class='ai-gap'></div>")
            continue

        if line.startswith("## "):
            close_list()
            title = format_inline(line[3:])
            html_lines.append(f"<h2 class='ai-section-title'>{title}</h2>")
            continue

        if line == "---":
            close_list()
            html_lines.append("<hr class='ai-divider' />")
            continue

        if line.startswith("-"):
            if not in_list:
                html_lines.append("<ul class='ai-list'>")
                in_list = True
            item = format_inline(line[1:].strip())
            html_lines.append(f"<li>{item}</li>")
            continue

        close_list()
        html_lines.append(f"<p class='ai-paragraph'>{format_inline(line)}</p>")

    close_list()

    html = "\n".join(html_lines)
    st.markdown(
        """
        <style>
        .ai-insights-card {
            background: linear-gradient(180deg, #ffffff 0%, #f6f8fb 100%);
            border: 1px solid #e6eaf0;
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
        }
        .ai-section-title {
            margin: 0.9rem 0 0.25rem 0;
            color: #1f2937;
            font-size: 1.15rem;
            letter-spacing: 0.2px;
        }
        .ai-paragraph {
            margin: 0.35rem 0 0.75rem 0;
            color: #374151;
            font-size: 0.95rem;
        }
        .ai-list {
            margin: 0.2rem 0 0.9rem 1rem;
            color: #374151;
        }
        .ai-list li {
            margin: 0.35rem 0;
            line-height: 1.45;
        }
        .ai-divider {
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 0.85rem 0;
        }
        .ai-gap {
            height: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='ai-insights-card'>{html}</div>", unsafe_allow_html=True)


def _inject_dashboard_styles() -> None:
    """Inject a cohesive visual theme for dashboard sections and cards."""
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at top right, #f8fbff 0%, #f4f7fb 40%, #f7f9fc 100%);
        }
        .stMetric {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid #e8edf5;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
        }
        .dashboard-section-title {
            display: inline-block;
            margin: 0.35rem 0 0.8rem 0;
            padding: 0.38rem 0.8rem;
            border-radius: 999px;
            background: #e8f0ff;
            color: #1e3a8a;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.2px;
        }
        .quick-insight-card {
            background: linear-gradient(145deg, #eff6ff 0%, #f8fbff 100%);
            border: 1px solid #dbeafe;
            border-radius: 12px;
            padding: 0.8rem 1rem;
            margin: 0.45rem 0 0.8rem 0;
            box-shadow: 0 6px 14px rgba(30, 58, 138, 0.08);
        }
        .quick-insight-title {
            color: #1d4ed8;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .quick-insight-list {
            margin: 0;
            padding-left: 1.15rem;
            color: #1f2937;
        }
        .insight-note {
            margin-top: 0.4rem;
            padding: 0.62rem 0.78rem;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.05);
            color: #334155;
            font-size: 0.92rem;
        }
        .insight-note strong {
            color: #0f172a;
        }
        .ai-tab-hero {
            background: linear-gradient(135deg, #1d4ed8 0%, #6d28d9 100%);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            color: #ffffff;
            box-shadow: 0 10px 24px rgba(29, 78, 216, 0.24);
            margin-bottom: 0.85rem;
        }
        .ai-tab-hero-title {
            margin: 0;
            font-weight: 700;
            font-size: 1.05rem;
        }
        .ai-tab-hero-subtitle {
            margin: 0.35rem 0 0 0;
            opacity: 0.95;
            font-size: 0.92rem;
            line-height: 1.45;
        }
        .ai-action-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border: 1px solid #dbeafe;
            border-radius: 12px;
            padding: 0.95rem;
            margin: 0.65rem 0 0.85rem 0;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
        }
        .ai-action-title {
            margin: 0 0 0.2rem 0;
            color: #1e40af;
            font-weight: 700;
        }
        .ai-action-subtitle {
            margin: 0;
            color: #475569;
            font-size: 0.9rem;
        }
        .ai-info-card {
            background: linear-gradient(180deg, #fffbeb 0%, #fef3c7 100%);
            border: 1px solid #fcd34d;
            border-radius: 10px;
            color: #7c2d12;
            padding: 0.75rem 0.9rem;
            margin: 0.6rem 0;
            font-size: 0.9rem;
        }
        .ai-refresh-hint {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
            margin-top: 0.6rem;
            font-size: 0.9rem;
        }
        div[data-baseweb="tab-list"] {
            background: #eef3fb;
            border-radius: 10px;
            padding: 0.2rem;
        }
        div[data-baseweb="tab-list"] button[role="tab"] {
            border-radius: 8px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_quick_insights(insights: list[str]) -> None:
    """Render a highlighted quick-insights card."""
    if not insights:
        return
    bullets = "".join([f"<li>{insight}</li>" for insight in insights[:3]])
    st.markdown(
        f"""
        <div class='quick-insight-card'>
            <div class='quick-insight-title'>⚡ Quick Insights</div>
            <ul class='quick-insight-list'>{bullets}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_insight_note(insight: str) -> None:
    """Render a compact styled insight note under a chart."""
    if not insight:
        return
    st.markdown(
        f"<div class='insight-note'><strong>Insight:</strong> {insight}</div>",
        unsafe_allow_html=True,
    )


def page_dashboard():
    """Render the main spending dashboard with metrics, filters, and tables.

    Builds the UI layout, computes KPI summaries, applies filters, and shows
    filtered bill data with guidance when no results are available.

    This function is intentionally UI-focused and delegates data logic to
    src.dashboard.analytics and chart rendering to src.dashboard.charts.
    """
    start = time.time()
    monthly_data = get_monthly_spending()
    print("Monthly query time:", time.time() - start)

    _inject_dashboard_styles()

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
    st.markdown("<div class='dashboard-section-title'>📈 Key Metrics</div>", unsafe_allow_html=True)
    template_parsing_count = sum(
        1 for bill in bills if bill.get("parsed_with_template")
    )
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
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
    with row1_col2:
        st.metric(
            label="🧾 Total Bills",
            value=str(transactions_count),
            delta=f"{bill_delta:+d} vs last month",
        )
    with row1_col3:
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
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        st.metric(
            label="🏪 Unique Vendors",
            value=str(vendors_count),
            delta=f"{vendor_delta:+d} vs last month",
        )
    with row2_col2:
        st.metric(label="📊 Monthly Avg", value=f"${avg_per_month:,.2f}")
    with row2_col3:
        st.metric(label="🧩 Template Parsed", value=str(template_parsing_count))

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

    _render_quick_insights(insights)

    st.divider()

    # Filter controls for date, vendor, amount, and payment method.
    st.markdown("<div class='dashboard-section-title'>🔍 Smart Filters</div>", unsafe_allow_html=True)

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

    # Filtering happens in SQL
    filtered_data = get_filtered_bills(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        min_amount=amount_range[0],
        max_amount=amount_range[1],
        vendor=selected_vendor,
        payment_method=selected_payment,
    )

    filtered_df = pd.DataFrame(filtered_data)

    if not filtered_df.empty:
        filtered_df["purchase_date_dt"] = pd.to_datetime(
            filtered_df["purchase_date"], errors="coerce"
        )




    

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
    st.markdown("<div class='dashboard-section-title'>📊 Insights & Trends</div>", unsafe_allow_html=True)

    # monthly_df = dashboard_analytics.monthly_spending(filtered_df)
    #  Now aggregation happens in SQL, not Pandas.
    monthly_data = get_monthly_spending()
    monthly_df = pd.DataFrame(monthly_data)

    monthly_tax_df = dashboard_analytics.monthly_tax_breakdown(filtered_df)
    monthly_counts_df = dashboard_analytics.monthly_transaction_counts(filtered_df)
    vendor_df = dashboard_analytics.top_vendors(filtered_df)
    payment_df = dashboard_analytics.payment_distribution(filtered_df)

    all_items = _cached_items(bills)
    items_df = dashboard_analytics.prepare_items_dataframe(all_items)
    if not items_df.empty and "bill_id" in items_df.columns and "id" in filtered_df.columns:
        items_df = items_df[items_df["bill_id"].isin(filtered_df["id"])].copy()

    # Tabbed chart sections for simpler navigation
    # Segment charts by theme to keep the page scannable.
    tab_overview, tab_vendors, tab_patterns, tab_items, tab_ai = st.tabs([
        "📌 Overview",
        "🏪 Vendors & Payments",
        "📅 Spending Patterns",
        "🧾 Item Insights",
        "🤖 AI Insights",
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
                insight = dashboard_insights.monthly_spending_insight(monthly_df)
                if insight:
                    _render_insight_note(insight)
            else:
                st.info("No monthly spending data available for this range.")
        with chart_col2:
            if not monthly_counts_df.empty:
                st.plotly_chart(
                    dashboard_charts.monthly_transactions_bar(monthly_counts_df),
                    width='content',
                )
                st.caption("How many bills you had each month.")
                insight = dashboard_insights.monthly_transactions_insight(monthly_counts_df)
                if insight:
                    _render_insight_note(insight)
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
                insight = dashboard_insights.tax_vs_subtotal_insight(monthly_tax_df)
                if insight:
                    _render_insight_note(insight)
        with chart_col_b:
            if not monthly_df.empty:
                st.plotly_chart(
                    dashboard_charts.cumulative_spending_line(monthly_df),
                    width='content',
                )
                st.caption("Running total of spending over time.")
                insight = dashboard_insights.cumulative_spending_insight(monthly_df)
                if insight:
                    _render_insight_note(insight)

        # Year-over-year (only shows if data spans multiple years)
        yoy_fig = dashboard_charts.yoy_comparison(filtered_df)
        if yoy_fig.data:
            st.plotly_chart(yoy_fig, width='content')
            st.caption("Compare the same months across different years.")
            insight = dashboard_insights.yoy_insight(filtered_df)
            if insight:
                _render_insight_note(insight)

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
                insight = dashboard_insights.vendor_insight(vendor_df)
                if insight:
                    _render_insight_note(insight)
            else:
                st.info("No vendor data available for this range.")
        with chart_col4:
            if not vendor_df.empty:
                st.plotly_chart(
                    dashboard_charts.vendor_pie_chart(vendor_df),
                    width='content',
                )
                st.caption("Share of spending by vendor.")
                insight = dashboard_insights.vendor_insight(vendor_df)
                if insight:
                    _render_insight_note(insight)

        chart_col_e, chart_col_f = st.columns(2)
        with chart_col_e:
            if not payment_df.empty:
                st.plotly_chart(
                    dashboard_charts.payment_method_bar(payment_df),
                    width='content',
                )
                st.caption("Total spending by payment method.")
                insight = dashboard_insights.payment_insight(payment_df)
                if insight:
                    _render_insight_note(insight)
            else:
                st.info("No payment method data available for this range.")
        with chart_col_f:
            if not payment_df.empty:
                st.plotly_chart(
                    dashboard_charts.payment_method_pie(payment_df),
                    width='content',
                )
                st.caption("Payment method share of total spending.")
                insight = dashboard_insights.payment_insight(payment_df)
                if insight:
                    _render_insight_note(insight)

    # ---- TAB 3: Spending Patterns ----
    with tab_patterns:
        chart_col5, chart_col6 = st.columns(2)
        with chart_col5:
            st.plotly_chart(
                dashboard_charts.transaction_histogram(filtered_df),
                width='content',
            )
            st.caption("Distribution of bill sizes. Most bills cluster near the center.")
            insight = dashboard_insights.transaction_histogram_insight(filtered_df)
            if insight:
                _render_insight_note(insight)
        with chart_col6:
            st.plotly_chart(
                dashboard_charts.day_of_week_bar(filtered_df),
                width='content',
            )
            st.caption("Total spending by day of the week.")
            insight = dashboard_insights.day_of_week_insight(filtered_df)
            if insight:
                _render_insight_note(insight)

    # ---- TAB 4: Item Insights ----
    with tab_items:
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
                insight = dashboard_insights.top_items_insight(top_items_df)
                if insight:
                    _render_insight_note(insight)
            else:
                st.info("No item spend data available for this range.")
        with item_col2:
            if not frequent_items_df.empty:
                st.plotly_chart(
                    dashboard_charts.frequent_items_bar(frequent_items_df),
                    width='content',
                )
                st.caption("Items you buy most often.")
                insight = dashboard_insights.frequent_items_insight(frequent_items_df)
                if insight:
                    _render_insight_note(insight)
            else:
                st.info("No item frequency data available for this range.")

    # ---- TAB 5: AI Insights ----
    with tab_ai:
        st.markdown(
            """
            <div class='ai-tab-hero'>
                <p class='ai-tab-hero-title'>🤖 AI Insights Studio</p>
                <p class='ai-tab-hero-subtitle'>
                    Turn your filtered bills into concise, actionable insights using Gemini.
                    Generate a narrative summary of trends, vendor behavior, and payment patterns.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ai_metric_col1, ai_metric_col2, ai_metric_col3 = st.columns(3)
        with ai_metric_col1:
            st.metric("📌 Records in Scope", f"{len(filtered_df):,}")
        with ai_metric_col2:
            st.metric("💳 Payment Methods", f"{payment_df['payment_method'].nunique() if not payment_df.empty else 0}")
        with ai_metric_col3:
            st.metric("🏪 Vendors in Scope", f"{vendor_df['vendor_name'].nunique() if not vendor_df.empty else 0}")

        st.markdown(
            """
            <div class='ai-action-card'>
                <p class='ai-action-title'>✨ Generate Insight Narrative</p>
                <p class='ai-action-subtitle'>Create a polished explanation of spending trends for the currently selected filters.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.get("api_key"):
            st.markdown(
                """
                <div class='ai-info-card'>
                    Add your Gemini API key in the sidebar to unlock AI-generated insights.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            summary = dashboard_ai_insights.build_summary(
                filtered_df,
                vendor_df,
                payment_df,
                items_df,
            )
            summary_key = dashboard_ai_insights.summary_hash(summary)

            if st.button(
                "✨ Generate AI Insights",
                key="ai_insights_generate",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("Generating insights with Gemini..."):
                    result = dashboard_ai_insights.generate_ai_insights(
                        summary,
                        st.session_state.get("api_key"),
                    )
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.session_state["ai_insights_text"] = result.get("text", "")
                    st.session_state["ai_insights_key"] = summary_key

            cached_text = st.session_state.get("ai_insights_text")
            cached_key = st.session_state.get("ai_insights_key")

            if cached_text and cached_key == summary_key:
                _render_ai_insights(cached_text)
            elif cached_text and cached_key != summary_key:
                st.markdown(
                    """
                    <div class='ai-refresh-hint'>
                        Filters changed since the last run. Click <strong>Generate AI Insights</strong> to refresh.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
