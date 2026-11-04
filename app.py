import pandas as pd
import plotly.express as px
import streamlit as st

# PAGE SETTINGS
st.set_page_config(page_title="Sales Analysis", page_icon="📊", layout="wide")

TEAL = "#6FA6A0"
DARK = "#425B57"
PALETTE = [TEAL, "#B8D3C5", "#D9C6B0", "#A9BBD0"]

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"]


# CHART FUNCTION
def show(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FAFBF9",
        plot_bgcolor="#F3F7F4",
        font=dict(color=DARK),
        margin=dict(l=20, r=20, t=50, b=30)
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2EBE5")
    fig.update_yaxes(showgrid=True, gridcolor="#E2EBE5")
    st.plotly_chart(fig, width="stretch")


# DATA CLEANING
@st.cache_data
def load_data(raw):
    report = {"Original rows": len(raw)}
    df = raw.drop(columns="Unnamed: 0", errors="ignore").copy()

    df["Quantity Ordered"] = pd.to_numeric(
        df["Quantity Ordered"], errors="coerce"
    )
    df["Price Each"] = pd.to_numeric(
        df["Price Each"], errors="coerce"
    )
    df["Order Date"] = pd.to_datetime(
        df["Order Date"], errors="coerce"
    )

    before = len(df)
    df = df.dropna(subset=[
        "Order ID", "Product", "Quantity Ordered",
        "Price Each", "Order Date", "Purchase Address"
    ])
    report["Missing/invalid rows removed"] = before - len(df)

    before = len(df)
    df = df.drop_duplicates()
    report["Duplicate rows removed"] = before - len(df)

    before = len(df)
    df = df[df["Order Date"].dt.year == 2019].copy()
    report["Rows outside 2019 removed"] = before - len(df)

    df["Sales"] = df["Quantity Ordered"] * df["Price Each"]
    df["Month"] = df["Order Date"].dt.month_name()
    df["Hour"] = df["Order Date"].dt.hour
    df["Weekday"] = df["Order Date"].dt.day_name()

    address = df["Purchase Address"].str.split(",", expand=True)
    df["City"] = (
        address[1].str.strip() + " (" +
        address[2].str.strip().str[:2] + ")"
    )

    report["Final rows"] = len(df)
    return df, report


# LOAD FILE
st.title("Electronics Store Sales Analysis")
st.caption("An interactive analysis of electronics sales during 2019.")

uploaded = st.sidebar.file_uploader("Upload Sales Data.csv", type="csv")

try:
    raw = pd.read_csv(uploaded) if uploaded else pd.read_csv("Sales Data.csv")
except FileNotFoundError:
    st.error("Sales Data.csv must be in the same folder as app.py.")
    st.stop()

df, report = load_data(raw)

if df.empty:
    st.error("No valid 2019 records found.")
    st.stop()


# SIDEBAR FILTERS
st.sidebar.title("Sales Filters")

months = st.sidebar.multiselect("Month", MONTHS, default=MONTHS)

city_options = sorted(df["City"].unique())
cities = st.sidebar.multiselect(
    "City", city_options, default=city_options
)

product_options = sorted(df["Product"].unique())
products = st.sidebar.multiselect(
    "Product", product_options, default=product_options
)

filtered = df[
    df["Month"].isin(months) &
    df["City"].isin(cities) &
    df["Product"].isin(products)
]

if filtered.empty:
    st.warning("No records match your filters. Please change your selections.")
    st.stop()

orders = filtered.groupby("Order ID")["Sales"].sum().reset_index()

dashboard, cleaning = st.tabs([
    "📊 Sales Dashboard", "🧹 Data Cleaning"
])


# ==================================================
# SALES DASHBOARD
# ==================================================

with dashboard:

    # KEY METRICS
    st.subheader("Sales Overview")
    cols = st.columns(4)

    metrics = [
        ("Total Sales", f"${filtered['Sales'].sum():,.2f}"),
        ("Number of Orders", f"{filtered['Order ID'].nunique():,}"),
        ("Items Sold", f"{filtered['Quantity Ordered'].sum():,}"),
        ("Average Order Value", f"${orders['Sales'].mean():,.2f}")
    ]

    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    st.divider()

    # MAIN RESEARCH QUESTIONS
    st.subheader("Sales Performance")

    monthly = filtered.groupby("Month")["Sales"].sum().reindex(MONTHS).dropna()
    city_sales = filtered.groupby("City")["Sales"].sum().sort_values(ascending=False)
    hourly = filtered.groupby("Hour")["Sales"].sum()
    product_sales = filtered.groupby("Product")["Sales"].sum().sort_values(ascending=False)

    questions = [
        (
            "1. Which month had the highest sales?",
            px.bar(monthly.rename_axis("Month").reset_index(),
                   x="Month", y="Sales", color_discrete_sequence=[TEAL]),
            f"{monthly.idxmax()} had the highest sales: ${monthly.max():,.2f}."
        ),
        (
            "2. Which city had the highest sales?",
            px.bar(city_sales.rename_axis("City").reset_index().sort_values("Sales"),
                   x="Sales", y="City", orientation="h",
                   color_discrete_sequence=[TEAL]),
            f"{city_sales.idxmax()} had the highest sales: ${city_sales.max():,.2f}."
        ),
        (
            "3. During which hour were sales highest?",
            px.line(hourly.rename_axis("Hour").reset_index(),
                    x="Hour", y="Sales", markers=True,
                    color_discrete_sequence=[TEAL]),
            f"The highest sales occurred at {hourly.idxmax()}:00."
        ),
        (
            "4. Which product generated the highest sales?",
            px.bar(product_sales.rename_axis("Product").reset_index().sort_values("Sales"),
                   x="Sales", y="Product", orientation="h",
                   color_discrete_sequence=[TEAL]),
            f"{product_sales.idxmax()} generated the highest sales."
        ),
        (
            "5. How much do customers spend per order?",
            px.histogram(orders, x="Sales", nbins=40,
                         color_discrete_sequence=[TEAL]),
            f"Average: ${orders['Sales'].mean():,.2f} | "
            f"Median: ${orders['Sales'].median():,.2f}."
        )
    ]

    for title, fig, insight in questions:
        st.markdown(f"**{title}**")
        show(fig)
        st.caption(insight)

    st.markdown("**Top-selling products by quantity**")

    sold = (
        filtered.groupby("Product")["Quantity Ordered"]
        .sum().sort_values(ascending=False)
        .rename_axis("Product").reset_index(name="Quantity Sold")
    )
    st.dataframe(sold, hide_index=True, width="stretch")

    st.divider()

    # ADDITIONAL RESEARCH QUESTIONS
    st.subheader("Additional Research Questions")

    left, right = st.columns(2)

    weekday = filtered.groupby("Weekday")["Sales"].sum().reindex(DAYS).dropna()

    with left:
        st.markdown("**6. Which weekday had the highest sales?**")
        show(px.bar(weekday.rename_axis("Weekday").reset_index(),
                    x="Weekday", y="Sales",
                    color_discrete_sequence=[TEAL]))
        st.caption(f"{weekday.idxmax()} recorded the highest sales.")

    average_quantity = (
        filtered.groupby(["Order ID", "Product"])["Quantity Ordered"]
        .sum().groupby("Product").mean()
        .sort_values(ascending=False)
    )

    with right:
        st.markdown("**7. Which product had the highest average quantity per order?**")

        average_df = (
            average_quantity.rename_axis("Product")
            .reset_index(name="Average Quantity")
        )

        show(px.bar(
            average_df.sort_values("Average Quantity"),
            x="Average Quantity",
            y="Product",
            orientation="h",
            color_discrete_sequence=[TEAL]
        ))

        st.caption(
            f"{average_quantity.idxmax()} had the highest average quantity: "
            f"{average_quantity.max():.2f}."
        )

    st.divider()

    # UNIVARIATE ANALYSIS
    st.subheader("Univariate Analysis")
    st.write("Distribution and frequency of individual variables.")

    product_count = (
        filtered["Product"].value_counts()
        .rename_axis("Product").reset_index(name="Count")
    )
    city_count = (
        filtered["City"].value_counts()
        .rename_axis("City").reset_index(name="Count")
    )
    month_count = (
        filtered["Month"].value_counts()
        .reindex(MONTHS).dropna()
        .rename_axis("Month").reset_index(name="Count")
    )
    hour_count = (
        filtered["Hour"].value_counts().sort_index()
        .rename_axis("Hour").reset_index(name="Count")
    )

    univariate = [
        ("1. Quantity Ordered Distribution",
         px.histogram(filtered, x="Quantity Ordered",
                      color_discrete_sequence=[TEAL]),
         "Most records contain relatively small quantities."),

        ("2. Product Price Distribution",
         px.histogram(filtered, x="Price Each", nbins=40,
                      color_discrete_sequence=[TEAL]),
         "Product prices vary across different electronics."),

        ("3. Sales Distribution",
         px.histogram(filtered, x="Sales", nbins=50,
                      color_discrete_sequence=[TEAL]),
         "Most sales records have lower values than the largest purchases."),

        ("4. Orders by Product",
         px.bar(product_count, x="Product", y="Count",
                color_discrete_sequence=[TEAL]),
         "Product counts show how frequently each product appears."),

        ("5. Orders by City",
         px.bar(city_count, x="City", y="Count",
                color_discrete_sequence=[TEAL]),
         "Order records are distributed across different cities."),

        ("6. Orders by Month",
         px.bar(month_count, x="Month", y="Count",
                color_discrete_sequence=[TEAL]),
         "Monthly counts show changes in customer activity."),

        ("7. Orders by Hour",
         px.bar(hour_count, x="Hour", y="Count",
                color_discrete_sequence=[TEAL]),
         "Hourly counts show when customers are most active.")
    ]

    for title, fig, insight in univariate:
        st.markdown(f"**{title}**")
        show(fig)
        st.caption(insight)

    st.divider()

    # BIVARIATE ANALYSIS
    st.subheader("Bivariate Analysis")
    st.write("Relationships between two variables.")

    city_orders = (
        filtered.groupby(["City", "Order ID"])["Sales"].sum()
        .groupby("City").mean()
        .reset_index(name="Average Order Sales")
    )

    product_quantity = (
        filtered.groupby("Product")["Quantity Ordered"]
        .sum().rename_axis("Product")
        .reset_index(name="Quantity Sold")
    )

    monthly_hourly = (
        filtered.groupby(["Month", "Hour"])["Sales"]
        .sum().reset_index()
    )

    weekday_month = (
        filtered.groupby(["Month", "Weekday"])["Sales"]
        .sum().reset_index()
    )

    bivariate = [
        (
            "1. Average order sales by city",
            px.bar(city_orders, x="City", y="Average Order Sales",
                   color_discrete_sequence=[TEAL]),
            "Average order values differ between cities."
        ),
        (
            "2. Quantity sold by product",
            px.bar(product_quantity, x="Product", y="Quantity Sold",
                   color_discrete_sequence=[TEAL]),
            "This comparison identifies products with higher demand."
        ),
        (
            "3. Sales by month and hour",
            px.line(monthly_hourly, x="Hour", y="Sales", color="Month",
                    markers=True, color_discrete_sequence=PALETTE),
            "Sales activity changes across months and hours."
        ),
        (
            "4. Product price and quantity purchased",
            px.scatter(filtered, x="Price Each", y="Quantity Ordered",
                       color="Product", color_discrete_sequence=PALETTE),
            "The chart compares product prices with quantities ordered."
        ),
        (
            "5. Sales by weekday and month",
            px.bar(weekday_month, x="Weekday", y="Sales", color="Month",
                   color_discrete_sequence=PALETTE),
            "This comparison shows how weekday sales vary between months."
        )
    ]

    for title, fig, insight in bivariate:
        st.markdown(f"**{title}**")
        show(fig)
        st.caption(insight)

    st.divider()

    # CONCLUSION
    st.subheader("Conclusion")

    st.write(
        f"- Total sales were ${filtered['Sales'].sum():,.2f}.\n"
        f"- The dataset contains {filtered['Order ID'].nunique():,} orders.\n"
        f"- Customers purchased {filtered['Quantity Ordered'].sum():,} items.\n"
        f"- {monthly.idxmax()} was the highest-sales month.\n"
        f"- {city_sales.idxmax()} was the highest-sales city."
    )


# ==================================================
# DATA CLEANING TAB
# ==================================================

with cleaning:

    st.subheader("Data Cleaning Summary")
    st.write("The dataset was cleaned before analysis.")

    st.table(
        pd.DataFrame(
            list(report.items()),
            columns=["Cleaning Step", "Rows"]
        ).set_index("Cleaning Step")
    )

    st.info(
        "The extra index column was removed. Missing values, invalid "
        "records, duplicates and records outside 2019 were handled. "
        "Sales, Month, Hour, Weekday and City columns were created."
    )

    st.divider()

    # OUTLIER ANALYSIS
    st.subheader("Outlier Analysis")

    left, right = st.columns(2)

    with left:
        show(px.box(
            df, y="Quantity Ordered",
            title="Quantity Ordered Outliers",
            color_discrete_sequence=[TEAL]
        ))

    with right:
        show(px.box(
            df, y="Sales",
            title="Sales Outliers",
            color_discrete_sequence=[TEAL]
        ))

    st.write(
        "Box plots help identify unusually high values in quantities "
        "and sales. These values may represent genuine large orders "
        "rather than errors."
    )

    st.info(
        "Decision: Genuine high-value sales and large quantities are "
        "retained because they may represent actual customer purchases. "
        "Only confirmed data errors should be removed."
    )

    st.divider()

    # CLEANED DATASET
    st.subheader("Cleaned Dataset")
    st.dataframe(df.head(100), hide_index=True, width="stretch")

    st.download_button(
        "Download Cleaned Data",
        df.to_csv(index=False),
        "cleaned_sales_data.csv",
        "text/csv"
    )