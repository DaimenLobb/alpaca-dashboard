import json
import os

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    st.error("Missing packages. Add gspread and google-auth to requirements.txt")
    st.stop()

st.set_page_config(page_title="Alpaca Bot Dashboard", layout="wide")
st.title("Alpaca Bot Dashboard")

GOOGLE_SHEET_NAME = "Alpaca Bot Logs"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_credentials():
    """Use Streamlit secrets in the cloud, or google_credentials.json locally."""
    if "gcp_service_account" in st.secrets:
        service_account_info = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

    if os.path.exists("google_credentials.json"):
        return Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)

    st.error(
        "No Google credentials found. In Streamlit Cloud, add your JSON values under "
        "[gcp_service_account] in App settings -> Secrets."
    )
    st.stop()


@st.cache_data(ttl=30)
def load_sheet_data():
    creds = get_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(
    st.secrets["gcp_service_account_extra"]["SPREADSHEET_ID"]
)

    data_by_tab = {}
    for worksheet in spreadsheet.worksheets():
        rows = worksheet.get_all_records()
        if rows:
            df = pd.DataFrame(rows)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
            data_by_tab[worksheet.title] = df

    return data_by_tab


try:
    data_by_tab = load_sheet_data()
except Exception as e:
    st.error(f"Could not load Google Sheet: {e}")
    st.stop()

if not data_by_tab:
    st.warning("No bot rows found yet. Wait for a bot polling cycle, then refresh.")
    st.stop()

bot_names = sorted(data_by_tab.keys())

cols = st.columns(3)

for i, bot_name in enumerate(bot_names):

    with cols[i % 3]:

        df = data_by_tab[bot_name]

        st.subheader(bot_name)

        if df.empty:
            st.warning("No rows yet.")
            continue

        latest = df.iloc[-1]

        st.metric(
            "Equity",
            f"${float(latest.get('equity', 0)):,.0f}"
        )

        if "equity" in df.columns and "timestamp" in df.columns:

            chart_df = (
                df.set_index("timestamp")[["equity"]]
                .apply(pd.to_numeric, errors="coerce")
            )

            st.line_chart(chart_df, height=180)

        st.caption(
            f"BP: ${float(latest.get('buying_power', 0)):,.0f}"
        )

        st.caption(
            f"Positions: {int(latest.get('open_positions', 0) or 0)}"
        )

        st.caption(
            f"Orders: {int(latest.get('open_orders', 0) or 0)}"
        )

    st.header(bot_name)

    df = data_by_tab[bot_name]

    if df.empty:
        st.warning("No rows yet.")
        continue

    latest = df.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Equity", f"${float(latest.get('equity', 0)):,.2f}")
    col2.metric("Buying Power", f"${float(latest.get('buying_power', 0)):,.2f}")
    col3.metric("Positions", int(latest.get("open_positions", 0) or 0))
    col4.metric("Orders", int(latest.get("open_orders", 0) or 0))

    if "equity" in df.columns and "timestamp" in df.columns:
        chart_df = (
            df.set_index("timestamp")[["equity"]]
            .apply(pd.to_numeric, errors="coerce")
        )

        st.line_chart(chart_df)

    st.dataframe(df.tail(10), use_container_width=True)

    st.divider()

if df.empty:
    st.warning("This bot tab has no rows yet.")
    st.stop()

latest = df.iloc[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Latest equity", f"${float(latest.get('equity', 0)):,.2f}")
col2.metric("Buying power", f"${float(latest.get('buying_power', 0)):,.2f}")
col3.metric("Open positions", int(latest.get("open_positions", 0) or 0))
col4.metric("Open orders", int(latest.get("open_orders", 0) or 0))

st.subheader("Equity Curve")
if "equity" in df.columns and "timestamp" in df.columns:
    chart_df = df.set_index("timestamp")[["equity"]].apply(pd.to_numeric, errors="coerce")
    st.line_chart(chart_df)
else:
    st.info("No equity column found yet.")

if "buying_power" in df.columns and "timestamp" in df.columns:
    st.subheader("Buying Power")
    bp_df = df.set_index("timestamp")[["buying_power"]].apply(pd.to_numeric, errors="coerce")
    st.line_chart(bp_df)

st.subheader("Latest Snapshots")
st.dataframe(df.tail(50), use_container_width=True)





