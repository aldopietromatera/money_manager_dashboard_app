import pandas as pd
import streamlit as st
from datetime import datetime


@st.cache_data
def load_data_from_file(uploaded_file) -> pd.DataFrame:
    """
    Load an Excel file uploaded by the user.

    - Reads the file into a DataFrame.
    - Converts the 'Period' column to datetime if present.

    Returns:
        pd.DataFrame: The loaded data.
    """
    df = pd.read_excel(uploaded_file)
    if "Period" in df.columns:
        df["Period"] = pd.to_datetime(df["Period"])
    return df


@st.cache_data
def load_default_data(path: str = "dummy.xlsx") -> pd.DataFrame:
    """
    Load the default Excel dataset and adjust sample months.

    - Loads local Excel file.
    - Converts 'Period' column to datetime.
    - Shifts:
        April  → last month of current year
        May    → current month of current year

    Args:
        path (str): Path to the Excel file.

    Returns:
        pd.DataFrame: The adjusted dataset.
    """
    df = pd.read_excel(path)

    if "Period" not in df.columns:
        return df

    df["Period"] = pd.to_datetime(df["Period"])

    today = datetime.today()
    current_year = today.year
    current_month = today.month

    # Compute last month (handle January rollover)
    if current_month == 1:
        last_month = 12
        last_month_year = current_year - 1
    else:
        last_month = current_month - 1
        last_month_year = current_year

    month_map = {
        4: (last_month_year, last_month),
        5: (current_year, current_month),
    }

    def shift_month(d):
        if d.month not in month_map:
            return d
        new_year, new_month = month_map[d.month]
        return d.replace(year=new_year, month=new_month)

    df["Period"] = df["Period"].apply(shift_month)
    return df


def count_months(df: pd.DataFrame) -> int:
    """
    Count the number of unique months in the 'Period' column.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        int: Number of unique months. Returns 0 if invalid.
    """
    if df.empty or "Period" not in df.columns:
        return 0
    return df["Period"].dt.to_period("M").nunique()


def clear_cache() -> None:
    """
    Clear all Streamlit caches:
    - cache_data
    - cache_resource
    """
    st.cache_data.clear()
    st.cache_resource.clear()
