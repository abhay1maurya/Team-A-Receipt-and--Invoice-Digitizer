import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import io

from src.database import get_all_bills, get_bill_items, delete_bill

# Professional color palette
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ecc71',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'info': '#3498db',
    'dark': '#2c3e50',
    'light': '#ecf0f1',
    'purple': '#9b59b6',
    'teal': '#1abc9c'
}

@st.cache_data(ttl=60, show_spinner=False)
def _cached_bills():
    """Fetch all bills from database with 60s cache."""
    try:
        return get_all_bills() or []
    except Exception as e:
        st.warning(f"Could not load bills: {e}")
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _cached_items(bills):
    """Fetch all line items for given bills and enrich with bill metadata."""
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
    """Render the main spending dashboard with filters, charts, and tables."""
    
    # Professional header with custom styling
    st.markdown("""
        <style>
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='color: #2c3e50;'>📊 Financial Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #7f8c8d; font-size: 1.1rem;'>Comprehensive insights into your spending patterns</p>", unsafe_allow_html=True)
    st.divider()

    # Load bills from database with caching
    bills = _cached_bills()
    if not bills:
        st.markdown("""
            <div style='text-align: center; padding: 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius: 10px; color: white;'>
                <h2>📭 No Data Available</h2>
                <p style='font-size: 1.2rem;'>Upload and save your first bill to unlock powerful insights!</p>
            </div>
        """, unsafe_allow_html=True)
        return

    # Convert to DataFrame
    bills_df = pd.DataFrame(bills)
    bills_df["purchase_date_dt"] = pd.to_datetime(bills_df.get("purchase_date"), errors="coerce")

    # Calculate metrics
    total_spent = bills_df["total_amount"].sum()
    months_active = bills_df["purchase_date_dt"].dt.to_period("M").nunique() or 1
    avg_per_month = total_spent / months_active
    vendors_count = bills_df["vendor_name"].nunique()
    transactions_count = len(bills_df)
    avg_transaction = total_spent / transactions_count if transactions_count > 0 else 0
    
    # Calculate trends
    current_month = datetime.now().replace(day=1)
    prev_month = (current_month - timedelta(days=1)).replace(day=1)
    
    current_month_data = bills_df[bills_df["purchase_date_dt"] >= current_month]
    prev_month_data = bills_df[(bills_df["purchase_date_dt"] >= prev_month) & (bills_df["purchase_date_dt"] < current_month)]
    
    current_month_spend = current_month_data["total_amount"].sum()
    prev_month_spend = prev_month_data["total_amount"].sum()
    
    spend_delta = current_month_spend - prev_month_spend
    spend_delta_pct = (spend_delta / prev_month_spend * 100) if prev_month_spend > 0 else 0

    # Display KPIs
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="💰 Total Spend", 
            value=f"${total_spent:,.2f}",
            delta=f"{spend_delta_pct:+.1f}% vs last month" if prev_month_spend > 0 else None
        )
    with col2:
        bill_delta = len(current_month_data) - len(prev_month_data)
        st.metric(
            label="🧾 Total Bills", 
            value=str(transactions_count),
            delta=f"{bill_delta:+d} this month" if len(prev_month_data) > 0 else None
        )
    with col3:
        st.metric(label="💵 Avg Bill Value", value=f"${avg_transaction:,.2f}")
    with col4:
        st.metric(label="🏪 Unique Vendors", value=str(vendors_count))
    with col5:
        st.metric(label="📊 Monthly Avg", value=f"${avg_per_month:,.2f}")

    st.divider()

    # SMART FILTERS
    st.markdown("### 🔍 Smart Filters")
    
    preset_col, custom_col = st.columns([1, 3])
    with preset_col:
        date_preset = st.selectbox(
            "Quick Select",
            ["Custom Range", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "This Year", "All Time"],
            key="date_preset"
        )
    
    # Calculate date range based on preset
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
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        if date_preset == "Custom Range":
            date_range = st.date_input(
                "📅 Date Range",
                value=(bills_df["purchase_date_dt"].min().date(), bills_df["purchase_date_dt"].max().date()),
                key="date_range_filter"
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
        else:
            st.markdown(f"**📅 Date Range**")
            st.caption(f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    with filter_col2:
        all_vendors = ["All Vendors"] + sorted(bills_df["vendor_name"].dropna().unique().tolist())
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
            key="amount_filter"
        )
    
    with filter_col4:
        payment_methods = bills_df[bills_df["payment_method"].notna()]["payment_method"].unique().tolist()
        all_payments = ["All Methods"] + sorted(payment_methods)
        selected_payment = st.selectbox("💳 Payment Method", options=all_payments, key="payment_filter")
    
    # Apply filters
    filtered_df = bills_df[
        (bills_df["purchase_date_dt"] >= start_date) &
        (bills_df["purchase_date_dt"] <= end_date) &
        (bills_df["total_amount"] >= amount_range[0]) &
        (bills_df["total_amount"] <= amount_range[1])
    ].copy()
    
    if selected_vendor != "All Vendors":
        filtered_df = filtered_df[filtered_df["vendor_name"] == selected_vendor]
    
    if selected_payment != "All Methods":
        filtered_df = filtered_df[filtered_df["payment_method"] == selected_payment]
    
    # Filter summary and export
    summary_col1, summary_col2 = st.columns([3, 1])
    with summary_col1:
        if len(filtered_df) < len(bills_df):
            st.success(f"✅ Showing **{len(filtered_df)}** of **{len(bills_df)}** bills | Total: **${filtered_df['total_amount'].sum():,.2f}**")
        else:
            st.info(f"📊 Showing all **{len(bills_df)}** bills | Total: **${filtered_df['total_amount'].sum():,.2f}**")

    # Charts
    st.markdown("### 📊 Spending Analytics")
    
    if filtered_df.empty:
        st.warning("⚠️ No data matches your current filters. Try adjusting the filter criteria.")
        return
    
    # Monthly trend
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("#### 📈 Monthly Spending Trend")
        monthly = (
            filtered_df.dropna(subset=["purchase_date_dt"])
            .groupby(filtered_df["purchase_date_dt"].dt.to_period("M"))["total_amount"]
            .sum()
            .reset_index()
        )
        monthly["month"] = monthly["purchase_date_dt"].dt.strftime("%Y-%m")
        
        fig1 = go.Figure()
        fig1.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["total_amount"],
                mode="lines+markers",
                line=dict(color=COLORS['primary'], width=3, shape='spline'),
                marker=dict(size=10, color=COLORS['primary'], line=dict(color='white', width=2)),
                fill='tozeroy',
                fillcolor="rgba(31, 119, 180, 0.1)"
            )
        )
        fig1.update_layout(
            hovermode="x unified",
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis_title="Amount ($)",
            xaxis_title="",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial, sans-serif", size=12)
        )
        fig1.update_xaxes(showgrid=False, showline=True, linewidth=1, linecolor='lightgray')
        fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig1, width="stretch")

    with col_chart2:
        st.markdown("#### 🧮 Tax % Contribution by Month")
        monthly_tax = (
            filtered_df.dropna(subset=["purchase_date_dt"]).groupby(
                filtered_df["purchase_date_dt"].dt.to_period("M")
            ).agg({
                "total_amount": "sum",
                "tax_amount": "sum"
            }).reset_index()
        )
        monthly_tax["month"] = monthly_tax["purchase_date_dt"].dt.strftime("%Y-%m")
        monthly_tax["tax_percentage"] = (monthly_tax["tax_amount"] / monthly_tax["total_amount"] * 100).round(2)
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=monthly_tax["month"],
            y=monthly_tax["tax_percentage"],
            mode="lines+markers",
            line=dict(color=COLORS['danger'], width=3, shape='spline'),
            marker=dict(size=10, color=COLORS['danger'], line=dict(color='white', width=2)),
            fill='tozeroy',
            fillcolor='rgba(231, 76, 60, 0.1)'
        ))
        fig2.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis_title="Tax % of Total",
            xaxis_title="",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial, sans-serif", size=12)
        )
        fig2.update_xaxes(showgrid=False, showline=True, linewidth=1, linecolor='lightgray')
        fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig2, width="stretch")

    st.divider()

    # Vendor and payment analysis
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.markdown("#### 🏪 Vendor Spend Distribution")
        by_vendor = filtered_df.groupby("vendor_name")["total_amount"].sum().sort_values(ascending=False).head(10).reset_index()
        
        fig3 = go.Figure(data=[
            go.Pie(
                labels=by_vendor["vendor_name"],
                values=by_vendor["total_amount"],
                hole=0.4,
                textinfo="none",
                # hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
                marker=dict(colors=px.colors.qualitative.Set3, line=dict(color='white', width=2)),
                pull=[0.05] * len(by_vendor)
            )
        ])
        fig3.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05, font=dict(size=10)),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial, sans-serif", size=11)
        )
        st.plotly_chart(fig3,width="stretch")

    with col_chart4:
        st.markdown("#### 💳 Payment Method Distribution")
        payment_dist = filtered_df[filtered_df["payment_method"].notna()].groupby("payment_method")["total_amount"].sum().reset_index()
        
        if not payment_dist.empty:
            fig4 = go.Figure(data=[
                go.Pie(
                    labels=payment_dist["payment_method"],
                    values=payment_dist["total_amount"],
                    hole=0.5,
                    textinfo="none",
                    hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
                    marker=dict(colors=px.colors.qualitative.Pastel, line=dict(color='white', width=2))
                )
            ])
            fig4.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05, font=dict(size=10)),
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial, sans-serif", size=11)
            )
            st.plotly_chart(fig4, width="stretch")
        else:
            st.info("No payment method data available")

    st.divider()

    # Tax and transaction analysis
    col_chart5, col_chart6 = st.columns(2)

    with col_chart5:
        st.markdown("#### 🧮 Tax vs Subtotal Breakdown")
        monthly_detailed = filtered_df.dropna(subset=["purchase_date_dt"]).groupby(
            filtered_df["purchase_date_dt"].dt.to_period("M")
        ).agg({
            "total_amount": "sum",
            "tax_amount": "sum"
        }).reset_index()
        monthly_detailed["month"] = monthly_detailed["purchase_date_dt"].dt.strftime("%Y-%m")
        monthly_detailed["subtotal"] = monthly_detailed["total_amount"] - monthly_detailed["tax_amount"]
        
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=monthly_detailed["month"],
            y=monthly_detailed["subtotal"],
            name="Subtotal",
            marker_color=COLORS['info'],
            hovertemplate="<b>Subtotal</b><br>$%{y:,.2f}<extra></extra>"
        ))
        fig5.add_trace(go.Bar(
            x=monthly_detailed["month"],
            y=monthly_detailed["tax_amount"],
            name="Tax",
            marker_color=COLORS['warning'],
            hovertemplate="<b>Tax</b><br>$%{y:,.2f}<extra></extra>"
        ))
        fig5.update_layout(
            barmode='stack',
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis_title="Amount ($)",
            xaxis_title="",
            legend=dict(orientation="h", yanchor="top", y=1.15, xanchor="right", x=1, bgcolor='rgba(255,255,255,0.8)'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial, sans-serif", size=12)
        )
        fig5.update_xaxes(showgrid=False, showline=True, linewidth=1, linecolor='lightgray')
        fig5.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig5, width="stretch")

    with col_chart6:
        st.markdown("#### 📊 Transaction Size Distribution")
        fig6 = go.Figure()
        fig6.add_trace(go.Histogram(
            x=filtered_df["total_amount"],
            nbinsx=20,
            marker_color=COLORS['success'],
            opacity=0.8,
            marker_line=dict(color='white', width=1),
            hovertemplate="Range: $%{x}<br>Count: %{y}<extra></extra>"
        ))
        fig6.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis_title="Bill Amount ($)",
            yaxis_title="Frequency",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial, sans-serif", size=12)
        )
        fig6.update_xaxes(showgrid=False, showline=True, linewidth=1, linecolor='lightgray')
        fig6.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig6, width="stretch")

    st.divider()

    # High-value bills
    st.markdown("### 💎 High-Value Bills (Above $100)")
    threshold = 100.0
    high_value_bills = filtered_df[filtered_df["total_amount"] >= threshold].sort_values("total_amount", ascending=False)
    
    if not high_value_bills.empty:
        col_hv1, col_hv2, col_hv3 = st.columns(3)
        with col_hv1:
            st.metric("🔴 High-Value Count", len(high_value_bills), 
                     delta=f"{len(high_value_bills) / len(filtered_df) * 100:.1f}% of filtered")
        with col_hv2:
            hv_total = high_value_bills["total_amount"].sum()
            st.metric("💰 High-Value Total", f"${hv_total:,.2f}",
                     delta=f"{hv_total / filtered_df['total_amount'].sum() * 100:.1f}% of spend")
        with col_hv3:
            st.metric("📊 High-Value Average", f"${high_value_bills['total_amount'].mean():,.2f}")
        
        hv_display = high_value_bills[["id", "invoice_number", "vendor_name", "purchase_date", "total_amount", "tax_amount", "payment_method"]].copy()
        hv_display["total_amount"] = hv_display["total_amount"].apply(lambda x: f"${x:.2f}")
        hv_display["tax_amount"] = hv_display["tax_amount"].apply(lambda x: f"${x:.2f}")
        st.dataframe(hv_display, hide_index=True, width="stretch")
    else:
        st.info(f"📭 No bills above ${threshold} in current filters")

    st.divider()

    # Insights tables
    st.markdown("### 📋 Detailed Insights")
    col_vendors, col_items = st.columns(2)

    with col_vendors:
        st.markdown("#### 🔝 Top Vendors Analysis")
        vendor_analysis = filtered_df.groupby("vendor_name").agg({"total_amount": ["sum", "count", "mean"]}).reset_index()
        vendor_analysis.columns = ["Vendor", "Total Spent", "Transactions", "Avg. per Bill"]
        vendor_analysis = vendor_analysis.sort_values("Total Spent", ascending=False).head(10)
        vendor_analysis["Total Spent"] = vendor_analysis["Total Spent"].apply(lambda x: f"${x:.2f}")
        vendor_analysis["Avg. per Bill"] = vendor_analysis["Avg. per Bill"].apply(lambda x: f"${x:.2f}")
        st.dataframe(vendor_analysis, hide_index=True, width="stretch")

    with col_items:
        st.markdown("#### ⭐ Top Items by Total Spend")
        items = _cached_items(bills)
        if items:
            items_df = pd.DataFrame(items)
            items_df["item_total"] = pd.to_numeric(items_df.get("item_total"), errors="coerce").fillna(0)
            filtered_bill_ids = set(filtered_df["id"].values)
            items_df = items_df[items_df["bill_id"].isin(filtered_bill_ids)]
            
            if not items_df.empty:
                top_items = items_df.groupby("item_name").agg({"item_total": ["sum", "count", "mean"]}).reset_index()
                top_items.columns = ["Item", "Total Spent", "Times Bought", "Avg. Price"]
                top_items = top_items.sort_values("Total Spent", ascending=False).head(10)
                top_items["Total Spent"] = top_items["Total Spent"].apply(lambda x: f"${x:.2f}")
                top_items["Avg. Price"] = top_items["Avg. Price"].apply(lambda x: f"${x:.2f}")
                st.dataframe(top_items, hide_index=True, width="stretch")
            else:
                st.info("No items in filtered results")
        else:
            st.info("No line items available yet.")

    st.divider()
    
    # Item-level analytics
    st.markdown("### 🛒 Item-Level Analytics")
    item_col1, item_col2 = st.columns(2)
    
    with item_col1:
        st.markdown("#### 🔁 Most Frequently Purchased Items")
        if items and 'items_df' in locals() and not items_df.empty:
            item_frequency = items_df.groupby("item_name").size().sort_values(ascending=False).head(10).reset_index()
            item_frequency.columns = ["Item", "Times Purchased"]
            
            fig_freq = px.bar(item_frequency, y="Item", x="Times Purchased", orientation='h',
                             color="Times Purchased", color_continuous_scale="Teal", height=350)
            fig_freq.update_layout(
                margin=dict(l=0, r=0, t=20, b=0), showlegend=False, yaxis_title="", xaxis_title="Purchase Count",
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Arial, sans-serif", size=11)
            )
            fig_freq.update_yaxes(categoryorder='total ascending')
            fig_freq.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
            st.plotly_chart(fig_freq, width="stretch")
        else:
            st.info("No item data available")
    
    with item_col2:
        st.markdown("#### 💸 Highest Spending Items")
        if items and 'items_df' in locals() and not items_df.empty:
            item_spending = items_df.groupby("item_name")["item_total"].sum().sort_values(ascending=False).head(10).reset_index()
            item_spending.columns = ["Item", "Total Spent"]
            
            fig_spend = px.bar(item_spending, y="Item", x="Total Spent", orientation='h',
                              color="Total Spent", color_continuous_scale="Purples", height=350)
            fig_spend.update_layout(
                margin=dict(l=0, r=0, t=20, b=0), showlegend=False, yaxis_title="", xaxis_title="Amount Spent ($)",
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Arial, sans-serif", size=11)
            )
            fig_spend.update_yaxes(categoryorder='total ascending')
            fig_spend.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
            st.plotly_chart(fig_spend, width="stretch")
        else:
            st.info("No item data available")
    
    st.divider()

    # Recent bills
    st.markdown("### 📋 Recent Bills")
    recent_cols = ["id", "invoice_number", "vendor_name", "purchase_date", "purchase_time", "payment_method", "total_amount", "tax_amount", "currency"]
    recent = filtered_df.sort_values(by="purchase_date_dt", ascending=False).head(20)
    recent_display = recent[recent_cols].copy()
    recent_display["total_amount"] = recent_display["total_amount"].apply(lambda x: f"${x:.2f}")
    recent_display["tax_amount"] = recent_display["tax_amount"].apply(lambda x: f"${x:.2f}")
    st.dataframe(recent_display, hide_index=True, width="stretch")

    st.divider()

    # Bill details viewer
    st.markdown("### 🔎 Bill Details")
    if not filtered_df.empty:
        options_df = filtered_df.sort_values(by="purchase_date_dt", ascending=False).loc[:, ["id", "vendor_name", "purchase_date", "total_amount"]].copy()
        options_df["total_amount"] = pd.to_numeric(options_df["total_amount"], errors="coerce").fillna(0.0)

        option_labels = {
            int(row["id"]): f"Bill #{int(row['id'])} • {row['vendor_name']} • {row['purchase_date']} • ${row['total_amount']:.2f}"
            for _, row in options_df.iterrows()
        }
        selected_bill_id = st.selectbox("Select a bill to view details:", options=list(option_labels.keys()),
                                       format_func=lambda x: option_labels.get(int(x), str(x)))

        if selected_bill_id is not None:
            bill_row = bills_df[bills_df["id"] == selected_bill_id]
            if not bill_row.empty:
                bill = bill_row.iloc[0].to_dict()

                meta_col1, meta_col2 = st.columns(2)
                with meta_col1:
                    st.markdown("#### Bill Summary")
                    st.write(f"Vendor: {bill.get('vendor_name', '-')}")
                    st.write(f"Invoice #: {bill.get('invoice_number', '-')}")
                    st.write(f"Date: {bill.get('purchase_date', '-')}")
                    st.write(f"Time: {bill.get('purchase_time', '-')}")
                    st.write(f"Payment: {bill.get('payment_method', '-')}")
                    st.write(f"Currency: {bill.get('currency', '-')}")

                with meta_col2:
                    st.markdown("#### Amounts")
                    subtotal = bill.get('subtotal') if bill.get('subtotal') is not None else bill.get('total_amount', 0) - bill.get('tax_amount', 0)
                    st.write(f"Subtotal: ${float(subtotal or 0):,.2f}")
                    st.write(f"Tax: ${float(bill.get('tax_amount', 0) or 0):,.2f}")
                    st.write(f"Total: ${float(bill.get('total_amount', 0) or 0):,.2f}")
                    
                    # Show original currency info if available
                    if bill.get('original_currency') and bill.get('original_currency') != bill.get('currency'):
                        st.divider()
                        st.markdown("#### Original Currency")
                        st.write(f"Currency: {bill.get('original_currency', '-')}")
                        if bill.get('original_total_amount') is not None:
                            orig_total = float(bill.get('original_total_amount'))
                            st.write(f"Original Total: {orig_total:,.2f} {bill.get('original_currency', '')}")
                        if bill.get('exchange_rate') is not None:
                            st.write(f"Exchange Rate: {float(bill.get('exchange_rate')):,.6f}")

                try:
                    line_items = get_bill_items(selected_bill_id) or []
                except Exception:
                    line_items = []

                st.markdown("#### Line Items")
                if line_items:
                    items_detail = pd.DataFrame(line_items)
                    for col in ["item_total", "unit_price", "quantity"]:
                        if col in items_detail.columns:
                            items_detail[col] = pd.to_numeric(items_detail[col], errors="coerce").fillna(0)
                    if "unit_price" in items_detail.columns:
                        items_detail["unit_price"] = items_detail["unit_price"].apply(lambda x: f"${x:.2f}")
                    if "item_total" in items_detail.columns:
                        items_detail["item_total"] = items_detail["item_total"].apply(lambda x: f"${x:.2f}")
                    st.dataframe(items_detail, hide_index=True, width="stretch")
                else:
                    st.info("No line items found for this bill.")
    else:
        st.info("No bills available in current filter to display details.")

    st.divider()

    # Database Explorer - show complete contents of bills and line items
    st.markdown("### 🗂️ Database Explorer")
    tabs = st.tabs(["Bills", "Line Items"])

    # Bills tab: show all columns returned by get_all_bills()
    with tabs[0]:
        st.markdown("#### All Bills (Raw)")
        bills_full_cols = [
            "id",
            "invoice_number",
            "vendor_name",
            "purchase_date",
            "purchase_time",
            "subtotal",
            "tax_amount",
            "total_amount",
            "currency",
            "original_currency",
            "original_total_amount",
            "exchange_rate",
            "payment_method",
        ]
        bills_full = bills_df.copy()
        # Ensure columns exist; missing ones will be filled with None
        for c in bills_full_cols:
            if c not in bills_full.columns:
                bills_full[c] = None
        bills_full = bills_full[bills_full_cols]

        # Format numeric currency fields for readability
        for c in ["subtotal", "tax_amount", "total_amount", "original_total_amount"]:
            bills_full[c] = pd.to_numeric(bills_full[c], errors="coerce")
            bills_full[c] = bills_full[c].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
        # Exchange rate formatting
        bills_full["exchange_rate"] = bills_full["exchange_rate"].apply(lambda x: f"{float(x):.6f}" if pd.notna(x) else "-")

        st.dataframe(bills_full, hide_index=True, width="stretch")

    # Line Items tab: show all items across bills (flattened)
    with tabs[1]:
        st.markdown("#### All Line Items (Raw)")
        all_items = _cached_items(bills)
        if all_items:
            items_all_df = pd.DataFrame(all_items)
            # Normalize numeric columns
            for col in ["quantity", "unit_price", "item_total"]:
                if col in items_all_df.columns:
                    items_all_df[col] = pd.to_numeric(items_all_df[col], errors="coerce").fillna(0)
            # Friendly formatting
            if "unit_price" in items_all_df.columns:
                items_all_df["unit_price"] = items_all_df["unit_price"].apply(lambda x: f"${x:.2f}")
            if "item_total" in items_all_df.columns:
                items_all_df["item_total"] = items_all_df["item_total"].apply(lambda x: f"${x:.2f}")

            # Order useful columns if present
            preferred_cols = [
                "s_no", "bill_id", "vendor_name", "purchase_date",
                "item_name", "quantity", "unit_price", "item_total"
            ]
            ordered_cols = [c for c in preferred_cols if c in items_all_df.columns]
            remaining_cols = [c for c in items_all_df.columns if c not in ordered_cols]
            items_all_df = items_all_df[ordered_cols + remaining_cols]

            st.dataframe(items_all_df, hide_index=True, width="stretch")
        else:
            st.info("No line items available in the database.")

    st.divider()

    # Delete Bill Section
    st.markdown("### 🗑️ Delete Bill")
    st.warning("⚠️ **Warning:** Deleting a bill will permanently remove it and all associated line items from the database. This action cannot be undone.")
    
    delete_col1, delete_col2, delete_col3 = st.columns([2, 1, 1])
    
    with delete_col1:
        # Create options for deletion
        delete_options_df = bills_df.sort_values(by="purchase_date_dt", ascending=False).copy()
        delete_option_labels = {
            int(row["id"]): f"Bill #{int(row['id'])} • {row['vendor_name']} • {row['purchase_date']} • ${float(row['total_amount']):,.2f}"
            for _, row in delete_options_df.iterrows()
        }
        
        selected_delete_id = st.selectbox(
            "Select bill to delete:",
            options=list(delete_option_labels.keys()),
            format_func=lambda x: delete_option_labels.get(int(x), str(x)),
            key="delete_bill_selector"
        )
    
    with delete_col2:
        st.markdown("#### ")  # Spacer for alignment
        confirm_delete = st.checkbox("Confirm deletion", key="confirm_delete_checkbox")
    
    with delete_col3:
        st.markdown("#### ")  # Spacer for alignment
        if st.button("🗑️ Delete Bill", type="primary", disabled=not confirm_delete, width="stretch"):
            try:
                success = delete_bill(selected_delete_id)
                if success:
                    st.success(f"✅ Bill #{selected_delete_id} deleted successfully!")
                    # Clear cache to refresh dashboard
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Bill #{selected_delete_id} not found in database.")
            except Exception as e:
                st.error(f"❌ Error deleting bill: {str(e)}")
