import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

st.title("Alpaca Bot Dashboard")

LOG_DIR = "logs"

if not os.path.exists(LOG_DIR):
    st.warning("No logs folder found yet.")
    st.stop()

files = [f for f in os.listdir(LOG_DIR) if f.endswith(".csv")]

if not files:
    st.warning("No CSV log files found.")
    st.stop()

selected = st.selectbox("Select Bot", files)

path = os.path.join(LOG_DIR, selected)

df = pd.read_csv(path)

st.subheader("Latest Snapshots")
st.dataframe(df.tail(20), use_container_width=True)

if "equity" in df.columns:
    st.subheader("Equity Curve")
    st.line_chart(df.set_index(df.columns[0])["equity"])

if "buying_power" in df.columns:
    st.subheader("Buying Power")
    st.line_chart(df.set_index(df.columns[0])["buying_power"])
