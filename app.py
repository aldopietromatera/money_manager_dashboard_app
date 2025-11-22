import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np

from agreement import check_user_agreement
from util import (
    load_data_from_file,
    load_default_data,
    clear_cache,
    count_months,
)

# --------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------
st.set_page_config(page_title="My Dashboard", page_icon="📊")

# Show privacy/terms modal
check_user_agreement()

# Title
st.markdown("### 📊 [Money Manager](https://www.realbyteapps.com/) Dashboard")

# --------------------------------------------------------------------
# Sidebar: Data source
# --------------------------------------------------------------------
st.sidebar.markdown("## 📁 Data Source")
DATA_SOURCE_OPTIONS = ("Use sample data", "Upload Excel file")
data_option = st.sidebar.radio("Choose data source:", DATA_SOURCE_OPTIONS)

# --------------------------------------------------------------------
# Load data
# --------------------------------------------------------------------
if data_option == "Upload Excel file":
    uploaded_file = st.sidebar.file_uploader("Upload your .xlsx file", type="xlsx")

    # Stop until a file is uploaded
    if uploaded_file is None:
        st.warning("Please upload a file to continue.")
        st.warning(
            "Your data stays private and is removed after processing.",
            icon="⚠️",
        )
        st.info(
            """How to export data from Money Manager:

1. Open the app  
2. Go to *More*  
3. Tap *Backup*  
4. Select *Export data to Excel*  
5. Pick *Total*  
6. Upload the file here  
            """,
            icon="ℹ️",
        )
        st.stop()

    df = load_data_from_file(uploaded_file)
else:
    # Load sample file and shift dates
    df = load_default_data()

# Remove notes if present
if "Note" in df.columns:
    df = df.drop(columns=["Note"])

# Ensure Period exists
if "Period" not in df.columns:
    st.error("❌ The data must contain a 'Period' column.")
    st.stop()

# --------------------------------------------------------------------
# Sidebar: Filters
# --------------------------------------------------------------------
st.sidebar.header("Filters")

today = datetime.today()
today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)

DATE_FILTER_OPTIONS = ["This month", "This year", "Last + This year", "Custom"]

date_filter = st.sidebar.selectbox("Select date range", DATE_FILTER_OPTIONS)

# Compute date range
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
    start_date = st.sidebar.date_input(
        "Start date", today_start.replace(month=1, day=1)
    )
    end_date = st.sidebar.date_input("End date", today)

start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# Apply date filter
df = df[(df["Period"] >= start_date) & (df["Period"] <= end_date)]

if df.empty:
    st.error("❌ No data found in the selected date range.")
    st.stop()


# Helper to sort labels ignoring emojis
def sort_key(label: str) -> str:
    return re.sub(r"[^\w\s]", "", str(label)).strip().lower()


# Build category lists
expense_categories = df[df["Income/Expense"] == "Exp."]["Category"].unique()
income_categories = df[df["Income/Expense"] == "Income"]["Category"].unique()

# Accounts filter
raw_accounts = sorted(df["Accounts"].dropna().unique().tolist())
account_options = ["All"] + raw_accounts

selected_accounts_raw = st.sidebar.multiselect(
    "Select accounts", options=account_options, default=["All"]
)
selected_accounts = ["All"] if "All" in selected_accounts_raw else selected_accounts_raw

# Expense category filter
all_expense_categories = sorted(list(expense_categories), key=sort_key)
category_options = ["All"] + all_expense_categories

selected_categories_raw = st.sidebar.multiselect(
    "Select categories (expenses)",
    options=category_options,
    default=["All"],
)
selected_categories = (
    ["All"] if "All" in selected_categories_raw else selected_categories_raw
)

# Validate selections
if not selected_accounts_raw or not selected_categories_raw:
    st.error("❌ Please select at least one account and one category.")
    st.stop()

# Apply filters
filtered_df = df.copy()

if "All" not in selected_accounts:
    filtered_df = filtered_df[filtered_df["Accounts"].isin(selected_accounts)]

if "All" not in selected_categories:
    filtered_df = filtered_df[filtered_df["Category"].isin(selected_categories)]

if filtered_df.empty:
    st.error("❌ No data matches your selected filters.")
    st.stop()

# --------------------------------------------------------------------
# Sidebar totals
# --------------------------------------------------------------------
total_expenses = filtered_df[filtered_df["Income/Expense"] == "Exp."]["EUR"].sum()
total_incomes = filtered_df[filtered_df["Income/Expense"] == "Income"]["EUR"].sum()
diff = total_incomes - total_expenses

st.sidebar.markdown("### Totals")
st.sidebar.markdown(f"**💸 Expenses:** € {total_expenses:,.2f}")
st.sidebar.markdown(f"**💰 Incomes:** € {total_incomes:,.2f}")
st.sidebar.markdown(f"**📊 Net:** € {diff:,.2f}")

# --------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------
tab0, tab1, tab2, tab3 = st.tabs(
    [
        "📂 Expenses by Category",
        "📈 Monthly Avg by Category",
        "📈 Monthly Overview",
        "🔍 Category ➝ Subcategory Drilldown",
    ]
)

# --------------------------------------------------------------------
# Tab 0: Expenses by Category
# --------------------------------------------------------------------
with tab0:
    exp_df = filtered_df[filtered_df["Income/Expense"] == "Exp."]

    if exp_df.empty:
        st.info("No expenses in the selected period.")
    else:
        # Sum by category
        category_totals = (
            exp_df.groupby("Category", as_index=False)["EUR"]
            .sum()
            .sort_values(by="EUR", ascending=False)
        )

        # Bar chart
        fig = px.bar(
            category_totals,
            x="Category",
            y="EUR",
            color="Category",
            title=f"Expenses by Category ({start_date.strftime('%d %B %Y')} to {end_date.strftime('%d %B %Y')})",
            labels={"EUR": "Total (€)"},
        )
        st.plotly_chart(fig, width="stretch")

        # Donut chart
        fig_donut = px.pie(
            category_totals,
            names="Category",
            values="EUR",
            hole=0.4,
            title=f"Expense Distribution by Category (%) ({start_date.strftime('%d %B %Y')} to {end_date.strftime('%d %B %Y')})",
        )
        st.plotly_chart(fig_donut, width="stretch")


# --------------------------------------------------------------------
# Tab 1: Monthly Avg by Category
# --------------------------------------------------------------------
with tab1:
    exp_df = filtered_df[filtered_df["Income/Expense"] == "Exp."]

    if exp_df.empty:
        st.info("No expenses in the selected period.")
    else:
        num_months = count_months(exp_df)

        # Warnings for low month count
        if num_months == 0:
            st.warning("No monthly data found for expenses.", icon="⚠️")
        elif num_months == 1:
            st.warning("Only one month selected.", icon="⚠️")

        if num_months >= 1:
            # Total + average per category
            totals = (
                exp_df.groupby("Category", as_index=False)["EUR"]
                .sum()
                .sort_values(by="EUR", ascending=False)
            )
            totals["Monthly Average"] = totals["EUR"] / num_months

            fig = px.bar(
                totals,
                x="Category",
                y="Monthly Average",
                color="Category",
                labels={"Monthly Average": "Avg Expense per Month (€)"},
                title=f"Average Monthly Expense per Category ({start_date.strftime('%d %B %Y')} to {end_date.strftime('%d %B %Y')})",
            )
            st.plotly_chart(fig, width="stretch")


# --------------------------------------------------------------------
# Tab 2: Monthly Overview
# --------------------------------------------------------------------
with tab2:
    st.subheader(
        f"Monthly Overview ({start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')})"
    )

    df_monthly = filtered_df.copy()
    df_monthly["Month"] = df_monthly["Period"].dt.to_period("M").dt.to_timestamp()

    num_months = count_months(df_monthly)

    if num_months == 0:
        st.warning("No monthly data found.", icon="⚠️")
    else:
        if num_months == 1:
            st.warning("Only one month selected.", icon="⚠️")

        # Build expenses/incomes/net per month
        monthly_totals = (
            df_monthly.groupby("Month", group_keys=False)
            .apply(
                lambda x: pd.Series(
                    {
                        "Expenses": x[x["Income/Expense"] == "Exp."]["EUR"].sum(),
                        "Incomes": x[x["Income/Expense"] == "Income"]["EUR"].sum(),
                    }
                ),
                include_groups=False,
            )
            .reset_index()
        )

        monthly_totals["Net"] = monthly_totals["Incomes"] - monthly_totals["Expenses"]
        monthly_totals["MonthStr"] = monthly_totals["Month"].dt.strftime("%b %Y")

        # Line chart
        fig = px.line(
            monthly_totals,
            x="MonthStr",
            y=["Expenses", "Incomes", "Net"],
            labels={"value": "Amount (€)", "MonthStr": "Month"},
            title="Monthly Expenses, Incomes, and Net",
            markers=True,
        )

        # Color overrides
        fig.update_traces(selector=dict(name="Incomes"), line=dict(color="green"))
        fig.update_traces(selector=dict(name="Expenses"), line=dict(color="red"))
        fig.update_traces(selector=dict(name="Net"), line=dict(color="blue"))

        st.plotly_chart(fig, width="stretch")

        # Net percentage
        monthly_totals["NetPerc"] = (
            monthly_totals["Net"] / monthly_totals["Incomes"].replace(0, np.nan)
        ) * 100

        fig2 = px.line(
            monthly_totals,
            x="MonthStr",
            y="NetPerc",
            labels={"NetPerc": "Net / Incomes (%)", "MonthStr": "Month"},
            title="Net as Percentage of Incomes",
            markers=True,
        )

        fig2.update_traces(line=dict(color="purple"))
        st.plotly_chart(fig2, width="stretch")

        st.info("💡 **Net %** shows how much income remains after expenses.")

# --------------------------------------------------------------------
# Tab 3: Category ➝ Subcategory Drilldown
# --------------------------------------------------------------------
with tab3:
    st.subheader(
        f"Drilldown by Category and Subcategory ({start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')})"
    )

    exp_df = filtered_df[filtered_df["Income/Expense"] == "Exp."]

    if exp_df.empty:
        st.info("No expenses in the selected period.")
    else:
        # Choose category
        drilldown_categories = sorted(exp_df["Category"].unique(), key=sort_key)
        selected_drilldown_cat = st.selectbox(
            "Choose a category", options=drilldown_categories
        )

        cat_df = exp_df[exp_df["Category"] == selected_drilldown_cat]

        has_subcategories = (
            "Subcategory" in cat_df.columns and cat_df["Subcategory"].notna().any()
        )

        # Show subcategory chart if available
        if has_subcategories:
            subcat_df = cat_df[cat_df["Subcategory"].notna()]
            subcat_totals = (
                subcat_df.groupby("Subcategory", as_index=False)["EUR"]
                .sum()
                .sort_values(by="EUR", ascending=False)
            )

            fig = px.bar(
                subcat_totals,
                x="Subcategory",
                y="EUR",
                color="Subcategory",
                labels={"EUR": "Total (€)"},
                title=f"Subcategory Breakdown for {selected_drilldown_cat}",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("This category has no subcategories.", icon="ℹ️")

        # Show all transactions for the category
        st.markdown("### 💡 Transactions")
        cols_to_show = [
            col
            for col in ["Period", "Subcategory", "Accounts", "EUR", "Description"]
            if col in cat_df.columns
        ]
        st.dataframe(
            cat_df[cols_to_show].sort_values(by="Period", ascending=False),
            width="stretch",
        )
