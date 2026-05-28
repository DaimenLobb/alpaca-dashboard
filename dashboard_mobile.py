import os

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    st.error("Missing packages. Add gspread and google-auth to requirements.txt")
    st.stop()


st.set_page_config(
    page_title="Alpaca Bot Sleep Check",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .stApp {
            background: #101820;
        }

        .block-container {
            padding-top: 0.45rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
            padding-bottom: 2rem;
            max-width: 900px;
        }

        header[data-testid="stHeader"] {
            background: rgba(16,24,32,0.92);
        }

        #MainMenu, footer {
            visibility: hidden;
        }

        h1 {
            font-size: 1.65rem !important;
            line-height: 1.85rem !important;
            font-weight: 900 !important;
            color: #f5f7fa !important;
            margin-bottom: 0.1rem !important;
            letter-spacing: -0.04em;
        }

        div[data-testid="stCaptionContainer"] p {
            color: #d6e2ea !important;
            font-size: 0.82rem;
        }

        .summary-card {
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.18);
            background: linear-gradient(145deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08));
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 10px 28px rgba(0,0,0,0.35);
        }

        .summary-label {
            color: #d6e2ea;
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 3px;
        }

        .summary-value {
            color: white;
            font-size: 2rem;
            font-weight: 900;
            line-height: 2.15rem;
        }

        .summary-pnl-positive {
            color: #00e676;
            font-weight: 900;
            font-size: 1rem;
            margin-top: 3px;
        }

        .summary-pnl-negative {
            color: #ff5252;
            font-weight: 900;
            font-size: 1rem;
            margin-top: 3px;
        }

        .summary-pnl-flat {
            color: #cfd8dc;
            font-weight: 900;
            font-size: 1rem;
            margin-top: 3px;
        }

        .bot-row {
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.16);
            padding: 12px 13px;
            margin-bottom: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.28);
        }

        .bot-row-positive {
            background: linear-gradient(90deg, rgba(0,200,83,0.28), rgba(0,200,83,0.09));
            border-left: 7px solid #00e676;
        }

        .bot-row-negative {
            background: linear-gradient(90deg, rgba(255,82,82,0.28), rgba(255,82,82,0.09));
            border-left: 7px solid #ff5252;
        }

        .bot-row-flat {
            background: linear-gradient(90deg, rgba(96,125,139,0.30), rgba(96,125,139,0.10));
            border-left: 7px solid #b0bec5;
        }

        .bot-topline {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
        }

        .bot-name {
            color: white;
            font-size: 0.95rem;
            font-weight: 900;
            line-height: 1.15rem;
        }

        .bot-pnl-positive {
            color: #00e676;
            font-size: 1.15rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .bot-pnl-negative {
            color: #ff5252;
            font-size: 1.15rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .bot-pnl-flat {
            color: #cfd8dc;
            font-size: 1.15rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .bot-subline {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            margin-top: 8px;
            color: #d6e2ea;
            font-size: 0.76rem;
            font-weight: 700;
        }

        .tiny {
            color: #90a4ae;
            font-size: 0.68rem;
            margin-top: 5px;
        }

        .section-title {
            color: #f5f7fa;
            font-size: 0.9rem;
            font-weight: 900;
            text-transform: uppercase;
            margin: 16px 0 8px 0;
            letter-spacing: 0.04em;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Alpaca Bot Sleep Check")
st.caption("Quick overnight view: bot P&L, equity, positions, orders")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_spreadsheet_id():
    if "SPREADSHEET_ID" in st.secrets:
        return st.secrets["SPREADSHEET_ID"]

    if "gcp_service_account_extra" in st.secrets:
        extra = st.secrets["gcp_service_account_extra"]
        if "SPREADSHEET_ID" in extra:
            return extra["SPREADSHEET_ID"]

    st.error("Missing SPREADSHEET_ID in Streamlit Secrets.")
    st.stop()


def get_credentials():
    if "gcp_service_account" in st.secrets:
        service_account_info = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

    if os.path.exists("google_credentials.json"):
        return Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)

    st.error("No Google credentials found.")
    st.stop()


@st.cache_data(ttl=30)
def load_sheet_data():
    creds = get_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(get_spreadsheet_id())

    snapshot_tabs = {}
    trade_tabs = {}

    for worksheet in spreadsheet.worksheets():
        rows = worksheet.get_all_records()

        if not rows:
            continue

        df = pd.DataFrame(rows)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        for col in [
            "equity",
            "buying_power",
            "open_positions",
            "open_orders",
            "qty",
            "buy_price",
            "sell_price",
            "pnl",
            "pnl_pct",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        title = worksheet.title

        if title.endswith(" Trades"):
            trade_tabs[title.replace(" Trades", "")] = df
        else:
            if "equity" in df.columns:
                df = df[df["equity"].fillna(0) > 0]

            snapshot_tabs[title] = df

    return snapshot_tabs, trade_tabs


def calc_delta(df):
    latest = float(df.iloc[-1].get("equity", 0) or 0)

    if len(df) > 1:
        previous = float(df.iloc[-2].get("equity", latest) or latest)
    else:
        previous = latest

    pnl = latest - previous
    pct = 0.0 if previous == 0 else (pnl / previous) * 100

    return latest, pnl, pct


def money(value):
    return f"${float(value or 0):,.0f}"


def pnl_class(pnl):
    if pnl > 0:
        return "positive"
    if pnl < 0:
        return "negative"
    return "flat"


try:
    data_by_tab, trades_by_tab = load_sheet_data()
except Exception as e:
    st.error(f"Could not load Google Sheet: {e}")
    st.stop()

valid_rows = []

for bot_name, df in data_by_tab.items():
    if df.empty:
        continue

    latest = df.iloc[-1]
    equity, pnl, pct = calc_delta(df)

    trades = trades_by_tab.get(bot_name)

    trades_today = 0
    if trades is not None and not trades.empty:
        trades_today = len(trades)

    valid_rows.append({
        "bot_name": bot_name,
        "equity": equity,
        "pnl": pnl,
        "pct": pct,
        "buying_power": float(latest.get("buying_power", 0) or 0),
        "positions": int(latest.get("open_positions", 0) or 0),
        "orders": int(latest.get("open_orders", 0) or 0),
        "last_update": latest.get("timestamp", ""),
        "trades": trades_today,
    })

if not valid_rows:
    st.warning("No valid bot rows found yet.")
    st.stop()

total_equity = sum(r["equity"] for r in valid_rows)
total_bp = sum(r["buying_power"] for r in valid_rows)
total_pnl = sum(r["pnl"] for r in valid_rows)
total_positions = sum(r["positions"] for r in valid_rows)
total_orders = sum(r["orders"] for r in valid_rows)

cls = pnl_class(total_pnl)

st.markdown(
    f"""
    <div class="summary-card">
        <div class="summary-label">Total Equity</div>
        <div class="summary-value">{money(total_equity)}</div>
        <div class="summary-pnl-{cls}">{total_pnl:+,.0f}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

s1, s2 = st.columns(2)

with s1:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-label">Buying Power</div>
            <div class="summary-value" style="font-size:1.35rem;">{money(total_bp)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with s2:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-label">Open Risk</div>
            <div class="summary-value" style="font-size:1.35rem;">{total_positions} pos / {total_orders} ord</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Bots</div>', unsafe_allow_html=True)

valid_rows.sort(key=lambda r: (r["pnl"] >= 0, abs(r["pnl"])), reverse=False)

for row in valid_rows:
    cls = pnl_class(row["pnl"])

    st.markdown(
        f"""
        <div class="bot-row bot-row-{cls}">
            <div class="bot-topline">
                <div class="bot-name">{row["bot_name"]}</div>
                <div class="bot-pnl-{cls}">{row["pnl"]:+,.0f}</div>
            </div>

            <div class="bot-subline">
                <span>Equity {money(row["equity"])}</span>
                <span>{row["pct"]:+.2f}%</span>
            </div>

            <div class="bot-subline">
                <span>Pos {row["positions"]}</span>
                <span>Orders {row["orders"]}</span>
                <span>Trades {row["trades"]}</span>
            </div>

            <div class="tiny">Last: {row["last_update"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption("Sleep-check layout. Refreshes every 30 seconds.")
