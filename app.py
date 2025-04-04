import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

from agreement import check_user_agreement
from util import load_data_from_file, load_default_data, clear_cache

st.set_page_config(page_title="My Dashboard", page_icon="📊")

# Privacy policy and terms of use
check_user_agreement()

# Title
# st.title("📊 Money Manager Dashboard")
st.markdown("### 📊 [Money Manager](https://www.realbyteapps.com/) Dashboard")


# --- File upload or default data ---
st.sidebar.markdown("## 📁 Data Source")
data_option = st.sidebar.radio(
    "Choose data source:", ("Use sample data", "Upload Excel file")
)

if data_option == "Upload Excel file":
    uploaded_file = st.sidebar.file_uploader("Upload your .xlsx file", type="xlsx")
    if uploaded_file is None:
        st.warning("Please upload a file to continue.")
        st.warning(
            "Your data remains private and is automatically deleted after the analysis.",
            icon="⚠️",
        )
        st.info(
        """Please, download your data from the Money Manager app and upload the XLSX file.

        How to Download Your Data 🤔

        1. Open the app.
        2. Go to "More" in the bottom right corner.
        3. Tap "Backup".
        4. Tap "Export data to Excel".
        5. Tap "Total" or whatever you want.
        6. Upload the XLSX file via the sidebar on the left , and Voilà! 🎉
        """,
        icon="ℹ️"
    )

        st.stop()
    df = load_data_from_file(uploaded_file)
else:
    df = load_default_data()

# --- Data preparation ---
# Remove the "Note" column if it exists
if "Note" in df.columns:
    df.drop(columns=["Note"], inplace=True)

# Sidebar filters
st.sidebar.header("Filters")
today = datetime.today()
today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)

tab0, tab1, tab2 = st.tabs(
    [
        "📂 Expenses by Category",
        "📈 Monthly Avg by Category",
        "🔍 Category ➝ Subcategory Drilldown",
    ]
)

# Determine default date filter
default_date_filter = "This month"
date_filter = st.sidebar.selectbox(
    "Select date range",
    ["This month", "This year", "Last + This year", "Custom"],
    index=["This month", "This year", "Last + This year", "Custom"].index(
        default_date_filter
    ),
)

if date_filter == "This month":
    start_date = today_start.replace(day=1)
    end_date = today
elif date_filter == "This year":
    start_date = today_start.replace(month=1, day=1)
    end_date = today
elif date_filter == "Last + This year":
    start_date = today_start.replace(year=today.year - 1, month=1, day=1)
    end_date = today
else:
    start_date = st.sidebar.date_input("Start date", today_start.replace(month=1, day=1))
    end_date = st.sidebar.date_input("End date", today)

# Filter by date
df = df[
    (df["Period"] >= pd.to_datetime(start_date))
    & (df["Period"] <= pd.to_datetime(end_date))
]

# Separate categories by type
expense_categories = df[df["Income/Expense"] == "Exp."]["Category"].unique()
income_categories = df[df["Income/Expense"] == "Income"]["Category"].unique()


# Sort categories ignoring emojis
def sort_key(label):
    return re.sub(r"[^\w\s]", "", label).strip().lower()


# Account and category filters
raw_accounts = sorted(df["Accounts"].unique().tolist())
account_options = ["All"] + raw_accounts
selected_accounts_raw = st.sidebar.multiselect(
    "Select accounts", options=account_options, default=["All"]
)
selected_accounts = ["All"] if "All" in selected_accounts_raw else selected_accounts_raw

all_categories = sorted([cat for cat in expense_categories], key=sort_key)
category_options = ["All"] + all_categories
selected_categories_raw = st.sidebar.multiselect(
    "Select categories", options=category_options, default=["All"]
)
selected_categories = (
    ["All"] if "All" in selected_categories_raw else selected_categories_raw
)

# Check if nothing is selected
if not selected_accounts_raw or not selected_categories_raw:
    st.error("❌ Please select at least one account and one category.")
    st.stop()

# Apply filters
filtered_df = df.copy()
if "All" not in selected_accounts:
    filtered_df = filtered_df[filtered_df["Accounts"].isin(selected_accounts)]
if "All" not in selected_categories:
    filtered_df = filtered_df[filtered_df["Category"].isin(selected_categories)]

# Check if filters exclude all data
if filtered_df.empty:
    st.error("❌ No data matches your selected filters.")
    st.stop()

# Totals
total_expenses = filtered_df[filtered_df["Income/Expense"] == "Exp."]["Amount"].sum()
total_incomes = filtered_df[filtered_df["Income/Expense"] == "Income"]["Amount"].sum()
diff = total_incomes - total_expenses

# Show totals in sidebar
st.sidebar.markdown("### Totals")
st.sidebar.markdown(f"**💸 Expenses:** € {total_expenses:,.2f}")
st.sidebar.markdown(f"**💰 Incomes:** € {total_incomes:,.2f}")
st.sidebar.markdown(f"**📊 Net:** € {diff:,.2f}")

with tab0:
    exp_df = filtered_df[filtered_df["Income/Expense"] == "Exp."]
    category_totals = (
        exp_df.groupby("Category")["Amount"]
        .sum()
        .reset_index()
        .sort_values(by="Amount", ascending=False)
    )
    fig = px.bar(
        category_totals,
        x="Category",
        y="Amount",
        color="Category",
        title=f'Expenses by Category ({start_date.strftime("%d %B %Y")} to {end_date.strftime("%d %B %Y")})',
        labels={"Amount": "Total"},
    )
    st.plotly_chart(fig, use_container_width=True)

with tab1:
    exp_df = filtered_df[filtered_df["Income/Expense"] == "Exp."]
    exp_df["Month"] = exp_df["Period"].dt.to_period("M").dt.to_timestamp()

    num_months = len(exp_df["Month"].dt.to_period("M").unique())
    if num_months <= 1:
        st.warning(
            "You selected only one month. Computing an average doesn't make much sense.",
            icon="⚠️",
        )

    if num_months > 0:
        total_per_category = exp_df.groupby("Category")["Amount"].sum().reset_index()
        total_per_category["Monthly Average"] = (
            total_per_category["Amount"] / num_months
        )
        total_per_category = total_per_category.sort_values(
            by="Monthly Average", ascending=False
        )

        fig = px.bar(
            total_per_category,
            x="Category",
            y="Monthly Average",
            color="Category",
            labels={"Monthly Average": "Avg Expense per Month"},
            title=f'Average Monthly Expense per Category ({start_date.strftime("%d %B %Y")} to {end_date.strftime("%d %B %Y")})',
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader(
        f"Drilldown by Category and Subcategory ({start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')})"
    )

    # Get list of categories
    drilldown_categories = sorted(exp_df["Category"].unique(), key=sort_key)
    selected_drilldown_cat = st.selectbox(
        "Choose a category", options=drilldown_categories
    )

    # Filter to selected category
    cat_df = exp_df[exp_df["Category"] == selected_drilldown_cat]

    # Check if subcategories exist (not all None/NaN)
    if "Subcategory" in cat_df.columns and cat_df["Subcategory"].notna().any():
        subcat_df = cat_df[cat_df["Subcategory"].notna()]
        subcat_totals = (
            subcat_df.groupby("Subcategory")["Amount"]
            .sum()
            .reset_index()
            .sort_values(by="Amount", ascending=False)
        )

        fig = px.bar(
            subcat_totals,
            x="Subcategory",
            y="Amount",
            color="Subcategory",
            labels={"Amount": "Total"},
            title=f"Subcategory Breakdown for {selected_drilldown_cat}",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("This category has no subcategories.", icon="ℹ️")

    # Show raw transactions regardless
    st.markdown("### 💡 Transactions")
    st.dataframe(
        cat_df[
            ["Period", "Subcategory", "Accounts", "Amount", "Description"]
        ].sort_values(by="Period", ascending=False),
        use_container_width=True,
    )

# Clear cache
clear_cache()
