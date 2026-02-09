"""
Charts module for the dashboard.

This file contains only Plotly chart builders.
No Streamlit code, no database access, no analytics logic.
All charts use a consistent theme, interactive tooltips, and responsive layouts.
"""

import plotly.graph_objects as go


# -------------------------------------------------------------------
# THEME & COLOR PALETTE
# -------------------------------------------------------------------

COLORS = {
    "primary": "#4361ee",
    "secondary": "#f72585",
    "success": "#06d6a0",
    "danger": "#ef476f",
    "warning": "#ffd166",
    "info": "#118ab2",
    "purple": "#7209b7",
    "teal": "#0cb0a9",
    "orange": "#fb8500",
    "slate": "#457b9d",
    "dark": "#2b2d42",
    "light_bg": "rgba(0,0,0,0)",
}

PALETTE_SEQUENCE = [
    "#4361ee", "#f72585", "#06d6a0", "#ffd166", "#118ab2",
    "#7209b7", "#fb8500", "#0cb0a9", "#457b9d", "#ef476f",
]

# Default qualitative palette for categorical charts.

# Shared layout defaults applied to every chart.
_COMMON_LAYOUT = dict(
    autosize=True,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Segoe UI, Roboto, sans-serif", size=13, color="#2b2d42"),
    margin=dict(l=60, r=40, t=70, b=60),
    hoverlabel=dict(
        bgcolor="white",
        font_size=13,
        font_family="Segoe UI, Roboto, sans-serif",
        bordercolor="#dee2e6",
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25,
        xanchor="center",
        x=0.5,
        font=dict(size=11),
    ),
)


def _apply_theme(fig, **overrides):
    """Apply the common theme to any figure."""
    # Allow per-chart overrides while keeping the global theme consistent.
    layout = {**_COMMON_LAYOUT, **overrides}
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, zeroline=False, automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False, automargin=True)
    return fig


#  SPENDING TRENDS

def monthly_spending_line(monthly_df):
    """Area + line chart for monthly spending trend with gradient fill."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=monthly_df["month"],
            y=monthly_df["total_amount"],
            mode="lines+markers+text",
            text=[f"${v:,.0f}" for v in monthly_df["total_amount"]],
            textposition="top center",
            textfont=dict(size=10, color=COLORS["primary"]),
            line=dict(color=COLORS["primary"], width=3, shape="spline"),
            marker=dict(size=9, color="white", line=dict(color=COLORS["primary"], width=2.5)),
            fill="tozeroy",
            fillcolor="rgba(67, 97, 238, 0.10)",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Spending: $%{y:,.2f}<extra></extra>",
            name="Spending",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Monthly Spending Trend", font=dict(size=16)),
        height=340,
        hovermode="x unified",
        yaxis_title="Amount ($)",
        showlegend=False,
    )
    return fig


def cumulative_spending_line(monthly_df):
    """Cumulative running-total spending over time."""
    df = monthly_df.copy()
    df["cumulative"] = df["total_amount"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["cumulative"],
            mode="lines+markers+text",
            text=[f"${v:,.0f}" for v in df["cumulative"]],
            textposition="top center",
            textfont=dict(size=10, color=COLORS["purple"]),
            line=dict(color=COLORS["purple"], width=3, shape="spline"),
            marker=dict(size=8, color="white", line=dict(color=COLORS["purple"], width=2)),
            fill="tozeroy",
            fillcolor="rgba(114, 9, 183, 0.08)",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Cumulative: $%{y:,.2f}<extra></extra>",
            name="Cumulative",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Cumulative Spending Over Time", font=dict(size=16)),
        height=340,
        hovermode="x unified",
        yaxis_title="Cumulative ($)",
        showlegend=False,
    )
    return fig


def monthly_transactions_bar(monthly_counts_df):
    """Simple bar chart showing number of bills per month."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly_counts_df["month"],
            y=monthly_counts_df["transactions"],
            marker_color=COLORS["secondary"],
            marker_line=dict(color="white", width=1),
            text=monthly_counts_df["transactions"].astype(str),
            textposition="outside",
            textfont=dict(size=10),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Bills: %{y}<extra></extra>",
            name="Bills",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Number of Bills per Month", font=dict(size=16)),
        height=320,
        yaxis_title="Bills",
        showlegend=False,
    )
    return fig


def tax_vs_subtotal_bar(monthly_df):
    """Stacked bar chart for subtotal vs tax with value labels."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly_df["month"],
            y=monthly_df["subtotal"],
            name="Subtotal",
            marker_color=COLORS["info"],
            marker_line=dict(color="white", width=1),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Subtotal: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=monthly_df["month"],
            y=monthly_df["tax_amount"],
            name="Tax",
            marker_color=COLORS["warning"],
            marker_line=dict(color="white", width=1),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Tax: $%{y:,.2f}<extra></extra>",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Tax vs Subtotal Breakdown", font=dict(size=16)),
        barmode="stack",
        height=340,
        yaxis_title="Amount ($)",
    )
    return fig

#  VENDOR ANALYSIS

def vendor_pie_chart(vendor_df):
    """Donut chart for vendor spend distribution with custom hover."""
    total = vendor_df["total_spent"].sum()
    vendor_df = vendor_df.copy()
    vendor_df["pct"] = (vendor_df["total_spent"] / total * 100).round(1)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=vendor_df["vendor_name"],
                values=vendor_df["total_spent"],
                hole=0.45,
                marker=dict(
                    colors=PALETTE_SEQUENCE[: len(vendor_df)],
                    line=dict(color="white", width=2.5),
                ),
                textinfo="label+percent",
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Spent: $%{value:,.2f}<br>"
                    "Share: %{percent}<extra></extra>"
                ),
                pull=[0.03] * len(vendor_df),
            )
        ]
    )

    fig.add_annotation(
        text=f"<b>${total:,.0f}</b><br><span style='font-size:11px'>Total</span>",
        x=0.5, y=0.5,
        font=dict(size=16, color=COLORS["dark"]),
        showarrow=False,
    )

    _apply_theme(
        fig,
        title=dict(text="Top Vendors by Spend", font=dict(size=16)),
        height=380,
        showlegend=False,
    )
    return fig


def vendor_bar_chart(vendor_df):
    """Horizontal bar chart ranking vendors by total spend."""
    df = vendor_df.sort_values("total_spent", ascending=True).tail(10)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["vendor_name"],
            x=df["total_spent"],
            orientation="h",
            marker=dict(
                color=df["total_spent"],
                colorscale=[[0, "#c7d2fe"], [1, COLORS["primary"]]],
                line=dict(color="white", width=1),
            ),
            text=[f"${v:,.0f}" for v in df["total_spent"]],
            textposition="outside",
            textfont=dict(size=11),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total: $%{x:,.2f}<extra></extra>",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Vendor Spend Ranking", font=dict(size=16)),
        height=380,
        xaxis_title="Total Spend ($)",
        showlegend=False,
    )
    return fig

#  PAYMENT METHOD ANALYSIS

def payment_method_pie(payment_df):
    """Donut chart for payment method distribution."""
    total = payment_df["total_amount"].sum()

    fig = go.Figure(
        data=[
            go.Pie(
                labels=payment_df["payment_method"],
                values=payment_df["total_amount"],
                hole=0.5,
                marker=dict(
                    colors=[COLORS["primary"], COLORS["success"], COLORS["orange"],
                            COLORS["purple"], COLORS["teal"], COLORS["danger"]],
                    line=dict(color="white", width=2.5),
                ),
                textinfo="label+percent",
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Amount: $%{value:,.2f}<br>"
                    "Share: %{percent}<extra></extra>"
                ),
            )
        ]
    )

    fig.add_annotation(
        text=f"<b>${total:,.0f}</b><br><span style='font-size:11px'>Total</span>",
        x=0.5, y=0.5,
        font=dict(size=15, color=COLORS["dark"]),
        showarrow=False,
    )

    _apply_theme(
        fig,
        title=dict(text="Payment Method Distribution", font=dict(size=16)),
        height=380,
        showlegend=False,
    )
    return fig


def payment_method_bar(payment_df):
    """Bar chart comparing payment methods side by side."""
    df = payment_df.sort_values("total_amount", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["payment_method"],
            x=df["total_amount"],
            orientation="h",
            marker=dict(
                color=[COLORS["primary"], COLORS["success"], COLORS["orange"],
                       COLORS["purple"], COLORS["teal"], COLORS["danger"]][: len(df)],
                line=dict(color="white", width=1),
            ),
            text=[f"${v:,.0f}" for v in df["total_amount"]],
            textposition="outside",
            textfont=dict(size=11),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total: $%{x:,.2f}<extra></extra>",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Spending by Payment Method", font=dict(size=16)),
        height=320,
        xaxis_title="Amount ($)",
        showlegend=False,
    )
    return fig


#  TRANSACTION DISTRIBUTION

def transaction_histogram(df):
    """Histogram of transaction sizes with mean/median markers."""
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=df["total_amount"],
            nbinsx=25,
            marker_color=COLORS["success"],
            marker_line=dict(color="white", width=1),
            opacity=0.85,
            cliponaxis=False,
            hovertemplate="Range: $%{x}<br>Count: %{y}<extra></extra>",
            name="Bills",
        )
    )

    avg_val = df["total_amount"].mean()
    median_val = df["total_amount"].median()

    fig.add_vline(
        x=avg_val, line_dash="dash", line_color=COLORS["danger"], line_width=2,
        annotation_text=f"Mean: ${avg_val:,.0f}",
        annotation_position="top right",
        annotation_font=dict(size=10, color=COLORS["danger"]),
    )
    fig.add_vline(
        x=median_val, line_dash="dot", line_color=COLORS["info"], line_width=2,
        annotation_text=f"Median: ${median_val:,.0f}",
        annotation_position="top left",
        annotation_font=dict(size=10, color=COLORS["info"]),
    )

    _apply_theme(
        fig,
        title=dict(text="Transaction Size Distribution", font=dict(size=16)),
        height=340,
        xaxis_title="Bill Amount ($)",
        yaxis_title="Frequency",
        showlegend=False,
    )
    return fig


#  DAY-OF-WEEK & TIME PATTERNS

def day_of_week_bar(df):
    """Bar chart showing spending by day of the week."""
    if "purchase_date_dt" not in df.columns:
        return go.Figure()

    df = df.copy()
    df["day_name"] = df["purchase_date_dt"].dt.day_name()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_data = (
        df.groupby("day_name")["total_amount"]
        .agg(["sum", "count"])
        .reindex(day_order)
        .fillna(0)
        .reset_index()
    )
    day_data.columns = ["day", "total", "count"]

    max_day = day_data.loc[day_data["total"].idxmax(), "day"] if not day_data.empty else ""
    colors = [COLORS["primary"] if d != max_day else COLORS["secondary"] for d in day_data["day"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=day_data["day"],
            y=day_data["total"],
            marker_color=colors,
            marker_line=dict(color="white", width=1),
            text=[f"${v:,.0f}" for v in day_data["total"]],
            textposition="outside",
            textfont=dict(size=10),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Total: $%{y:,.2f}<br>"
                "Bills: %{customdata}<extra></extra>"
            ),
            customdata=day_data["count"],
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Spending by Day of Week", font=dict(size=16)),
        height=340,
        yaxis_title="Total Spend ($)",
        showlegend=False,
    )
    return fig


#  ITEM-LEVEL CHARTS

def top_items_bar(items_df):
    """Horizontal bar chart for top items by total spend with gradient coloring."""
    df = items_df.sort_values("item_total", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["item_name"],
            x=df["item_total"],
            orientation="h",
            marker=dict(
                color=df["item_total"],
                colorscale=[[0, "#e0c3fc"], [1, COLORS["purple"]]],
                line=dict(color="white", width=1),
            ),
            text=[f"${v:,.2f}" for v in df["item_total"]],
            textposition="outside",
            textfont=dict(size=10),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total Spend: $%{x:,.2f}<extra></extra>",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Top Items by Spend", font=dict(size=16)),
        height=max(280, len(df) * 32 + 80),
        xaxis_title="Total Spend ($)",
        showlegend=False,
    )
    return fig


def frequent_items_bar(freq_df):
    """Horizontal bar chart for most frequently purchased items."""
    df = freq_df.sort_values("purchase_count", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["item_name"],
            x=df["purchase_count"],
            orientation="h",
            marker=dict(
                color=df["purchase_count"],
                colorscale=[[0, "#b2f5ea"], [1, COLORS["teal"]]],
                line=dict(color="white", width=1),
            ),
            text=df["purchase_count"].astype(str),
            textposition="outside",
            textfont=dict(size=10),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Purchased: %{x} times<extra></extra>",
        )
    )

    _apply_theme(
        fig,
        title=dict(text="Most Frequently Purchased Items", font=dict(size=16)),
        height=max(280, len(df) * 32 + 80),
        xaxis_title="Purchase Count",
        showlegend=False,
    )
    return fig


#  YEAR-OVER-YEAR COMPARISON

def yoy_comparison(df):
    """Grouped bar chart comparing monthly spending across years."""
    if "purchase_date_dt" not in df.columns:
        return go.Figure()

    df = df.copy()
    df["year"] = df["purchase_date_dt"].dt.year
    df["month_num"] = df["purchase_date_dt"].dt.month
    df["month_name"] = df["purchase_date_dt"].dt.strftime("%b")

    yearly = (
        df.groupby(["year", "month_num", "month_name"])["total_amount"]
        .sum()
        .reset_index()
        .sort_values(["year", "month_num"])
    )

    years = sorted(yearly["year"].unique())
    if len(years) < 2:
        return go.Figure()

    fig = go.Figure()
    for i, year in enumerate(years):
        yr_data = yearly[yearly["year"] == year]
        fig.add_trace(
            go.Bar(
                x=yr_data["month_name"],
                y=yr_data["total_amount"],
                name=str(year),
                marker_color=PALETTE_SEQUENCE[i % len(PALETTE_SEQUENCE)],
                marker_line=dict(color="white", width=1),
                cliponaxis=False,
                hovertemplate=f"<b>{year} - %{{x}}</b><br>Spent: $%{{y:,.2f}}<extra></extra>",
            )
        )

    _apply_theme(
        fig,
        title=dict(text="Year-over-Year Monthly Comparison", font=dict(size=16)),
        barmode="group",
        height=360,
        yaxis_title="Amount ($)",
    )
    return fig


