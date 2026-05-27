import os

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    st.error("Missing packages. Add gspread and google-auth to requirements.txt")
    st.stop()


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Alpaca Bot Dashboard",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 12px;
            border-radius: 14px;
        }
        h1 {
            margin-bottom: 0.25rem;
        }
        h3 {
            font-size: 1.05rem;
            line-height: 1.25rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Alpaca Bot Dashboard")
st.caption("Live Google Sheets feed from your Alpaca trading bots")


# ============================================================
# GOOGLE SHEETS CONFIG
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_spreadsheet_id() -> str:
    """Read spreadsheet ID from Streamlit secrets."""
    if "SPREADSHEET_ID" in st.secrets:
        return st.secrets["SPREADSHEET_ID"]

    if "gcp_service_account_extra" in st.secrets:
        extra = st.secrets["gcp_service_account_extra"]
        if "SPREADSHEET_ID" in extra:
            return extra["SPREADSHEET_ID"]

    st.error(
        "Missing SPREADSHEET_ID in Streamlit Secrets. Add it under "
        "[gcp_service_account_extra]."
    )
    st.stop()


def get_credentials():
    """Use Streamlit secrets in cloud, or google_credentials.json locally."""
    if "gcp_service_account" in st.secrets:
        service_account_info = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )

    if os.path.exists("google_credentials.json"):
        return Credentials.from_service_account_file(
            "google_credentials.json",
            scopes=SCOPES,
        )

    st.error(
        "No Google credentials found. In Streamlit Cloud, add your JSON values "
        "under [gcp_service_account] in App settings → Secrets."
    )
    st.stop()


@st.cache_data(ttl=30)
def load_sheet_data():
    creds = get_credentials()
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(get_spreadsheet_id())

    data_by_tab = {}
    for worksheet in spreadsheet.worksheets():
        rows = worksheet.get_all_records()

        if not rows:
            continue

        df = pd.DataFrame(rows)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        for col in ["equity", "buying_power", "open_positions", "open_orders"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        data_by_tab[worksheet.title] = df

    return data_by_tab


# ============================================================
# LOAD DATA
# ============================================================

try:
    data_by_tab = load_sheet_data()
except Exception as e:
    st.error(f"Could not load Google Sheet: {e}")
    st.stop()

if not data_by_tab:
    st.warning("No bot rows found yet. Wait for a bot polling cycle, then refresh.")
    st.stop()


# ============================================================
# PORTFOLIO SUMMARY
# ============================================================

latest_rows = []

for bot_name, df in data_by_tab.items():
    if df.empty:
        continue

    latest = df.iloc[-1].copy()
    latest["bot"] = bot_name
    latest_rows.append(latest)

if latest_rows:
    latest_df = pd.DataFrame(latest_rows)

    total_equity = pd.to_numeric(latest_df.get("equity", 0), errors="coerce").sum()
    total_buying_power = pd.to_numeric(
        latest_df.get("buying_power", 0),
        errors="coerce",
    ).sum()
    total_positions = pd.to_numeric(
        latest_df.get("open_positions", 0),
        errors="coerce",
    ).fillna(0).sum()
    total_orders = pd.to_numeric(
        latest_df.get("open_orders", 0),
        errors="coerce",
    ).fillna(0).sum()

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Equity", f"${total_equity:,.0f}")
    s2.metric("Total Buying Power", f"${total_buying_power:,.0f}")
    s3.metric("Open Positions", int(total_positions))
    s4.metric("Open Orders", int(total_orders))

st.divider()


# ============================================================
# BOT CARDS
# ============================================================

bot_names = sorted(data_by_tab.keys())

for row_start in range(0, len(bot_names), 3):
    cols = st.columns(3)

    for col, bot_name in zip(cols, bot_names[row_start:row_start + 3]):
        df = data_by_tab[bot_name]

        with col:
            with st.container(border=True):
                st.markdown(f"### {bot_name}")

                if df.empty:
                    st.warning("No rows yet.")
                    continue

                latest = df.iloc[-1]

                equity = float(latest.get("equity", 0) or 0)
                buying_power = float(latest.get("buying_power", 0) or 0)
                open_positions = int(latest.get("open_positions", 0) or 0)
                open_orders = int(latest.get("open_orders", 0) or 0)

                st.metric("Equity", f"${equity:,.0f}")

                if "equity" in df.columns and "timestamp" in df.columns:
                    chart_df = (
                        df.set_index("timestamp")[["equity"]]
                        .apply(pd.to_numeric, errors="coerce")
                    )
                    st.line_chart(chart_df, height=140)
                else:
                    st.info("No equity data yet.")

                c1, c2, c3 = st.columns(3)
                c1.metric("BP", f"${buying_power:,.0f}")
                c2.metric("Pos", open_positions)
                c3.metric("Orders", open_orders)

                if "timestamp" in df.columns:
                    last_seen = latest.get("timestamp")
                    st.caption(f"Last update: {last_seen}")

                with st.expander("Latest rows"):
                    st.dataframe(df.tail(10), use_container_width=True)

st.caption("Dashboard refreshes Google Sheets data every 30 seconds.")






