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

st.set_page_config(page_title="Alpaca Bot Sleep Check", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp { background: #101820; }
.block-container { padding-top: 0.45rem; padding-left: 0.75rem; padding-right: 0.75rem; padding-bottom: 2rem; max-width: 900px; }
header[data-testid="stHeader"] { background: rgba(16,24,32,0.92); }
#MainMenu, footer { visibility: hidden; }
h1 { font-size: 1.65rem !important; line-height: 1.85rem !important; font-weight: 900 !important; color: #f5f7fa !important; margin-bottom: 0.1rem !important; letter-spacing: -0.04em; }
div[data-testid="stCaptionContainer"] p { color: #d6e2ea !important; font-size: 0.82rem; }
.summary-card { border-radius: 20px; border: 1px solid rgba(255,255,255,0.18); background: linear-gradient(145deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08)); padding: 14px; margin-bottom: 12px; box-shadow: 0 10px 28px rgba(0,0,0,0.35); }
.summary-card-positive { border-left: 7px solid #00e676; background: linear-gradient(120deg, rgba(0,200,83,0.26), rgba(255,255,255,0.08)); }
.summary-card-negative { border-left: 7px solid #ff5252; background: linear-gradient(120deg, rgba(255,82,82,0.26), rgba(255,255,255,0.08)); }
.summary-card-flat { border-left: 7px solid #b0bec5; }
.summary-label { color: #d6e2ea; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin-bottom: 3px; }
.summary-value { color: white; font-size: 2rem; font-weight: 900; line-height: 2.15rem; }
.summary-pnl-positive { color: #00e676; font-weight: 900; font-size: 1.25rem; margin-top: 5px; }
.summary-pnl-negative { color: #ff5252; font-weight: 900; font-size: 1.25rem; margin-top: 5px; }
.summary-pnl-flat { color: #cfd8dc; font-weight: 900; font-size: 1.25rem; margin-top: 5px; }
.bot-row { border-radius: 18px; border: 1px solid rgba(255,255,255,0.16); padding: 12px 13px; margin-bottom: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.28); }
.bot-row-positive { background: linear-gradient(90deg, rgba(0,200,83,0.32), rgba(0,200,83,0.10)); border-left: 7px solid #00e676; }
.bot-row-negative { background: linear-gradient(90deg, rgba(255,82,82,0.32), rgba(255,82,82,0.10)); border-left: 7px solid #ff5252; }
.bot-row-flat { background: linear-gradient(90deg, rgba(96,125,139,0.30), rgba(96,125,139,0.10)); border-left: 7px solid #b0bec5; }
.bot-topline { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.bot-name { color: white; font-size: 0.95rem; font-weight: 900; line-height: 1.15rem; }
.bot-pnl-positive { color: #00e676; font-size: 1.28rem; font-weight: 900; white-space: nowrap; }
.bot-pnl-negative { color: #ff5252; font-size: 1.28rem; font-weight: 900; white-space: nowrap; }
.bot-pnl-flat { color: #cfd8dc; font-size: 1.28rem; font-weight: 900; white-space: nowrap; }
.bot-subline { display: flex; justify-content: space-between; gap: 8px; margin-top: 8px; color: #d6e2ea; font-size: 0.76rem; font-weight: 700; }
.tiny { color: #90a4ae; font-size: 0.68rem; margin-top: 5px; }
.section-title { color: #f5f7fa; font-size: 0.9rem; font-weight: 900; text-transform: uppercase; margin: 16px 0 8px 0; letter-spacing: 0.04em; }
.trade-card { border-radius: 14px; padding: 10px 11px; margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.14); background: rgba(255,255,255,0.06); }
.trade-card-positive { border-left: 5px solid #00e676; background: rgba(0,230,118,0.10); }
.trade-card-negative { border-left: 5px solid #ff5252; background: rgba(255,82,82,0.10); }
.trade-card-flat { border-left: 5px solid #b0bec5; }
.trade-top { display: flex; justify-content: space-between; gap: 8px; font-size: 0.84rem; font-weight: 900; color: white; }
.trade-sub { display: flex; justify-content: space-between; gap: 8px; margin-top: 5px; font-size: 0.72rem; color: #d6e2ea; font-weight: 700; }
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


    /* Hide Streamlit mobile/desktop toolbar and header */
    #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }

    footer {
        visibility: hidden !important;
        display: none !important;
    }

    header {
        visibility: hidden !important;
        display: none !important;
        height: 0rem !important;
    }

    [data-testid="stHeader"] {
        visibility: hidden !important;
        display: none !important;
        height: 0rem !important;
    }

    [data-testid="stToolbar"] {
        visibility: hidden !important;
        display: none !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    [data-testid="stStatusWidget"] {
        visibility: hidden !important;
        display: none !important;
    }

    .viewerBadge_container__1QSob {
        display: none !important;
    }

    .stDeployButton {
        display: none !important;
    }

    .block-container {
        padding-top: 0.25rem !important;
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
        border: 1px solid rgba(255,255,255,0.18);
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

</style>
""", unsafe_allow_html=True)

st.title("Alpaca Bot Sleep Check")
st.caption("Split view: Top 3 shared account first, then other bots. Equity change from clean baseline.")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]


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
        return Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
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
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        for col in ["equity", "buying_power", "open_positions", "open_orders", "qty", "buy_price", "sell_price", "pnl", "pnl_pct"]:
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
    if df is None or df.empty or "timestamp" not in df.columns or session_date is None:
        return pd.DataFrame()
    temp = df.copy()
    temp["_session_date"] = temp["timestamp"].apply(trading_session_date)
    return temp[temp["_session_date"] == session_date].drop(columns=["_session_date"], errors="ignore")


def bot_session_stats(df):
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
    if pnl > 0:
        return "positive"
    if pnl < 0:
        return "negative"
    return "flat"


def render_html(html):
    st.markdown(html, unsafe_allow_html=True)



# ============================================================
# BOT GROUPING / TRADE DEDUPE
# ============================================================

TOP_ACCOUNT_MATCHERS = [
    "STRUCTURE HUNTER",
    "STRUCTURE",
    "METALS ORB",
    "QUALITY HUNTER",
    "QUALITY SIZER",
    "QUILITY HUNTER",
    "QUILITY",
]


def is_top_account_bot(bot_name):
    name = str(bot_name or "").upper()
    return any(match in name for match in TOP_ACCOUNT_MATCHERS)


def sort_rows(rows):
    return sorted(rows, key=lambda r: (r["pnl"] < 0, -abs(r["pnl"]), r["bot_name"]))


def dedupe_trades_df(df):
    """Remove duplicate trade rows caused by repeated trade logger passes."""
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



# ============================================================
# BOT GROUPING / TRADE DEDUPE / ALLOCATION BASELINES
# ============================================================

TOP3_SHARED_ACCOUNT_EQUITY = 50000.0
TOP3_SHARED_ACCOUNT_BUYING_POWER = 100000.0

TOP3_ALLOCATIONS = {
    "STRUCTURE": 0.45,
    "METALS": 0.45,
    "QUALITY": 0.10,
}


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


def sort_rows(rows):
    return sorted(rows, key=lambda r: (r["pnl"] < 0, -abs(r["pnl"]), r["bot_name"]))


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
    equity, pnl, pct, session_date = bot_session_stats(df)
    trades = trades_by_tab.get(bot_name)
    session_trades = dedupe_trades_df(session_slice(trades, session_date)) if trades is not None and not trades.empty else pd.DataFrame()
    trade_count = len(session_trades)
    trade_pnl = float(session_trades["pnl"].fillna(0).sum()) if not session_trades.empty and "pnl" in session_trades.columns else 0.0
    # Main card P&L uses equity change, matching Alpaca-style daily account movement.
    # Trades underneath are still shown for audit/details.
    allocated_start = top3_allocated_start_equity(bot_name)

    if allocated_start is not None:
        display_equity = allocated_start + pnl
        display_bp = top3_allocated_buying_power(bot_name)
        display_pct = 0.0 if allocated_start == 0 else (pnl / allocated_start) * 100
    else:
        display_equity = equity
        display_bp = float(latest.get("buying_power", 0) or 0)
        display_pct = pct

    valid_rows.append({
        "bot_name": bot_name,
        "equity": display_equity,
        "raw_equity": equity,
        "pnl": pnl,
        "equity_pnl": pnl,
        "pct": display_pct,
        "buying_power": display_bp,
        "positions": int(latest.get("open_positions", 0) or 0),
        "orders": int(latest.get("open_orders", 0) or 0),
        "last_update": to_et(latest.get("timestamp", "")),
        "trades": trade_count,
        "trade_pnl": trade_pnl,
        "session_date": session_date,
        "session_trades": session_trades,
    })

if not valid_rows:
    st.warning("No valid bot rows found yet.")
    st.stop()


total_equity = sum(r["equity"] for r in valid_rows)
total_bp = sum(r["buying_power"] for r in valid_rows)
total_pnl = sum(r["pnl"] for r in valid_rows)
total_positions = sum(r["positions"] for r in valid_rows)
total_orders = sum(r["orders"] for r in valid_rows)

session_dates = sorted({r["session_date"] for r in valid_rows if r["session_date"] is not None})
session_label = session_dates[-1] if session_dates else "Current"

render_html(
    f'<div class="summary-card summary-card-{pnl_class(total_pnl)}">'
    f'<div class="summary-label">Split Dashboard</div>'
    f'<div class="summary-value" style="font-size:1.35rem;">Top 3 Account + Other Bots</div>'
    f'<div class="tiny">Session: {session_label} ET. Top 3 baseline: $50k equity / $100k buying power.</div>'
    f'</div>'
)

def render_group(group_title, group_rows, subtitle):
    if not group_rows:
        return

    group_equity = sum(r["equity"] for r in group_rows)
    group_pnl = sum(r["pnl"] for r in group_rows)
    group_bp = sum(r["buying_power"] for r in group_rows)
    group_positions = sum(r["positions"] for r in group_rows)
    group_orders = sum(r["orders"] for r in group_rows)
    group_trades = sum(r["trades"] for r in group_rows)
    cls = pnl_class(group_pnl)

    render_html(f'<div class="group-title">{group_title}</div>')
    render_html(f'<div class="group-subtitle">{subtitle}</div>')
    render_html(
        f'<div class="group-summary group-summary-{cls}">'
        f'<div class="group-row"><span>Total Equity</span><span>{money(group_equity)}</span></div>'
        f'<div class="group-row"><span>Equity Change</span><span>{group_pnl:+,.0f}</span></div>'
        f'<div class="group-row"><span>Buying Power</span><span>{money(group_bp)}</span></div>'
        f'<div class="group-row"><span>Risk</span><span>{group_positions} pos / {group_orders} ord / {group_trades} trades</span></div>'
        f'</div>'
    )

    for row in sort_rows(group_rows):
        cls = pnl_class(row["pnl"])

        html = (
            f'<div class="bot-row bot-row-{cls}">'
            f'<div class="bot-topline">'
            f'<div class="bot-name">{row["bot_name"]}</div>'
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
            f'<span>Trade P&L {row["trade_pnl"]:+,.0f}</span>'
            f'<span>Allocation adjusted</span>'
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


top_rows = [r for r in valid_rows if is_top_account_bot(r["bot_name"])]
other_rows = [r for r in valid_rows if not is_top_account_bot(r["bot_name"])]

render_group(
    "Top 3 Shared Trading Account",
    top_rows,
    "Structure Hunter ORB 45%, Metals ORB 45%, Quality Hunter/Sizer 10%.",
)

render_group(
    "Other Bot Accounts",
    other_rows,
    "Separate total for all remaining bot accounts.",
)


st.caption("Sleep-check layout. Refreshes every 30 seconds.")
