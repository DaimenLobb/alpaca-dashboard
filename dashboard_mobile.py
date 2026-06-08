import os
from datetime import timedelta

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
    page_title="Alpaca Bot Sleep Check",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp {
        background: #101820;
    }

    .block-container {
        padding-top: 0.25rem !important;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }

    #MainMenu,
    footer,
    header,
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton {
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
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
        border: 1px solid rgba(255,255,255,0.22);
        background: linear-gradient(145deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08));
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    }

    .summary-card-positive {
        border-left: 7px solid #00e676;
        background: linear-gradient(120deg, rgba(0,200,83,0.26), rgba(255,255,255,0.08));
    }

    .summary-card-negative {
        border-left: 7px solid #ff5252;
        background: linear-gradient(120deg, rgba(255,82,82,0.26), rgba(255,255,255,0.08));
    }

    .summary-card-flat {
        border-left: 7px solid #b0bec5;
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
        font-size: 1.7rem;
        font-weight: 900;
        line-height: 2rem;
    }

    .bot-row {
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.16);
        padding: 12px 13px;
        margin-bottom: 10px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.28);
    }

    .bot-row-positive {
        background: linear-gradient(90deg, rgba(0,200,83,0.32), rgba(0,200,83,0.10));
        border-left: 7px solid #00e676;
    }

    .bot-row-negative {
        background: linear-gradient(90deg, rgba(255,82,82,0.32), rgba(255,82,82,0.10));
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
        font-size: 1.28rem;
        font-weight: 900;
        white-space: nowrap;
    }

    .bot-pnl-negative {
        color: #ff5252;
        font-size: 1.28rem;
        font-weight: 900;
        white-space: nowrap;
    }

    .bot-pnl-flat {
        color: #cfd8dc;
        font-size: 1.28rem;
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

    .group-title {
        color: #ffffff;
        font-size: 1.02rem;
        font-weight: 950;
        text-transform: uppercase;
        margin: 20px 0 9px 0;
        letter-spacing: 0.045em;
    }

    .group-subtitle {
        color: #aebbc4;
        font-size: 0.72rem;
        font-weight: 700;
        margin-top: -5px;
        margin-bottom: 10px;
    }

    .group-summary {
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.22);
        padding: 12px 13px;
        margin-bottom: 12px;
        background: linear-gradient(120deg, rgba(255,255,255,0.14), rgba(255,255,255,0.06));
    }

    .group-summary-positive {
        border-left: 7px solid #00e676;
        background: linear-gradient(120deg, rgba(0,200,83,0.22), rgba(255,255,255,0.06));
    }

    .group-summary-negative {
        border-left: 7px solid #ff5252;
        background: linear-gradient(120deg, rgba(255,82,82,0.22), rgba(255,255,255,0.06));
    }

    .group-summary-flat {
        border-left: 7px solid #b0bec5;
    }

    .group-row {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        color: #f5f7fa;
        font-size: 0.86rem;
        font-weight: 900;
        margin-bottom: 5px;
    }

    .trade-card {
        border-radius: 14px;
        padding: 10px 11px;
        margin-bottom: 8px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(255,255,255,0.06);
    }

    .trade-card-positive {
        border-left: 5px solid #00e676;
        background: rgba(0,230,118,0.10);
    }

    .trade-card-negative {
        border-left: 5px solid #ff5252;
        background: rgba(255,82,82,0.10);
    }

    .trade-card-flat {
        border-left: 5px solid #b0bec5;
    }

    .trade-top {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        font-size: 0.84rem;
        font-weight: 900;
        color: white;
    }

    .trade-sub {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        margin-top: 5px;
        font-size: 0.72rem;
        color: #d6e2ea;
        font-weight: 700;
    }

    .trade-pnl-positive { color: #00e676; }
    .trade-pnl-negative { color: #ff5252; }
    .trade-pnl-flat { color: #cfd8dc; }

    div[data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.28) !important;
        border-radius: 16px !important;
        background: rgba(255,255,255,0.095) !important;
        margin-top: -4px !important;
        margin-bottom: 18px !important;
        box-shadow: 0 8px 22px rgba(0,0,0,0.24);
    }

    div[data-testid="stExpander"] details summary {
        color: #f5f7fa !important;
        font-size: 0.88rem !important;
        font-weight: 900 !important;
        padding: 10px 12px !important;
    }

    div[data-testid="stExpander"] details summary p {
        color: #f5f7fa !important;
        font-weight: 900 !important;
    }

    div[data-testid="stExpander"] svg {
        color: #00e676 !important;
        fill: #00e676 !important;
    }

    .account-card {
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.20);
        padding: 16px 15px;
        margin: 14px 0 16px 0;
        box-shadow: 0 14px 34px rgba(0,0,0,0.38);
    }

    .account-card-positive {
        border-left: 9px solid #00e676;
        background: linear-gradient(125deg, rgba(0,200,83,0.30), rgba(255,255,255,0.08));
    }

    .account-card-negative {
        border-left: 9px solid #ff5252;
        background: linear-gradient(125deg, rgba(255,82,82,0.30), rgba(255,255,255,0.08));
    }

    .account-card-flat {
        border-left: 9px solid #b0bec5;
        background: linear-gradient(125deg, rgba(96,125,139,0.24), rgba(255,255,255,0.08));
    }

    .account-title {
        color: #ffffff;
        font-size: 1.05rem;
        font-weight: 950;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 9px;
    }

    .account-main-value {
        color: #ffffff;
        font-size: 2.35rem;
        font-weight: 950;
        line-height: 2.5rem;
        letter-spacing: -0.055em;
        margin-bottom: 8px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 10px;
    }

    .metric-box {
        border-radius: 14px;
        background: rgba(255,255,255,0.09);
        border: 1px solid rgba(255,255,255,0.11);
        padding: 9px 10px;
    }

    .metric-label {
        color: #aebbc4;
        font-size: 0.64rem;
        font-weight: 900;
        text-transform: uppercase;
    }

    .metric-value {
        color: #ffffff;
        font-size: 0.98rem;
        font-weight: 950;
        margin-top: 2px;
    }

    .metric-positive {
        color: #00e676;
    }

    .metric-negative {
        color: #ff5252;
    }

    .metric-flat {
        color: #cfd8dc;
    }

</style>
""", unsafe_allow_html=True)

st.title("Alpaca Bot Sleep Check")
st.caption("Top 3 account reset. Overall shows gain from original $50k start.")


# ============================================================
# GOOGLE SHEETS
# ============================================================

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
def _make_unique_headers(raw_headers):
    """Make Google Sheet headers safe for pandas/gspread.

    Google Sheets can have blank or duplicate header cells. gspread
    get_all_records() crashes on that, so the dashboard reads raw values
    and repairs headers locally.
    """
    headers = []
    seen = {}

    for idx, header in enumerate(raw_headers):
        name = str(header or "").strip()

        if not name:
            name = f"blank_{idx + 1}"

        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1

        headers.append(name)

    return headers


@st.cache_data(ttl=30)
def load_sheet_data():
    creds = get_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(get_spreadsheet_id())

    snapshot_tabs = {}
    trade_tabs = {}

    for worksheet in spreadsheet.worksheets():
        title = worksheet.title

        try:
            values = worksheet.get_all_values()
        except Exception as e:
            print(f"[SHEET SKIP] {title}: {type(e).__name__}: {e}")
            continue

        if not values or len(values) < 2:
            continue

        raw_headers = values[0]
        headers = _make_unique_headers(raw_headers)

        data_rows = values[1:]

        # Pad or trim rows to match headers.
        clean_rows = []
        for row in data_rows:
            if not any(str(v).strip() for v in row):
                continue

            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]

            clean_rows.append(row)

        if not clean_rows:
            continue

        df = pd.DataFrame(clean_rows, columns=headers)

        # Drop repaired blank columns. They are only there to prevent crashes.
        blank_cols = [c for c in df.columns if str(c).startswith("blank_")]
        if blank_cols:
            df = df.drop(columns=blank_cols, errors="ignore")

        # Drop duplicated columns just in case.
        df = df.loc[:, ~df.columns.duplicated()]

        if df.empty:
            continue

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
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

        if is_excluded_bot(title.replace(" Trades", "")):
            continue

        if title.endswith(" Trades"):
            trade_tabs[title.replace(" Trades", "")] = df
        else:
            if "equity" in df.columns:
                df = df[df["equity"].fillna(0) > 0]
            snapshot_tabs[title] = df

    return snapshot_tabs, trade_tabs



# ============================================================
# HELPERS
# ============================================================

def to_et(ts):
    if pd.isna(ts):
        return ts

    stamp = pd.Timestamp(ts)

    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")

    return stamp.tz_convert("America/New_York")


def trading_session_date(ts):
    et = to_et(ts)

    if pd.isna(et):
        return None

    if et.hour < 4:
        return (et - timedelta(days=1)).date()

    return et.date()


def current_session_for_df(df):
    if df.empty or "timestamp" not in df.columns:
        return None

    latest_ts = df.iloc[-1]["timestamp"]
    return trading_session_date(latest_ts)


def session_slice(df, session_date):
    if df.empty or "timestamp" not in df.columns or session_date is None:
        return df.iloc[0:0].copy()

    temp = df.copy()
    temp["_session_date"] = temp["timestamp"].apply(trading_session_date)
    return temp[temp["_session_date"] == session_date].drop(columns=["_session_date"], errors="ignore")


def bot_session_stats(df):
    if df.empty:
        return 0.0, 0.0, 0.0, None

    session_date = current_session_for_df(df)
    sdf = session_slice(df, session_date)

    if sdf.empty:
        sdf = df.copy()

    latest = float(sdf.iloc[-1].get("equity", 0) or 0)
    start = float(sdf.iloc[0].get("equity", latest) or latest)

    pnl = latest - start
    pct = 0.0 if start == 0 else (pnl / start) * 100

    return latest, pnl, pct, session_date


def money(value):
    return f"${float(value or 0):,.0f}"


def money2(value):
    return f"${float(value or 0):,.2f}"


def pnl_class(pnl):
    pnl = float(pnl or 0)
    if abs(pnl) < 0.5:
        return "flat"
    if pnl > 0:
        return "positive"
    return "negative"


def render_html(html):
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# TOP 3 SHARED ACCOUNT CONFIG
# ============================================================

TOP3_SHARED_ACCOUNT_EQUITY = 53620.22
TOP3_SHARED_ACCOUNT_BUYING_POWER = 107240.44

# Manual clean reset/current account value from Alpaca.
# Dashboard uses this for the Top 3 header until fresh snapshot rows catch up.
TOP3_CURRENT_EQUITY_OVERRIDE = 53620.22
TOP3_CURRENT_BUYING_POWER_OVERRIDE = TOP3_CURRENT_EQUITY_OVERRIDE * 2

# Original 50k start for overall account performance.
TOP3_ORIGINAL_START_EQUITY = 50000.0
TOP3_ORIGINAL_START_BUYING_POWER = 100000.0

TOP3_ALLOCATIONS = {
    "STRUCTURE": 0.45,
    "METALS": 0.45,
    "QUALITY": 0.10,
}

# Change this if you want the top 3 reset time moved.
# Rows/trades before this ET time are ignored for the top 3 shared account.
TOP3_RESET_ET = pd.Timestamp("2026-06-02 19:50:00", tz="America/New_York")


def top3_bucket(bot_name):
    name = str(bot_name or "").upper()

    if "STRUCTURE" in name:
        return "STRUCTURE"

    if "METALS ORB" in name or "METALS" in name:
        return "METALS"

    if (
        "QUALITY HUNTER" in name
        or "QUALITY SIZER" in name
        or "QUILITY HUNTER" in name
        or "QUILITY" in name
    ):
        return "QUALITY"

    return None


def is_top_account_bot(bot_name):
    return top3_bucket(bot_name) is not None


def top3_allocated_start_equity(bot_name):
    bucket = top3_bucket(bot_name)
    if bucket is None:
        return None
    return TOP3_SHARED_ACCOUNT_EQUITY * TOP3_ALLOCATIONS[bucket]


def top3_allocated_buying_power(bot_name):
    bucket = top3_bucket(bot_name)
    if bucket is None:
        return 0.0
    return TOP3_SHARED_ACCOUNT_BUYING_POWER * TOP3_ALLOCATIONS[bucket]


EXCLUDED_BOT_KEYWORDS = [
    "TECH HUNTER FULL RUNNER",
    "RECOVERY 20-50",
    "INSTITUTIONAL ORB",
    "MARKET SCOUT",
]


def is_excluded_bot(bot_name):
    name = str(bot_name or "").upper()
    return any(keyword in name for keyword in EXCLUDED_BOT_KEYWORDS)


TOP3_BOT_LABELS = {
    "QUALITY_SIZER": "Quality Sizer",
    "METALS_ORB": "Metals ORB",
    "STRUCTURE_ORB": "Structure ORB",
}


def normalise_bot_id(value, fallback_name=""):
    value = str(value or "").strip().upper()

    if value in TOP3_BOT_LABELS:
        return value

    name = str(fallback_name or "").upper()

    if "QUALITY" in name or "QUILITY" in name:
        return "QUALITY_SIZER"

    if "METALS" in name:
        return "METALS_ORB"

    if "STRUCTURE" in name:
        return "STRUCTURE_ORB"

    return value or "UNKNOWN"


def add_bot_id_to_trade_df(df, fallback_name):
    if df is None or df.empty:
        return df

    temp = df.copy()

    if "bot_id" not in temp.columns:
        temp["bot_id"] = normalise_bot_id("", fallback_name)
    else:
        temp["bot_id"] = temp["bot_id"].apply(lambda x: normalise_bot_id(x, fallback_name))

    if "bot_name" not in temp.columns:
        temp["bot_name"] = temp["bot_id"].map(TOP3_BOT_LABELS).fillna(fallback_name)

    return temp


def trade_row_confirmed_for_bot(trade, bot_id):
    """Only count trades that were logged by the owning bot.

    Old shared-account trade logs are polluted because each bot could read the
    whole Alpaca account and log the same closed orders as itself.
    New bot patches write entry_client_order_id and exit_client_order_id.
    We only count rows where both IDs start with the same bot_id.
    """
    entry_cid = str(trade.get("entry_client_order_id", "") or "")
    exit_cid = str(trade.get("exit_client_order_id", "") or "")

    if not entry_cid or not exit_cid:
        return False

    prefix = f"{bot_id}-"
    return entry_cid.startswith(prefix) and exit_cid.startswith(prefix)


def top3_all_trade_rows_by_bot(trades_by_tab):
    """All Top 3 trades since TOP3_RESET_ET. This is the running leaderboard source."""
    rows = []

    for tab_name, trades in trades_by_tab.items():
        if not is_top_account_bot(tab_name):
            continue

        if trades is None or trades.empty:
            continue

        temp = add_bot_id_to_trade_df(trades, tab_name)
        temp = since_top3_reset(temp)
        temp = dedupe_trades_df(temp)

        if temp is None or temp.empty:
            continue

        for _, trade in temp.iterrows():
            bot_id = normalise_bot_id(trade.get("bot_id", ""), tab_name)
            if not trade_row_confirmed_for_bot(trade, bot_id):
                continue
            rows.append(trade)

    if not rows:
        return pd.DataFrame()

    all_trades = pd.DataFrame(rows)
    all_trades = dedupe_trades_df(all_trades)

    if "bot_id" not in all_trades.columns:
        all_trades["bot_id"] = "UNKNOWN"

    return all_trades


def top3_leaderboard_from_trades(trades_by_tab):
    all_trades = top3_all_trade_rows_by_bot(trades_by_tab)

    leaderboard = []

    for bot_id, label in TOP3_BOT_LABELS.items():
        subset = pd.DataFrame()
        pnl = 0.0
        trades_count = 0
        wins = 0
        losses = 0

        if all_trades is not None and not all_trades.empty and "bot_id" in all_trades.columns:
            subset = all_trades[all_trades["bot_id"] == bot_id].copy()

        if subset is not None and not subset.empty:
            if "pnl" in subset.columns:
                pnl_series = pd.to_numeric(subset["pnl"], errors="coerce").fillna(0)
                pnl = float(pnl_series.sum())
                wins = int((pnl_series > 0).sum())
                losses = int((pnl_series < 0).sum())
            trades_count = len(subset)

        leaderboard.append({
            "bot_id": bot_id,
            "bot_name": label,
            "pnl": pnl,
            "trades": trades_count,
            "wins": wins,
            "losses": losses,
            "session_trades": subset,
        })

    leaderboard.sort(key=lambda r: r["pnl"], reverse=True)
    return leaderboard, all_trades


def since_top3_reset(df):
    if df is None or df.empty or "timestamp" not in df.columns:
        return pd.DataFrame()

    temp = df.copy()
    temp["_et"] = temp["timestamp"].apply(to_et)
    temp = temp[temp["_et"] >= TOP3_RESET_ET].drop(columns=["_et"], errors="ignore")
    return temp


def normalise_top3_rows_to_account(top_rows):
    """Top 3 bot cards use only owner-safe bot_id trade logs from the clean reset."""
    leaderboard, _ = top3_leaderboard_from_trades(trades_by_tab)
    source = latest_row_by_time(top_rows) if top_rows else None
    fixed = []

    allocation_by_bot = {
        "STRUCTURE_ORB": 0.45,
        "METALS_ORB": 0.45,
        "QUALITY_SIZER": 0.10,
    }

    for item in leaderboard:
        bot_id = item["bot_id"]
        label = item["bot_name"]
        allocation = allocation_by_bot.get(bot_id, 0.0)

        allocated_start = TOP3_CURRENT_EQUITY_OVERRIDE * allocation
        allocated_bp = TOP3_CURRENT_BUYING_POWER_OVERRIDE * allocation
        pnl = float(item.get("pnl", 0) or 0)

        fixed.append({
            "bot_name": label,
            "bot_id": bot_id,
            "equity": allocated_start + pnl,
            "raw_equity": allocated_start + pnl,
            "pnl": pnl,
            "equity_pnl": pnl,
            "equity_overnight": pnl,
            "equity_overall": pnl,
            "bp_overnight": pnl * 2,
            "bp_overall": pnl * 2,
            "pct": 0.0 if allocated_start == 0 else (pnl / allocated_start) * 100,
            "buying_power": allocated_bp + (pnl * 2),
            "positions": 0,
            "orders": 0,
            "last_update": source.get("last_update") if source else "",
            "trades": int(item.get("trades", 0) or 0),
            "trade_pnl": pnl,
            "session_date": source.get("session_date") if source else None,
            "session_trades": item.get("session_trades", pd.DataFrame()),
            "df": source.get("df") if source else pd.DataFrame(),
        })

    return fixed


def dedupe_trades_df(df):
    if df is None or df.empty:
        return df

    temp = df.copy()

    if "trade_id" in temp.columns:
        temp["_trade_id_str"] = temp["trade_id"].astype(str)
        has_id = temp["_trade_id_str"].str.len() > 0
        with_id = temp[has_id].drop_duplicates(subset=["_trade_id_str"], keep="last")
        without_id = temp[~has_id]
        temp = pd.concat([with_id, without_id], ignore_index=True).drop(columns=["_trade_id_str"], errors="ignore")

    key_cols = [c for c in ["timestamp", "symbol", "side", "qty", "buy_price", "sell_price", "pnl"] if c in temp.columns]
    if key_cols:
        temp = temp.drop_duplicates(subset=key_cols, keep="last")

    if "timestamp" in temp.columns:
        temp = temp.sort_values("timestamp")

    return temp


def sort_rows(rows):
    return sorted(rows, key=lambda r: (r["pnl"] < 0, -abs(r["pnl"]), r["bot_name"]))


def latest_row_by_time(rows):
    if not rows:
        return None

    def key_func(row):
        try:
            return pd.Timestamp(row.get("last_update"))
        except Exception:
            return pd.Timestamp.min.tz_localize("UTC")

    return max(rows, key=key_func)


def latest_valid_number(df, col):
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    values = values[values > 0]
    return float(values.iloc[-1]) if not values.empty else 0.0


def account_equity_summary_from_rows(rows, equity_baseline, bp_baseline):
    """Top 3 account header.

    Source of truth for now is the Alpaca reset/current value:
    - Current equity override: $53,620.22
    - Original account start: $50,000
    This makes the top card show +$3,620.22 overall.
    Bot cards/leaderboard stay clean from owner-safe bot trade logs.
    """
    equity = TOP3_CURRENT_EQUITY_OVERRIDE
    buying_power = TOP3_CURRENT_BUYING_POWER_OVERRIDE

    equity_overall = equity - TOP3_ORIGINAL_START_EQUITY
    bp_overall = buying_power - TOP3_ORIGINAL_START_BUYING_POWER

    # New clean leaderboard starts from the reset, so overnight is zero until new owner-safe trades arrive.
    equity_overnight = 0.0
    bp_overnight = 0.0

    return {
        "equity": equity,
        "equity_overnight": equity_overnight,
        "equity_overall": equity_overall,
        "buying_power": buying_power,
        "bp_overnight": bp_overnight,
        "bp_overall": bp_overall,
        "positions": sum(r["positions"] for r in rows),
        "orders": sum(r["orders"] for r in rows),
        "trades": sum(r["trades"] for r in rows),
    }


def first_valid_number(df, col):
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    values = values[values > 0]
    return float(values.iloc[0]) if not values.empty else 0.0


def latest_valid_number(df, col):
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    values = values[values > 0]
    return float(values.iloc[-1]) if not values.empty else 0.0


def overnight_change_for_df(df, col):
    if df is None or df.empty or "timestamp" not in df.columns or col not in df.columns:
        return 0.0
    session_date = current_session_for_df(df)
    sdf = session_slice(df, session_date)
    if sdf.empty:
        return 0.0
    values = pd.to_numeric(sdf[col], errors="coerce").dropna()
    values = values[values > 0]
    if values.empty:
        return 0.0
    return float(values.iloc[-1] - values.iloc[0])


def metric_class(value):
    value = float(value or 0)
    if abs(value) < 0.5:
        return "flat"
    if value > 0:
        return "positive"
    return "negative"



# ============================================================
# LOAD
# ============================================================

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
    raw_equity, equity_pnl, equity_pct, session_date = bot_session_stats(df)

    trades = trades_by_tab.get(bot_name)
    session_trades = pd.DataFrame()

    if is_top_account_bot(bot_name):
        allocated_start = top3_allocated_start_equity(bot_name) or 0.0
        allocated_bp = top3_allocated_buying_power(bot_name)

        all_reset_trades = pd.DataFrame()
        overnight_trades = pd.DataFrame()

        if trades is not None and not trades.empty:
            all_reset_trades = dedupe_trades_df(since_top3_reset(trades))
            if session_date is not None:
                overnight_trades = dedupe_trades_df(since_top3_reset(session_slice(trades, session_date)))

        overall_trade_pnl = 0.0
        if all_reset_trades is not None and not all_reset_trades.empty and "pnl" in all_reset_trades.columns:
            overall_trade_pnl = float(all_reset_trades["pnl"].fillna(0).sum())

        overnight_trade_pnl = 0.0
        if overnight_trades is not None and not overnight_trades.empty and "pnl" in overnight_trades.columns:
            overnight_trade_pnl = float(overnight_trades["pnl"].fillna(0).sum())

        session_trades = all_reset_trades
        trade_pnl = overall_trade_pnl
        trade_count = len(all_reset_trades) if all_reset_trades is not None else 0

        display_equity = allocated_start + overall_trade_pnl
        display_pnl = overnight_trade_pnl
        display_pct = 0.0 if allocated_start == 0 else (overnight_trade_pnl / allocated_start) * 100
        display_bp = allocated_bp + (overall_trade_pnl * 2)

        equity_overnight = overnight_trade_pnl
        equity_overall = overall_trade_pnl
        bp_overnight = overnight_trade_pnl * 2
        bp_overall = overall_trade_pnl * 2

    else:
        display_equity = raw_equity
        display_bp = float(latest.get("buying_power", 0) or 0)

        if trades is not None and not trades.empty and session_date is not None:
            session_trades = dedupe_trades_df(session_slice(trades, session_date))

        trade_count = len(session_trades) if session_trades is not None else 0
        trade_pnl = 0.0
        if session_trades is not None and not session_trades.empty and "pnl" in session_trades.columns:
            trade_pnl = float(session_trades["pnl"].fillna(0).sum())

        display_pnl = trade_pnl if trade_count > 0 else 0.0
        display_pct = 0.0 if trade_count == 0 or raw_equity == 0 else (display_pnl / max(raw_equity - display_pnl, 1)) * 100

        first_equity = first_valid_number(df, "equity")
        first_bp = first_valid_number(df, "buying_power")
        latest_bp = latest_valid_number(df, "buying_power")

        equity_overnight = display_pnl
        equity_overall = raw_equity - first_equity if first_equity else 0.0
        bp_overnight = display_pnl * 2
        bp_overall = latest_bp - first_bp if first_bp else 0.0

    valid_rows.append({
        "bot_name": bot_name,
        "equity": display_equity,
        "raw_equity": raw_equity,
        "pnl": display_pnl,
        "equity_pnl": equity_pnl,
        "equity_overnight": equity_overnight,
        "equity_overall": equity_overall,
        "bp_overnight": bp_overnight,
        "bp_overall": bp_overall,
        "pct": display_pct,
        "buying_power": display_bp,
        "positions": int(latest.get("open_positions", 0) or 0),
        "orders": int(latest.get("open_orders", 0) or 0),
        "last_update": to_et(latest.get("timestamp", "")),
        "trades": trade_count,
        "trade_pnl": trade_pnl,
        "session_date": session_date,
        "session_trades": session_trades,
        "df": df,
    })

if not valid_rows:
    st.warning("No valid bot rows found yet.")
    st.stop()

session_dates = sorted({r["session_date"] for r in valid_rows if r["session_date"] is not None})
session_label = session_dates[-1] if session_dates else "Current"

render_html(
    f'<div class="summary-card summary-card-flat">'
    f'<div class="summary-label">Split Dashboard</div>'
    f'<div class="summary-value" style="font-size:1.25rem;">Overnight / Overall</div>'
    f'<div class="tiny">Session: {session_label} ET. Top 3 current: $53,620.22 equity / $107,240.44 buying power.</div>'
    f'</div>'
)


def render_top3_leaderboard():
    leaderboard, _ = top3_leaderboard_from_trades(trades_by_tab)

    rows_html = ""

    for i, item in enumerate(leaderboard, start=1):
        overall = float(item.get("pnl", 0) or 0)
        overnight = overall
        overall_cls = pnl_class(overall)
        overnight_cls = pnl_class(overnight)
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"

        rows_html += (
            f'<div style="display:grid;grid-template-columns:42px 1fr 92px 92px;gap:8px;align-items:center;padding:13px 0;border-top:1px solid rgba(255,255,255,0.14);">'
            f'<div style="font-size:1.45rem;font-weight:950;">{medal}</div>'
            f'<div>'
            f'<div style="font-size:1.08rem;font-weight:950;color:#fff;">{item["bot_name"]}</div>'
            f'<div style="font-size:0.76rem;color:#9fb0bb;margin-top:2px;">Trades {item["trades"]} · Wins {item["wins"]} / Losses {item["losses"]}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.62rem;color:#9fb0bb;text-align:right;text-transform:uppercase;font-weight:900;">Overnight</div>'
            f'<div class="pnl-{overnight_cls}" style="font-size:1.02rem;font-weight:950;text-align:right;">{overnight:+,.0f}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.62rem;color:#9fb0bb;text-align:right;text-transform:uppercase;font-weight:900;">Overall</div>'
            f'<div class="pnl-{overall_cls}" style="font-size:1.02rem;font-weight:950;text-align:right;">{overall:+,.0f}</div>'
            f'</div>'
            f'</div>'
        )

    render_html(
        f'<div style="border-radius:24px;border:1px solid rgba(255,255,255,0.22);border-left:10px solid #00e676;'
        f'background:linear-gradient(145deg, rgba(0,200,83,0.26), rgba(255,255,255,0.075));'
        f'padding:20px 18px;margin:18px 0 28px 0;box-shadow:0 18px 40px rgba(0,0,0,0.38);">'
        f'<div style="font-size:1.55rem;font-weight:950;color:white;margin-bottom:12px;">🏆 Top 3 Running Leaderboard</div>'
        f'{rows_html}'
        f'<div class="last-seen">Leaderboard starts from the $53,620.22 clean reset.</div>'
        f'</div>'
    )


# ============================================================
# RENDER
# ============================================================

def render_group(group_title, group_rows, subtitle):
    if not group_rows:
        return

    if "Top 3" in group_title:
        account_summary = account_equity_summary_from_rows(
            group_rows,
            TOP3_SHARED_ACCOUNT_EQUITY,
            TOP3_SHARED_ACCOUNT_BUYING_POWER,
        )
        group_equity = account_summary["equity"]
        group_equity_overnight = account_summary["equity_overnight"]
        group_equity_overall = account_summary["equity_overall"]
        group_bp = account_summary["buying_power"]
        group_bp_overnight = account_summary["bp_overnight"]
        group_bp_overall = account_summary["bp_overall"]
        group_positions = account_summary["positions"]
        group_orders = account_summary["orders"]
        group_trades = account_summary["trades"]
    else:
        group_equity = sum(r["equity"] for r in group_rows)
        group_equity_overnight = sum(r["equity_overnight"] for r in group_rows)
        group_equity_overall = sum(r["equity_overall"] for r in group_rows)
        group_bp = sum(r["buying_power"] for r in group_rows)
        group_bp_overnight = sum(r["bp_overnight"] for r in group_rows)
        group_bp_overall = sum(r["bp_overall"] for r in group_rows)
        group_positions = sum(r["positions"] for r in group_rows)
        group_orders = sum(r["orders"] for r in group_rows)
        group_trades = sum(r["trades"] for r in group_rows)

    cls = pnl_class(group_equity_overnight)

    eq_overnight_cls = metric_class(group_equity_overnight)
    eq_overall_cls = metric_class(group_equity_overall)
    bp_overnight_cls = metric_class(group_bp_overnight)
    bp_overall_cls = metric_class(group_bp_overall)

    render_html(
        f'<div class="account-card account-card-{cls}">'
        f'<div class="account-title">{group_title}</div>'
        f'<div class="account-main-value">{money(group_equity)}</div>'
        f'<div class="metric-grid">'
        f'<div class="metric-box"><div class="metric-label">Equity Overnight</div><div class="metric-value metric-{eq_overnight_cls}">{group_equity_overnight:+,.0f}</div></div>'
        f'<div class="metric-box"><div class="metric-label">Equity Overall</div><div class="metric-value metric-{eq_overall_cls}">{group_equity_overall:+,.0f}</div></div>'
        f'<div class="metric-box"><div class="metric-label">Buying Power</div><div class="metric-value">{money(group_bp)}</div></div>'
        f'<div class="metric-box"><div class="metric-label">BP Overnight</div><div class="metric-value metric-{bp_overnight_cls}">{group_bp_overnight:+,.0f}</div></div>'
        f'<div class="metric-box"><div class="metric-label">BP Overall</div><div class="metric-value metric-{bp_overall_cls}">{group_bp_overall:+,.0f}</div></div>'
        f'<div class="metric-box"><div class="metric-label">Risk / Trades</div><div class="metric-value">{group_positions} pos / {group_orders} ord / {group_trades}</div></div>'
        f'</div>'
        f'<div class="tiny">{subtitle}</div>'
        f'</div>'
    )

    rank_lookup = {}
    if "Top 3" in group_title:
        leaderboard, _ = top3_leaderboard_from_trades(trades_by_tab)
        for rank, item in enumerate(leaderboard, start=1):
            rank_lookup[item["bot_id"]] = {
                "rank": rank,
                "badge": "🥇 1st" if rank == 1 else "🥈 2nd" if rank == 2 else "🥉 3rd",
                "overnight": float(item.get("pnl", 0) or 0),
                "overall": float(item.get("pnl", 0) or 0),
            }

    for row in sort_rows(group_rows):
        cls = pnl_class(row["pnl"])
        bot_id = row.get("bot_id") or normalise_bot_id("", row.get("bot_name", ""))

        rank_info = rank_lookup.get(bot_id)
        if rank_info:
            badge = rank_info["badge"]
            overnight_equity = rank_info["overnight"]
            overall_equity = rank_info["overall"]
        elif bot_id == "UNALLOCATED":
            badge = "⚠️ Gap"
            overnight_equity = float(row.get("pnl", 0) or 0)
            overall_equity = float(row.get("equity_overall", 0) or 0)
        else:
            badge = ""
            overnight_equity = float(row.get("pnl", 0) or 0)
            overall_equity = float(row.get("equity_overall", 0) or 0)

        overnight_cls = pnl_class(overnight_equity)
        overall_cls = pnl_class(overall_equity)
        title = f'{badge} {row["bot_name"]}'.strip()

        html = (
            f'<div class="bot-row bot-row-{cls}">'
            f'<div class="bot-topline">'
            f'<div class="bot-name">{title}</div>'
            f'<div class="bot-pnl-{cls}">{row["pnl"]:+,.0f}</div>'
            f'</div>'
            f'<div class="bot-subline">'
            f'<span>Equity {money(row["equity"])}</span>'
            f'<span>{row["pct"]:+.2f}%</span>'
            f'</div>'
            f'<div class="bot-subline">'
            f'<span>Pos {row["positions"]}</span>'
            f'<span>Orders {row["orders"]}</span>'
            f'<span>Trades {row["trades"]}</span>'
            f'</div>'
            f'<div class="bot-subline">'
            f'<span>Overnight Equity <b class="pnl-{overnight_cls}">{overnight_equity:+,.0f}</b></span>'
            f'<span>Overall Equity <b class="pnl-{overall_cls}">{overall_equity:+,.0f}</b></span>'
            f'</div>'
            f'<div class="tiny">Last: {row["last_update"]}</div>'
            f'</div>'
        )

        render_html(html)

        with st.expander(f'📊 View trades ({row["trades"]})', expanded=False):
            trades = row["session_trades"]

            if trades is None or trades.empty:
                st.caption("No trades logged for this session yet.")
            else:
                show = dedupe_trades_df(trades).tail(20).sort_values("timestamp", ascending=False)

                for _, trade in show.iterrows():
                    trade_pnl = float(trade.get("pnl", 0) or 0)
                    trade_pct = float(trade.get("pnl_pct", 0) or 0)
                    trade_cls = pnl_class(trade_pnl)

                    symbol = trade.get("symbol", "")
                    side = str(trade.get("side", "")).upper()
                    qty = trade.get("qty", "")
                    buy_price = trade.get("buy_price", 0)
                    sell_price = trade.get("sell_price", 0)
                    status = trade.get("status", "")
                    timestamp = to_et(trade.get("timestamp", ""))

                    trade_html = (
                        f'<div class="trade-card trade-card-{trade_cls}">'
                        f'<div class="trade-top">'
                        f'<span>{symbol} {side}</span>'
                        f'<span class="trade-pnl-{trade_cls}">{trade_pnl:+,.2f}</span>'
                        f'</div>'
                        f'<div class="trade-sub">'
                        f'<span>Qty {qty}</span>'
                        f'<span>{trade_pct:+.2f}%</span>'
                        f'</div>'
                        f'<div class="trade-sub">'
                        f'<span>Buy {money2(buy_price)}</span>'
                        f'<span>Sell {money2(sell_price)}</span>'
                        f'</div>'
                        f'<div class="tiny">{status} | {timestamp}</div>'
                        f'</div>'
                    )

                    render_html(trade_html)


valid_rows = [r for r in valid_rows if not is_excluded_bot(r["bot_name"])]
top_rows_raw = [r for r in valid_rows if is_top_account_bot(r["bot_name"])]
top_rows = normalise_top3_rows_to_account(top_rows_raw)
other_rows = [r for r in valid_rows if not is_top_account_bot(r["bot_name"])]

render_group(
    "Top 3 Shared Trading Account",
    top_rows,
    "Top 3 account $53,620.22. Overall measured from original $50k start.",
)


render_group(
    "Other Bot Accounts",
    other_rows,
    "Separate total for all remaining bot accounts.",
)

st.caption("Sleep-check layout. Refreshes every 30 seconds.")
