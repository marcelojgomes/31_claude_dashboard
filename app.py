"""E-commerce performance dashboard.

Reads the CSVs in dataset/ and renders an interactive Streamlit dashboard.
Chart styling follows the project's dataviz palette (dark surface, fixed
categorical hue order, single-hue magnitude bars, no dual-axis charts).
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "dataset"

# --- palette (validated dark-mode set, see CLAUDE.md / dataviz skill) ------
SURFACE = "#1a1a19"
PAGE = "#0d0d0d"
INK_PRIMARY = "#ffffff"
INK_SECONDARY = "#c3c2b7"
INK_MUTED = "#898781"
GRIDLINE = "#2c2c2a"
BASELINE = "#383835"

BLUE = "#3987e5"
ORANGE = "#d95926"
AQUA = "#199e70"
YELLOW = "#c98500"
MAGENTA = "#d55181"
GREEN = "#008300"
VIOLET = "#9085e9"
RED = "#e66767"

STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"

TIER_COLORS = {"Free": INK_MUTED, "Silver": BLUE, "Gold": YELLOW, "Platinum": VIOLET}
CHANNEL_COLORS = {
    "Direct": BLUE,
    "Organic Search": AQUA,
    "Paid Ad": ORANGE,
    "Social Media": MAGENTA,
    "Email Campaign": YELLOW,
    "Referral": VIOLET,
}
DEVICE_COLORS = {"Desktop": BLUE, "Mobile": AQUA, "Tablet": ORANGE}
GENDER_COLORS = {"Female": MAGENTA, "Male": BLUE, "Other": VIOLET}
SEGMENT_COLORS = {
    "Champions": STATUS_GOOD,
    "Loyal": BLUE,
    "At risk": STATUS_WARNING,
    "Lost": STATUS_CRITICAL,
}
STATUS_COLORS = {
    "Delivered": STATUS_GOOD,
    "Processing": YELLOW,
    "Returned": ORANGE,
    "Cancelled": STATUS_CRITICAL,
}
REPEAT_COLORS = {"New": BLUE, "Returning": AQUA}
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

st.set_page_config(page_title="E-Commerce Dashboard", layout="wide", page_icon="📊")


# --- data -------------------------------------------------------------
@st.cache_data
def load_data():
    orders = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date", "delivery_date"])
    customers = pd.read_csv(DATA_DIR / "customers.csv", parse_dates=["registration_date"])
    return orders, customers


orders, customers = load_data()

# --- sidebar filters ----------------------------------------------------
st.sidebar.header("Filters")

year_min, year_max = int(orders["year"].min()), int(orders["year"].max())
year_range = st.sidebar.slider("Year range", year_min, year_max, (year_min, year_max))

categories = sorted(orders["category"].dropna().unique())
selected_categories = st.sidebar.multiselect("Category", categories, default=categories)

devices = sorted(orders["device_used"].dropna().unique())
selected_devices = st.sidebar.multiselect("Device", devices, default=devices)

statuses = sorted(orders["order_status"].dropna().unique())
selected_statuses = st.sidebar.multiselect("Order status", statuses, default=statuses)

filtered = orders[
    orders["year"].between(*year_range)
    & orders["category"].isin(selected_categories)
    & orders["device_used"].isin(selected_devices)
    & orders["order_status"].isin(selected_statuses)
]


# --- chart chrome helper --------------------------------------------------
def style_fig(fig, height=320, showlegend=False):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=INK_SECONDARY, size=13),
        title_font=dict(color=INK_PRIMARY, size=15),
        showlegend=showlegend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK_SECONDARY)),
        hoverlabel=dict(bgcolor=PAGE, font=dict(color=INK_PRIMARY)),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=BASELINE, zerolinecolor=BASELINE, tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=BASELINE, zerolinecolor=BASELINE, tickfont=dict(color=INK_MUTED))
    return fig


def unfiltered_caption():
    st.caption("This panel reflects the full customer table and is not affected by the filters above.")


# --- page styling (mirrors design-system/ dark glass-card look) ---------
st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {PAGE}; }}
    div[data-testid="stMetric"] {{
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 20px;
        padding: 16px 18px;
    }}
    div[data-testid="stMetricLabel"] {{ color: {INK_MUTED}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("E-Commerce Performance Dashboard")
st.caption(f"{len(filtered):,} orders in the selected filters · {year_range[0]}–{year_range[1]}")

tab_overview, tab_customers, tab_products, tab_funnel, tab_geo = st.tabs(
    ["Overview", "Customers & Retention", "Products & Returns", "Funnel & Engagement", "Geography & Demographics"]
)

# ===========================================================================
# TAB 1 — OVERVIEW
# ===========================================================================
with tab_overview:
    delivered = filtered[filtered["order_status"] != "Cancelled"]
    total_revenue = delivered["total_amount_usd"].sum()
    total_orders = len(filtered)
    unique_customers = filtered["customer_id"].nunique()
    aov = delivered["total_amount_usd"].mean() if len(delivered) else 0.0
    return_rate = filtered["returned"].mean() if len(filtered) else 0.0
    churn_rate = customers["churned"].mean()

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Revenue", f"${total_revenue:,.0f}")
    k2.metric("Orders", f"{total_orders:,}")
    k3.metric("Customers", f"{unique_customers:,}")
    k4.metric("Avg order value", f"${aov:,.2f}")
    k5.metric("Return rate", f"{return_rate:.1%}")
    k6.metric("Churn rate (all customers)", f"{churn_rate:.1%}")

    st.divider()

    # revenue & orders trend (own axes, stacked - never dual-axis)
    monthly = (
        filtered.groupby(["year", "month"])
        .agg(revenue=("total_amount_usd", "sum"), orders=("order_id", "count"))
        .reset_index()
        .sort_values(["year", "month"])
    )
    monthly["period"] = pd.to_datetime(monthly["year"].astype(str) + "-" + monthly["month"].astype(str) + "-01")

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(
            go.Scatter(
                x=monthly["period"],
                y=monthly["revenue"],
                mode="lines",
                line=dict(color=BLUE, width=2, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(57,135,229,0.12)",
                hovertemplate="%{x|%b %Y}<br>Revenue: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(title="Monthly revenue")
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with c2:
        fig = go.Figure(
            go.Bar(
                x=monthly["period"],
                y=monthly["orders"],
                marker_color=ORANGE,
                hovertemplate="%{x|%b %Y}<br>Orders: %{y:,}<extra></extra>",
            )
        )
        fig.update_layout(title="Monthly order volume", bargap=0.25)
        st.plotly_chart(style_fig(fig), use_container_width=True)

    # category performance (single-hue magnitude ranking)
    by_category = filtered.groupby("category")["total_amount_usd"].sum().sort_values(ascending=True)
    fig = go.Figure(
        go.Bar(
            x=by_category.values,
            y=by_category.index,
            orientation="h",
            marker_color=BLUE,
            hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(title="Revenue by category")
    st.plotly_chart(style_fig(fig, height=420), use_container_width=True)

    # top products table
    st.subheader("Top products")
    top_products = (
        filtered.groupby(["product_name", "category"])
        .agg(
            orders=("order_id", "count"),
            revenue=("total_amount_usd", "sum"),
            avg_rating=("customer_rating", "mean"),
            return_rate=("returned", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(10)
    )
    top_products["revenue"] = top_products["revenue"].map(lambda v: f"${v:,.0f}")
    top_products["avg_rating"] = top_products["avg_rating"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
    top_products["return_rate"] = top_products["return_rate"].map(lambda v: f"{v:.1%}")
    st.dataframe(top_products, use_container_width=True, hide_index=True)

    st.divider()

    # payment method & device split
    c3, c4 = st.columns(2)
    with c3:
        by_payment = filtered["payment_method"].value_counts().sort_values(ascending=True)
        fig = go.Figure(
            go.Bar(
                x=by_payment.values,
                y=by_payment.index,
                orientation="h",
                marker_color=AQUA,
                hovertemplate="%{y}<br>Orders: %{x:,}<extra></extra>",
            )
        )
        fig.update_layout(title="Orders by payment method")
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with c4:
        by_device = filtered["device_used"].value_counts()
        fig = go.Figure(
            go.Pie(
                labels=by_device.index,
                values=by_device.values,
                hole=0.6,
                marker=dict(colors=[DEVICE_COLORS.get(d, INK_MUTED) for d in by_device.index]),
                textfont=dict(color=INK_PRIMARY),
                hovertemplate="%{label}<br>Orders: %{value:,} (%{percent})<extra></extra>",
            )
        )
        fig.update_layout(title="Orders by device")
        st.plotly_chart(style_fig(fig, height=320, showlegend=True), use_container_width=True)

    with st.expander("Filtered orders (raw data)"):
        st.dataframe(filtered, use_container_width=True, hide_index=True)

# ===========================================================================
# TAB 2 — CUSTOMERS & RETENTION (full customer base, not affected by filters)
# ===========================================================================
with tab_customers:
    st.subheader("Customer base")
    unfiltered_caption()

    c5, c6 = st.columns(2)
    with c5:
        by_tier = customers["membership_tier"].value_counts()
        order = [t for t in ["Free", "Silver", "Gold", "Platinum"] if t in by_tier.index]
        by_tier = by_tier.reindex(order)
        fig = go.Figure(
            go.Bar(
                x=by_tier.index,
                y=by_tier.values,
                marker_color=[TIER_COLORS[t] for t in by_tier.index],
                hovertemplate="%{x}<br>Customers: %{y:,}<extra></extra>",
            )
        )
        fig.update_layout(title="Customers by membership tier", bargap=0.4)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with c6:
        by_channel = customers["acquisition_channel"].value_counts()
        fig = go.Figure(
            go.Bar(
                x=by_channel.index,
                y=by_channel.values,
                marker_color=[CHANNEL_COLORS.get(c, INK_MUTED) for c in by_channel.index],
                hovertemplate="%{x}<br>Customers: %{y:,}<extra></extra>",
            )
        )
        fig.update_layout(title="Customers by acquisition channel", bargap=0.3)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    st.divider()

    # --- registration cohort x churn -------------------------------------
    st.subheader("Churn by registration cohort")
    unfiltered_caption()
    cohort = customers.copy()
    cohort["cohort"] = cohort["registration_date"].dt.to_period("Q").astype(str)
    by_cohort = (
        cohort.groupby("cohort")
        .agg(customers=("customer_id", "count"), churn_rate=("churned", "mean"))
        .reset_index()
        .sort_values("cohort")
    )
    fig = go.Figure(
        go.Bar(
            x=by_cohort["cohort"],
            y=by_cohort["churn_rate"],
            marker_color=ORANGE,
            hovertemplate="%{x}<br>Churn rate: %{y:.1%}<br>Customers: %{customdata:,}<extra></extra>",
            customdata=by_cohort["customers"],
        )
    )
    fig.update_layout(title="Churn rate by sign-up quarter", bargap=0.2)
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    st.divider()

    # --- RFM segmentation --------------------------------------------------
    st.subheader("RFM segmentation")
    unfiltered_caption()
    rfm = customers.copy()
    rfm["r_score"] = pd.qcut(rfm["days_since_last_purchase"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["total_orders"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["total_spend_usd"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def segment_label(score):
        if score >= 10:
            return "Champions"
        if score >= 8:
            return "Loyal"
        if score >= 6:
            return "At risk"
        return "Lost"

    rfm["segment"] = rfm["rfm_score"].map(segment_label)

    c7, c8 = st.columns([3, 2])
    with c7:
        fig = go.Figure()
        for segment, color in SEGMENT_COLORS.items():
            sub = rfm[rfm["segment"] == segment]
            fig.add_trace(
                go.Scatter(
                    x=sub["days_since_last_purchase"],
                    y=sub["total_spend_usd"],
                    mode="markers",
                    name=segment,
                    marker=dict(
                        color=color,
                        size=(sub["total_orders"].clip(upper=30) / 30 * 16 + 4),
                        opacity=0.65,
                    ),
                    hovertemplate="Recency: %{x} days<br>Spend: $%{y:,.0f}<br>" + segment + "<extra></extra>",
                )
            )
        fig.update_layout(title="Recency vs. spend (bubble size = order frequency)")
        fig.update_xaxes(title="Days since last purchase")
        fig.update_yaxes(title="Total spend (USD)")
        st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)

    with c8:
        seg_summary = (
            rfm.groupby("segment")
            .agg(customers=("customer_id", "count"), avg_spend=("total_spend_usd", "mean"), churn_rate=("churned", "mean"))
            .reindex(["Champions", "Loyal", "At risk", "Lost"])
            .reset_index()
        )
        seg_summary["avg_spend"] = seg_summary["avg_spend"].map(lambda v: f"${v:,.0f}")
        seg_summary["churn_rate"] = seg_summary["churn_rate"].map(lambda v: f"{v:.1%}")
        st.dataframe(seg_summary, use_container_width=True, hide_index=True)

# ===========================================================================
# TAB 3 — PRODUCTS & RETURNS (respects sidebar filters)
# ===========================================================================
with tab_products:
    st.subheader("Products & returns")
    st.caption("Respects the filters selected in the sidebar.")

    # --- problem products: return rate vs revenue -------------------------
    by_product = (
        filtered.groupby("product_name")
        .agg(revenue=("total_amount_usd", "sum"), return_rate=("returned", "mean"), orders=("order_id", "count"))
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(30)
    )
    colors = [STATUS_CRITICAL if r > 0.15 else BLUE for r in by_product["return_rate"]]
    fig = go.Figure(
        go.Scatter(
            x=by_product["revenue"],
            y=by_product["return_rate"],
            mode="markers",
            marker=dict(color=colors, size=10, opacity=0.75),
            text=by_product["product_name"],
            hovertemplate="%{text}<br>Revenue: $%{x:,.0f}<br>Return rate: %{y:.1%}<extra></extra>",
        )
    )
    fig.update_layout(title="Return rate vs. revenue (top 30 products by revenue)")
    fig.update_xaxes(title="Revenue (USD)")
    fig.update_yaxes(title="Return rate", tickformat=".0%")
    st.plotly_chart(style_fig(fig, height=420), use_container_width=True)
    st.caption(f"Highlighted in red: products with return rate above 15%.")

    c9, c10 = st.columns(2)
    with c9:
        by_discount = (
            filtered.groupby("discount_pct")
            .agg(aov=("total_amount_usd", "mean"), return_rate=("returned", "mean"))
            .reset_index()
            .sort_values("discount_pct")
        )
        fig = go.Figure(
            go.Bar(
                x=by_discount["discount_pct"].astype(str) + "%",
                y=by_discount["aov"],
                marker_color=AQUA,
                hovertemplate="Discount: %{x}<br>Avg order value: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.update_layout(title="Avg order value by discount level", bargap=0.25)
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    with c10:
        fig = go.Figure(
            go.Bar(
                x=by_discount["discount_pct"].astype(str) + "%",
                y=by_discount["return_rate"],
                marker_color=ORANGE,
                hovertemplate="Discount: %{x}<br>Return rate: %{y:.1%}<extra></extra>",
            )
        )
        fig.update_layout(title="Return rate by discount level", bargap=0.25)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    c11, c12 = st.columns(2)
    with c11:
        delivery_bins = pd.cut(
            filtered["delivery_days"],
            bins=[0, 3, 6, 9, 14],
            labels=["1–3 days", "4–6 days", "7–9 days", "10–14 days"],
        )
        by_delivery = filtered.assign(delivery_bucket=delivery_bins).groupby("delivery_bucket", observed=True)[
            "customer_rating"
        ].mean()
        fig = go.Figure(
            go.Bar(
                x=by_delivery.index.astype(str),
                y=by_delivery.values,
                marker_color=BLUE,
                hovertemplate="%{x}<br>Avg rating: %{y:.2f}<extra></extra>",
            )
        )
        fig.update_layout(title="Avg customer rating by delivery time", bargap=0.3)
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    with c12:
        by_cat_return = filtered.groupby("category")["returned"].mean().sort_values(ascending=True)
        fig = go.Figure(
            go.Bar(
                x=by_cat_return.values,
                y=by_cat_return.index,
                orientation="h",
                marker_color=MAGENTA,
                hovertemplate="%{y}<br>Return rate: %{x:.1%}<extra></extra>",
            )
        )
        fig.update_layout(title="Return rate by category")
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

# ===========================================================================
# TAB 4 — FUNNEL & ENGAGEMENT (respects sidebar filters)
# ===========================================================================
with tab_funnel:
    st.subheader("Funnel & engagement")
    st.caption("Respects the filters selected in the sidebar.")

    c13, c14 = st.columns(2)
    with c13:
        fig = go.Figure(
            go.Histogram(
                x=filtered["session_duration_minutes"],
                marker_color=BLUE,
                nbinsx=30,
                hovertemplate="Session length: %{x} min<br>Orders: %{y}<extra></extra>",
            )
        )
        fig.update_layout(title="Session duration before purchase", bargap=0.05)
        fig.update_xaxes(title="Minutes")
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with c14:
        fig = go.Figure(
            go.Histogram(
                x=filtered["pages_viewed_before_purchase"],
                marker_color=AQUA,
                nbinsx=20,
                hovertemplate="Pages viewed: %{x}<br>Orders: %{y}<extra></extra>",
            )
        )
        fig.update_layout(title="Pages viewed before purchase", bargap=0.05)
        fig.update_xaxes(title="Pages")
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    c15, c16 = st.columns(2)
    with c15:
        by_repeat = filtered["is_repeat_customer"].map({0: "New", 1: "Returning"}).value_counts()
        fig = go.Figure(
            go.Pie(
                labels=by_repeat.index,
                values=by_repeat.values,
                hole=0.6,
                marker=dict(colors=[REPEAT_COLORS.get(l, INK_MUTED) for l in by_repeat.index]),
                textfont=dict(color=INK_PRIMARY),
                hovertemplate="%{label}<br>Orders: %{value:,} (%{percent})<extra></extra>",
            )
        )
        fig.update_layout(title="New vs. returning customer orders")
        st.plotly_chart(style_fig(fig, height=340, showlegend=True), use_container_width=True)

    with c16:
        by_status = filtered["order_status"].value_counts().reindex(list(STATUS_COLORS.keys())).dropna()
        fig = go.Figure(
            go.Bar(
                x=by_status.values,
                y=by_status.index,
                orientation="h",
                marker_color=[STATUS_COLORS[s] for s in by_status.index],
                hovertemplate="%{y}<br>Orders: %{x:,}<extra></extra>",
            )
        )
        fig.update_layout(title="Orders by status")
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    st.divider()

    c17, c18 = st.columns(2)
    with c17:
        by_dow = filtered["day_of_week"].value_counts().reindex(DAY_ORDER)
        fig = go.Figure(
            go.Bar(
                x=by_dow.index,
                y=by_dow.values,
                marker_color=VIOLET,
                hovertemplate="%{x}<br>Orders: %{y:,}<extra></extra>",
            )
        )
        fig.update_layout(title="Orders by day of week", bargap=0.3)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with c18:
        by_quarter = filtered.groupby("quarter")["total_amount_usd"].sum().reindex(["Q1", "Q2", "Q3", "Q4"])
        fig = go.Figure(
            go.Bar(
                x=by_quarter.index,
                y=by_quarter.values,
                marker_color=YELLOW,
                hovertemplate="%{x}<br>Revenue: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(title="Revenue by quarter (all selected years)", bargap=0.3)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

# ===========================================================================
# TAB 5 — GEOGRAPHY & DEMOGRAPHICS (full customer base, not affected by filters)
# ===========================================================================
with tab_geo:
    st.subheader("Geography & demographics")
    unfiltered_caption()

    by_country = customers.groupby("country")["total_spend_usd"].sum().sort_values(ascending=True).tail(12)
    fig = go.Figure(
        go.Bar(
            x=by_country.values,
            y=by_country.index,
            orientation="h",
            marker_color=BLUE,
            hovertemplate="%{y}<br>Total spend: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(title="Total spend by country (top 12)")
    st.plotly_chart(style_fig(fig, height=420), use_container_width=True)

    c19, c20 = st.columns(2)
    with c19:
        age_bins = pd.cut(
            customers["age"],
            bins=[17, 24, 34, 44, 54, 64, 75],
            labels=["18–24", "25–34", "35–44", "45–54", "55–64", "65–75"],
        )
        by_age = customers.assign(age_bucket=age_bins).groupby("age_bucket", observed=True)["total_spend_usd"].mean()
        fig = go.Figure(
            go.Bar(
                x=by_age.index.astype(str),
                y=by_age.values,
                marker_color=AQUA,
                hovertemplate="%{x}<br>Avg spend: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(title="Avg spend by age group", bargap=0.3)
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    with c20:
        by_gender = customers.groupby("gender")["total_spend_usd"].mean()
        fig = go.Figure(
            go.Bar(
                x=by_gender.index,
                y=by_gender.values,
                marker_color=[GENDER_COLORS.get(g, INK_MUTED) for g in by_gender.index],
                hovertemplate="%{x}<br>Avg spend: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(title="Avg spend by gender", bargap=0.4)
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    st.divider()

    c21, c22 = st.columns(2)
    with c21:
        by_news = customers.groupby("newsletter_subscribed")["churned"].mean()
        by_news.index = by_news.index.map({0: "Not subscribed", 1: "Subscribed"})
        fig = go.Figure(
            go.Bar(
                x=by_news.index,
                y=by_news.values,
                marker_color=[INK_MUTED, AQUA],
                hovertemplate="%{x}<br>Churn rate: %{y:.1%}<extra></extra>",
            )
        )
        fig.update_layout(title="Churn rate by newsletter subscription", bargap=0.4)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with c22:
        by_news_spend = customers.groupby("newsletter_subscribed")["total_spend_usd"].mean()
        by_news_spend.index = by_news_spend.index.map({0: "Not subscribed", 1: "Subscribed"})
        fig = go.Figure(
            go.Bar(
                x=by_news_spend.index,
                y=by_news_spend.values,
                marker_color=[INK_MUTED, BLUE],
                hovertemplate="%{x}<br>Avg spend: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(title="Avg spend by newsletter subscription", bargap=0.4)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)
