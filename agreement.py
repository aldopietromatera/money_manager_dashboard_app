# agreement.py
import streamlit as st


def check_user_agreement():

    agree = st.checkbox(
        "I agree to use this app and to the [Streamlit's privacy policy](https://streamlit.io/privacy-policy)."
    )

    if not agree:
        st.warning("You must agree to the terms before using the app.")
        st.warning(
            "Your data remains private and is automatically deleted after the analysis.",
            icon="⚠️",
        )
        st.stop()
