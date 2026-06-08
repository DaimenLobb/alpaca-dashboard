
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
    page_title="Alpaca Bot Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    '''
    <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(0, 200, 83, 0.12), transparent 25%),
                radial-gradient(circle at top right, rgba(0, 176, 255, 0.10), transparent 25%),
                #071018;
        }

        .block-container {
            padding-top: 1rem;
            padding-left: 1.4rem;
            padding-right: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1700px;
        }

        header[data-testid="stHeader"] {
            background: rgba(7,16,24,0.82);
        }

        #MainMenu, footer {
            visibility: hidden;
        }

        h1 {
            font-size: 2.35rem !important;
            line-height: 2.55rem !important;
            font-weight: 900 !important;
            margin-bottom: 0.2rem !important;
            color: #f5f7fa !important;
            letter-spacing: -0.04em;
        }

        p, span, div {
            color: #eef3f8;
        }

        div[data-testid="stCaptionContainer"] p {
            color: #d6e2ea !important;
            font-size: 0.9rem;
        }

        .account-card {
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.20);
            padding: 18px 18px;
            margin: 14px 0 18px 0;
            box-shadow: 0 14px 34px rgba(0,0,0,0.38);
        }

        .account-card-positive {
            border-left: 10px solid #00e676;
            background: linear-gradient(125deg, rgba(0,200,83,0.30), rgba(255,255,255,0.08));
        }

        .account-card-negative {
            border-left: 10px solid #ff5252;
            background: linear-gradient(125deg, rgba(255,82,82,0.30), rgba(255,255,255,0.08));
        }

        .account-card-flat {
            border-left: 10px solid #b0bec5;
            background: linear-gradient(125deg, rgba(96,125,139,0.24), rgba(255,255,255,0.08));
        }

        .account-title {
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 9px;
        }

        .account-main-value {
            color: #ffffff;
            font-size: 2.55rem;
            font-weight: 950;
            line-height: 2.75rem;
            letter-spacing: -0.055em;
            margin-bottom: 8px;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            margin-top: 12px;
        }

        .metric-box {
            border-radius: 14px;
            background: rgba(255,255,255,0.09);
            border: 1px solid rgba(255,255,255,0.11);
            padding: 10px 11px;
            min-height: 72px;
        }

        .metric-label {
            color: #aebbc4;
            font-size: 0.68rem;
            font-weight: 900;
            text-transform: uppercase;
        }

        .metric-value {
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 950;
            margin-top: 4px;
        }

        .metric-positive { color: #00e676; }
        .metric-negative { color: #ff5252; }
        .metric-flat { color: #cfd8dc; }

        .bot-card {
            padding: 0;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.16);
            background: linear-gradient(160deg, rgba(255,255,255,0.08), rgba(255,255,255,0.025));
            box-shadow: 0 10px 34px rgba(0,0,0,0.34);
            overflow: hidden;
            margin-bottom: 16px;
        }

        .bot-header {
            padding: 12px 14px;
            color: white;
            font-weight: 900;
            font-size: 0.88rem;
            min-height: 46px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }

        .bot-body {
            padding: 12px;
        }

        .status-pill {
            font-size: 0.70rem;
            font-weight: 900;
            padding: 5px 9px;
            border-radius: 999px;
            background: rgba(0,0,0,0.30);
            border: 1px solid rgba(255,255,255,0.24);
            white-space: nowrap;
        }

        .header-positive {
            background: linear-gradient(90deg, #007a3d, #00c853);
        }

        .header-negative {
            background: linear-gradient(90deg, #8b1f1f, #ff5252);
        }

        .header-flat {
            background: linear-gradient(90deg, #263238, #607d8b);
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08));
            border: 1px solid rgba(255,255,255,0.16);
            padding: 13px;
            border-radius: 18px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.28);
        }

        div[data-testid="stMetricLabel"] p {
            color: #eef3f8 !important;
            font-size: 0.78rem !important;
            font-weight: 800 !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.55rem !important;
            font-weight: 900 !important;
            color: white !important;
        }

        .mini-box {
            padding: 9px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.09);
            min-height: 64px;
        }

        .mini-label {
            color: #aab8c3;
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 2px;
        }

        .mini-value {
            font-size: 1.05rem;
            font-weight: 900;
            color: white;
        }


        .pnl-line {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            margin-top: 8px;
            margin-bottom: 8px;
            font-size: 0.82rem;
            font-weight: 900;
        }

        .pnl-label {
            color: #aebbc4;
            font-weight: 800;
        }

        .pnl-positive {
            color: #00e676;
        }

        .pnl-negative {
            color: #ff5252;
        }

        .pnl-flat {
            color: #cfd8dc;
        }

        .last-seen {
            color: #90a4ae;
            font-size: 0.68rem;
            margin-top: 8px;
            line-height: 1.1rem;
        }

        .divider-soft {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
            margin: 18px 0;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 950;
            color: white;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin: 18px 0 10px 0;
        }

        @media (max-width: 1100px) {
            .metric-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.35rem;
                padding-left: 0.7rem;
                padding-right: 0.7rem;
            }

            h1 {
                font-size: 1.7rem !important;
                line-height: 1.95rem !important;
            }

            .metric-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .account-main-value {
                font-size: 2rem;
                line-height: 2.2rem;
            }

            .bot-header {
                font-size: 0.78rem;
                min-height: 42px;
                padding: 10px 11px;
            }
        }
    </style>
    ''',
    unsafe_allow_html=True,
)

st.title("Alpaca Bot Dashboard")
st.caption("PC view: Top 3 running leaderboard from the 50k account start.")


# ============================================================
# GOOGLE SHEETS CONFIG
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_spreadsheet_id() -> str:
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
    return trading_session_date(df.iloc[-1]["timestamp"])


def session_slice(df, session_date):
    if df.empty or "timestamp" not in df.columns or session_date is None:
        return df.iloc[0:0].copy()
    temp = df.copy()
    temp["_session_date"] = temp["timestamp"].apply(trading_session_date)
    return temp[temp["_session_date"] == session_date].drop(columns=["_session_date"], errors="ignore")


def chart_session_df(df):
    """Default PC chart to the current trading session."""
    if df is None or df.empty:
        return df

    session_date = current_session_for_df(df)
    sdf = session_slice(df, session_date)

    if not sdf.empty:
        return sdf

    return df.tail(120)


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


def money(value):
    return f"${float(value or 0):,.0f}"


def fmt_price(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def pnl_class(pnl):
    pnl = float(pnl or 0)
    if abs(pnl) < 0.5:
        return "flat"
    if pnl > 0:
        return "positive"
    return "negative"


def metric_class(value):
    return pnl_class(value)


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

# Ignore tiny paper-account drift, but show real equity moves even if trade rows missed.
NO_TRADE_EQUITY_MOVE_THRESHOLD = 10.0

TOP3_ALLOCATIONS = {
    "STRUCTURE": 0.45,
    "METALS": 0.45,
    "QUALITY": 0.10,
}

TOP3_RESET_ET = pd.Timestamp("2026-06-03 03:19:00", tz="America/New_York")


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


def make_bot_chart_df(row):
    """Build the bot card chart.

    Top 3 bots use allocation-adjusted equity, not raw old account equity.
    Other bots use only the current trading session.
    """
    bot_name = row["bot_name"]
    df = row["df"]

    if df is None or df.empty or "timestamp" not in df.columns:
        return pd.DataFrame(columns=["timestamp", "equity"])

    # Top 3 charts are synthetic/clean:
    # allocation baseline + cumulative post-reset trade P&L.
    if is_top_account_bot(bot_name):
        allocated_start = top3_allocated_start_equity(bot_name) or 0.0
        trades = row.get("session_trades")

        if trades is None or trades.empty or "timestamp" not in trades.columns or "pnl" not in trades.columns:
            ts = df["timestamp"].dropna()
            if ts.empty:
                now_ts = pd.Timestamp.now(tz="UTC")
                return pd.DataFrame({"timestamp": [now_ts], "equity": [allocated_start]})

            session_date = current_session_for_df(df)
            sdf = session_slice(df, session_date)
            if sdf.empty:
                sdf = df.tail(2)

            return pd.DataFrame({
                "timestamp": sdf["timestamp"],
                "equity": [allocated_start] * len(sdf),
            })

        clean_trades = dedupe_trades_df(trades).copy()
        clean_trades = clean_trades.dropna(subset=["timestamp"]).sort_values("timestamp")
        clean_trades["pnl"] = pd.to_numeric(clean_trades["pnl"], errors="coerce").fillna(0)
        clean_trades["equity"] = allocated_start + clean_trades["pnl"].cumsum()

        # Add a baseline point before first trade so line starts at allocation.
        first_trade_time = clean_trades.iloc[0]["timestamp"]
        base_row = pd.DataFrame({
            "timestamp": [first_trade_time - pd.Timedelta(minutes=1)],
            "equity": [allocated_start],
        })

        return pd.concat(
            [base_row, clean_trades[["timestamp", "equity"]]],
            ignore_index=True,
        )

    # Other bots: only show current trading session raw equity.
    session_date = current_session_for_df(df)
    sdf = session_slice(df, session_date)

    if sdf.empty:
        sdf = df.tail(120)

    return sdf[["timestamp", "equity"]].copy()


# ============================================================
# LOAD
# ============================================================

try:
    data_by_tab, trades_by_tab = load_sheet_data()
except Exception as e:
    st.error(f"Could not load Google Sheet: {e}")
    st.stop()

if not data_by_tab:
    st.warning("No bot rows found yet.")
    st.stop()


# ============================================================
# PREPARE ROWS
# ============================================================

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

        # Prefer logged trade P&L. If trade rows are missing but equity clearly moved, show equity movement.
        if trade_count > 0:
            display_pnl = trade_pnl
        elif abs(equity_pnl) >= NO_TRADE_EQUITY_MOVE_THRESHOLD:
            display_pnl = equity_pnl
        else:
            display_pnl = 0.0

        display_pct = 0.0 if display_pnl == 0 or raw_equity == 0 else (display_pnl / max(raw_equity - display_pnl, 1)) * 100

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


def render_top3_leaderboard():
    leaderboard, _ = top3_leaderboard_from_trades(trades_by_tab)

    rows_html = ""

    for rank, item in enumerate(leaderboard, start=1):
        overall = float(item.get("pnl", 0) or 0)
        overnight = overall
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        overall_cls = pnl_class(overall)
        overnight_cls = pnl_class(overnight)

        rows_html += (
            f'<div style="display:grid;grid-template-columns:60px 1fr 150px 150px 120px 140px;gap:14px;align-items:center;'
            f'padding:14px 0;border-top:1px solid rgba(255,255,255,0.13);">'
            f'<div style="font-size:1.8rem;font-weight:950;">{medal}</div>'
            f'<div><div style="font-size:1.15rem;font-weight:950;color:white;">{item["bot_name"]}</div>'
            f'<div style="font-size:0.78rem;color:#9fb0bb;">Running from 50k reset</div></div>'
            f'<div><div class="metric-label">Overnight</div><div class="metric-value metric-{overnight_cls}">{overnight:+,.0f}</div></div>'
            f'<div><div class="metric-label">Overall</div><div class="metric-value metric-{overall_cls}">{overall:+,.0f}</div></div>'
            f'<div><div class="metric-label">Trades</div><div class="metric-value">{item["trades"]}</div></div>'
            f'<div><div class="metric-label">Wins / Losses</div><div class="metric-value">{item["wins"]} / {item["losses"]}</div></div>'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="account-card account-card-positive">
            <div class="account-title">🏆 Top 3 Running Leaderboard</div>
            <div class="last-seen">Leaderboard starts from the $53,620.22 clean reset.</div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# RENDER SUMMARIES
# ============================================================

def render_account_summary(group_title, group_rows, subtitle, override_summary=None):
    if not group_rows:
        return

    if override_summary is not None:
        group_equity = override_summary["equity"]
        group_equity_overnight = override_summary["equity_overnight"]
        group_equity_overall = override_summary["equity_overall"]
        group_bp = override_summary["buying_power"]
        group_bp_overnight = override_summary["bp_overnight"]
        group_bp_overall = override_summary["bp_overall"]
        group_positions = override_summary["positions"]
        group_orders = override_summary["orders"]
        group_trades = override_summary["trades"]
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
        f'<div class="last-seen">{subtitle}</div>'
        f'</div>'
    )


valid_rows = [r for r in valid_rows if not is_excluded_bot(r["bot_name"])]
top_rows_raw = [r for r in valid_rows if is_top_account_bot(r["bot_name"])]
top_rows = normalise_top3_rows_to_account(top_rows_raw)
other_rows = [r for r in valid_rows if not is_top_account_bot(r["bot_name"])]

render_html(
    f'<div class="last-seen">Session: {session_label} ET. Top 3 current: $53,620.22 equity / $107,240.44 buying power. Reset: {TOP3_RESET_ET.strftime("%Y-%m-%d %H:%M ET")}.</div>'
)

summary_col1, summary_col2 = st.columns(2)

with summary_col1:
    top3_account_summary = account_equity_summary_from_rows(
        top_rows,
        TOP3_SHARED_ACCOUNT_EQUITY,
        TOP3_SHARED_ACCOUNT_BUYING_POWER,
    )
    render_account_summary(
        "Top 3 Shared Trading Account",
        top_rows,
        "Leaderboard uses confirmed owner-safe bot trade logs.",
        override_summary=top3_account_summary,
    )

with summary_col2:
    render_account_summary(
        "Other Bot Accounts",
        other_rows,
        "Overnight = trade P&L only. Overall = equity change from first logged baseline.",
    )

st.markdown('<div class="divider-soft"></div>', unsafe_allow_html=True)


# ============================================================
# BOT CARDS
# ============================================================

def render_trade_cards(trades):
    if trades is None or trades.empty:
        st.caption("No completed trades logged yet.")
        return

    trade_show = dedupe_trades_df(trades).tail(10).sort_values("timestamp", ascending=False)

    for _, trade in trade_show.iterrows():
        pnl = float(trade.get("pnl", 0) or 0)
        pnl_pct = float(trade.get("pnl_pct", 0) or 0)

        if pnl > 0:
            trade_color = "#00e676"
            bg = "rgba(0,230,118,0.08)"
            border = "rgba(0,230,118,0.35)"
        elif pnl < 0:
            trade_color = "#ff5252"
            bg = "rgba(255,82,82,0.08)"
            border = "rgba(255,82,82,0.35)"
        else:
            trade_color = "#b0bec5"
            bg = "rgba(176,190,197,0.06)"
            border = "rgba(176,190,197,0.20)"

        symbol = trade.get("symbol", "")
        side = str(trade.get("side", "")).upper()
        qty = trade.get("qty", "")
        buy_price = fmt_price(trade.get("buy_price", 0))
        sell_price = fmt_price(trade.get("sell_price", 0))
        status = trade.get("status", "")

        st.markdown(
            f'''
            <div style="
                border:1px solid {border};
                background:{bg};
                border-radius:14px;
                padding:10px 12px;
                margin-bottom:10px;
            ">
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-bottom:4px;
                ">
                    <div style="font-weight:800;font-size:15px;color:white;">
                        {symbol} • {side}
                    </div>
                    <div style="color:{trade_color};font-weight:900;font-size:15px;">
                        ${pnl:+,.2f}
                    </div>
                </div>
                <div style="color:#cfd8dc;font-size:12px;margin-bottom:4px;">
                    Qty {qty} | Buy ${buy_price} → Sell ${sell_price}
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="color:{trade_color};font-size:12px;font-weight:700;">
                        {pnl_pct:+.2f}%
                    </div>
                    <div style="color:#90a4ae;font-size:11px;">
                        {status}
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )


def render_bot_card(row):
    bot_id = row.get("bot_id") or normalise_bot_id("", row.get("bot_name", ""))
    lb_badge = ""
    lb_overnight = float(row.get("pnl", 0) or 0)
    lb_overall = float(row.get("equity_overall", 0) or 0)

    if bot_id in TOP3_BOT_LABELS:
        _leaderboard, _ = top3_leaderboard_from_trades(trades_by_tab)
        for _rank, _item in enumerate(_leaderboard, start=1):
            if _item["bot_id"] == bot_id:
                lb_badge = "🥇 1st" if _rank == 1 else "🥈 2nd" if _rank == 2 else "🥉 3rd"
                lb_overnight = float(_item.get("pnl", 0) or 0)
                lb_overall = float(_item.get("pnl", 0) or 0)
                break
    elif bot_id == "UNALLOCATED":
        lb_badge = "⚠️ Gap"

    lb_overnight_cls = pnl_class(lb_overnight)
    lb_overall_cls = pnl_class(lb_overall)

    bot_name = row["bot_name"]
    df = row["df"]

    pnl = float(row["pnl"] or 0)
    header_class = f"header-{pnl_class(pnl)}"
    status_text = "🟢 UP" if pnl > 0 else "🔴 DOWN" if pnl < 0 else "⚪ FLAT"
    delta_color = "normal" if pnl > 0 else "inverse" if pnl < 0 else "off"

    st.markdown(
        f'''
        <div class="bot-card">
            <div class="bot-header {header_class}">
                <span>{bot_name}</span>
                <span class="status-pill">{status_text}</span>
            </div>
            <div class="bot-body">
        ''',
        unsafe_allow_html=True,
    )

    st.metric(
        "Equity",
        money(row["equity"]),
    )

    overnight_cls = pnl_class(row["pnl"])
    overall_cls = pnl_class(row["equity_overall"])

    st.markdown(
        f"""
        <div class="pnl-line">
            <div><span class="pnl-label">Overnight</span> <span class="pnl-{overnight_cls}">{row["pnl"]:+,.0f}</span></div>
            <div><span class="pnl-label">Overall</span> <span class="pnl-{overall_cls}">{row["equity_overall"]:+,.0f}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_source = make_bot_chart_df(row)

    if chart_source is not None and not chart_source.empty and "timestamp" in chart_source.columns:
        chart_df = (
            chart_source
            .dropna(subset=["timestamp"])
            .set_index("timestamp")[["equity"]]
            .apply(pd.to_numeric, errors="coerce")
        )
        st.line_chart(chart_df, height=125)
    else:
        st.caption("No session chart data yet.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">BP</div>
                <div class="mini-value">{money(row["buying_power"])}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">Pos</div>
                <div class="mini-value">{row["positions"]}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">Orders</div>
                <div class="mini-value">{row["orders"]}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">Trades</div>
                <div class="mini-value">{row["trades"]}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="last-seen">Last update: {row["last_update"]}</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Recent trades", expanded=False):
        render_trade_cards(row["session_trades"])

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_bot_grid(title, rows):
    if not rows:
        return

    render_html(f'<div class="section-title">{title}</div>')

    rows = sort_rows(rows)

    for row_start in range(0, len(rows), 3):
        cols = st.columns(3)
        for col, row in zip(cols, rows[row_start:row_start + 3]):
            with col:
                render_bot_card(row)


render_bot_grid("Top 3 Shared Account Bots", top_rows)
render_bot_grid("Other Bot Accounts", other_rows)

st.caption("Responsive layout. Dashboard refreshes every 30 seconds.")
