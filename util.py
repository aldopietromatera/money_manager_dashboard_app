import pandas as pd
import streamlit as st


def load_data_from_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df["Period"] = pd.to_datetime(df["Period"])
    return df


def load_default_data():
    df = pd.read_excel("dummy.xlsx")
    df["Period"] = pd.to_datetime(df["Period"])
    return df


def clear_cache():
    st.cache_data.clear()
    st.cache_resource.clear()
