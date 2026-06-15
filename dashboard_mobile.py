import os
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    st.error("Missing packages. Add gspread and google-auth to requirements.txt")
    st.stop()

st.set_page_config(page_title="Alpaca Fleet Sleep Check", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp { background: #101820; }
.block-container { padding-top: 0.45rem; padding-left: 0.75rem; padding-right: 0.75rem; padding-bottom: 2rem; max-width: 900px; }
header[data-testid="stHeader"] { background: rgba(16,24,32,0.92); }
#MainMenu, footer { visibility: hidden; }
h1 { font-size: 1.55rem !important; line-height: 1.8rem !important; font-weight: 900 !important; color: #f5f7fa !important; margin-bottom: 0.1rem !important; letter-spacing: -0.04em; }
div[data-testid="stCaptionContainer"] p { color: #d6e2ea !important; font-size: 0.82rem; }
.summary-card { border-radius: 20px; border: 1px solid rgba(255,255,255,0.18); background: linear-gradient(145deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08)); padding: 14px; margin-bottom: 12px; box-shadow: 0 10px 28px rgba(0,0,0,0.35); }
.summary-label { color: #d6e2ea; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin-bottom: 3px; }
.summary-value { color: white; font-size: 2rem; font-weight: 900; line-height: 2.15rem; }
.summary-pnl-positive, .bot-pnl-positive { color: #00e676; }
.summary-pnl-negative, .bot-pnl-negative { color: #ff5252; }
.summary-pnl-flat, .bot-pnl-flat { color: #cfd8dc; }
.summary-pnl-positive, .summary-pnl-negative, .summary-pnl-flat { font-weight: 900; font-size: 1rem; margin-top: 3px; }
.bot-row { border-radius: 18px; border: 1px solid rgba(255,255,255,0.16); padding: 12px 13px; margin-bottom: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.28); }
.bot-row-positive { background: linear-gradient(90deg, rgba(0,200,83,0.28), rgba(0,200,83,0.09)); border-left: 7px solid #00e676; }
.bot-row-negative { background: linear-gradient(90deg, rgba(255,82,82,0.28), rgba(255,82,82,0.09)); border-left: 7px solid #ff5252; }
.bot-row-flat { background: linear-gradient(90deg, rgba(96,125,139,0.30), rgba(96,125,139,0.10)); border-left: 7px solid #b0bec5; }
.child-row { margin-left: 8px; border-left-width: 4px; padding: 10px 11px; opacity: 0.96; }
.bot-topline { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.bot-name { color: white; font-size: 0.95rem; font-weight: 900; line-height: 1.15rem; }
.child-name { font-size: 0.86rem; }
.bot-pnl-positive, .bot-pnl-negative, .bot-pnl-flat { font-size: 1.15rem; font-weight: 900; white-space: nowrap; }
.bot-subline { display: flex; justify-content: space-between; gap: 8px; margin-top: 8px; color: #d6e2ea; font-size: 0.76rem; font-weight: 700; flex-wrap: wrap; }
.tiny { color: #90a4ae; font-size: 0.68rem; margin-top: 5px; }
.section-title { color: #f5f7fa; font-size: 0.9rem; font-weight: 900; text-transform: uppercase; margin: 16px 0 8px 0; letter-spacing: 0.04em; }
div[data-testid="stExpander"] { border: 0 !important; background: transparent !important; }
div[data-testid="stExpander"] details { border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; background: rgba(255,255,255,0.04); margin-bottom: 10px; }
div[data-testid="stExpander"] summary { color: #f5f7fa !important; font-weight: 900; }
</style>
""", unsafe_allow_html=True)

st.title("Alpaca Fleet Sleep Check")
st.caption("Combined mobile view across separated Google Sheets")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# The sheet IDs below came from your launcher .bat files.
BOT_SHEETS = [
    {
        "name": "Fusion Portfolio",
        "spreadsheet_id": "1fRCRhiJ_5eNwJCBRW9EXwZRW4Gu6WkEXld_a760EiPY",
        "type": "single",
    },
    {
        "name": "Fusion 15",
        "spreadsheet_id": "1jP2KCG06Ai0PcZ9_zjcZ6sOx0srv_ZoUVWujvnfZDmk",
        "type": "single",
    },
    {
        "name": "Fusion Smart SL",
        "spreadsheet_id": "1AD9Zkr1DRBUl74JbMxdQDbtdeVqV97s-3qac-hiddjo",
        "type": "single",
    },
    {
        "name": "Fusion Half Runner",
        "spreadsheet_id": "18OiMDUaOWyF0LhHdmVrJUCUhsQU2bT7o0ArDWaCmLjs",
        "type": "single",
    },
    {
        "name": "Apex 50K 3-Bot Portfolio",
        "spreadsheet_id": "1pgYoFqiWDGLXh-GYCkFQ76oxT8v-kSQJ9EpSJkEAuHk",
        "type": "group",
        "children": ["METALS ORB", "STRUCTURE HUNTER ORB", "QUALITY SIZER"],
    },
]

NUMERIC_COLUMNS = [
    "equity", "buying_power", "open_positions", "open_orders", "qty",
    "buy_price", "sell_price", "pnl", "pnl_pct", "avg_entry_price",
]


def get_credentials():
    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    if os.path.exists("google_credentials.json"):
        return Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)
    st.error("No Google credentials found. Add gcp_service_account to Streamlit Secrets or place google_credentials.json beside this app.")
    st.stop()


def clean_dataframe(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df.columns = [str(c).strip() for c in df.columns]
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_spreadsheet(spreadsheet_id):
    client = gspread.authorize(get_credentials())
    spreadsheet = client.open_by_key(spreadsheet_id)
    snapshots = {}
    trades = {}

    for worksheet in spreadsheet.worksheets():
        rows = worksheet.get_all_records()
        if not rows:
            continue
        df = clean_dataframe(rows)
        if df.empty:
            continue

        title = worksheet.title.strip()
        title_lower = title.lower()
        if title_lower.endswith(" trades"):
            trades[title[:-7].strip()] = df
            continue

        # Snapshot tabs need equity. Ignore helper/config tabs that do not look like account snapshots.
        if "equity" not in df.columns:
            continue
        df = df[df["equity"].fillna(0) > 0]
        if not df.empty:
            snapshots[title] = df

    return snapshots, trades


def norm(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def best_snapshot_for_name(snapshots, wanted_name):
    if not snapshots:
        return None, pd.DataFrame()
    wanted = norm(wanted_name)
    for title, df in snapshots.items():
        if norm(title) == wanted:
            return title, df
    for title, df in snapshots.items():
        if wanted in norm(title) or norm(title) in wanted:
            return title, df
    # Prefer the newest tab if no names match.
    newest_title = None
    newest_time = None
    for title, df in snapshots.items():
        if "timestamp" in df.columns and not df["timestamp"].dropna().empty:
            t = df["timestamp"].dropna().iloc[-1]
        else:
            t = pd.Timestamp.min
        if newest_time is None or t > newest_time:
            newest_title, newest_time = title, t
    return newest_title, snapshots[newest_title]


def calc_delta(df):
    latest = float(df.iloc[-1].get("equity", 0) or 0)
    previous = float(df.iloc[-2].get("equity", latest) or latest) if len(df) > 1 else latest
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


def safe_int(value):
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def fmt_time(value):
    if pd.isna(value) or value == "":
        return ""
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def trade_count(trades, tab_name):
    if not trades:
        return 0
    title, df = best_snapshot_for_name(trades, tab_name)
    if df is None or df.empty:
        return 0
    return len(df)


def row_from_snapshot(display_name, tab_name, df, trades, detail_only=False):
    equity, pnl, pct = calc_delta(df)
    latest = df.iloc[-1]
    return {
        "bot_name": display_name,
        "tab_name": tab_name,
        "equity": equity,
        "pnl": pnl,
        "pct": pct,
        "buying_power": float(latest.get("buying_power", 0) or 0),
        "positions": safe_int(latest.get("open_positions", 0)),
        "orders": safe_int(latest.get("open_orders", 0)),
        "last_update": latest.get("timestamp", ""),
        "trades": trade_count(trades, tab_name),
        "detail_only": detail_only,
    }


def make_single_row(config, snapshots, trades):
    tab_name, df = best_snapshot_for_name(snapshots, config["name"])
    if df is None or df.empty:
        return None
    return row_from_snapshot(config["name"], tab_name, df, trades)


def make_group_row(config, snapshots, trades):
    children = []
    used_tabs = set()

    for child_name in config.get("children", []):
        tab_name, df = best_snapshot_for_name({k: v for k, v in snapshots.items() if k not in used_tabs}, child_name)
        if df is not None and not df.empty:
            used_tabs.add(tab_name)
            children.append(row_from_snapshot(child_name, tab_name, df, trades, detail_only=True))

    # If the sheet has extra snapshot tabs, show them as detail too.
    for tab_name, df in snapshots.items():
        if tab_name not in used_tabs:
            children.append(row_from_snapshot(tab_name, tab_name, df, trades, detail_only=True))

    if not children:
        return None, []

    # Parent account card: use the newest child snapshot for account equity/BP.
    # This avoids triple-counting one Alpaca account when 3 bots log the same account sheet.
    parent_source = max(children, key=lambda r: pd.to_datetime(r["last_update"], errors="coerce") if r["last_update"] != "" else pd.Timestamp.min)
    parent = dict(parent_source)
    parent["bot_name"] = config["name"]
    parent["tab_name"] = "account-level from newest child snapshot"
    parent["detail_only"] = False

    # Positions/orders are account-level fields in each child log. Use max, not sum.
    parent["positions"] = max((c["positions"] for c in children), default=0)
    parent["orders"] = max((c["orders"] for c in children), default=0)
    parent["trades"] = sum(c["trades"] for c in children)
    return parent, children


def render_row(row, child=False):
    cls = pnl_class(row["pnl"])
    child_class = " child-row" if child else ""
    name_class = "bot-name child-name" if child else "bot-name"
    st.markdown(
        f'''<div class="bot-row bot-row-{cls}{child_class}">
            <div class="bot-topline">
                <div class="{name_class}">{row["bot_name"]}</div>
                <div class="bot-pnl-{cls}">{row["pnl"]:+,.0f}</div>
            </div>
            <div class="bot-subline"><span>Equity {money(row["equity"])}</span><span>{row["pct"]:+.2f}%</span></div>
            <div class="bot-subline"><span>Pos {row["positions"]}</span><span>Orders {row["orders"]}</span><span>Trades {row["trades"]}</span></div>
            <div class="tiny">Last: {fmt_time(row["last_update"])} | Source: {row["tab_name"]}</div>
        </div>''',
        unsafe_allow_html=True,
    )


fleet_rows = []
group_children = {}
load_errors = []

with st.spinner("Loading bot sheets..."):
    for config in BOT_SHEETS:
        try:
            snapshots, trades = load_spreadsheet(config["spreadsheet_id"])
            if config.get("type") == "group":
                parent, children = make_group_row(config, snapshots, trades)
                if parent:
                    fleet_rows.append(parent)
                    group_children[parent["bot_name"]] = children
            else:
                row = make_single_row(config, snapshots, trades)
                if row:
                    fleet_rows.append(row)
                else:
                    load_errors.append(f"{config['name']}: no snapshot tab with equity found")
        except Exception as e:
            load_errors.append(f"{config['name']}: {type(e).__name__}: {e}")

if not fleet_rows:
    st.warning("No valid bot rows found yet.")
    if load_errors:
        st.error("\n".join(load_errors))
    st.stop()

# Grand total uses parent account rows only. Apex child rows stay detail-only.
total_equity = sum(r["equity"] for r in fleet_rows)
total_bp = sum(r["buying_power"] for r in fleet_rows)
total_pnl = sum(r["pnl"] for r in fleet_rows)
total_positions = sum(r["positions"] for r in fleet_rows)
total_orders = sum(r["orders"] for r in fleet_rows)
cls = pnl_class(total_pnl)

st.markdown(
    f'''<div class="summary-card"><div class="summary-label">Total Fleet Equity</div><div class="summary-value">{money(total_equity)}</div><div class="summary-pnl-{cls}">{total_pnl:+,.0f}</div></div>''',
    unsafe_allow_html=True,
)

s1, s2 = st.columns(2)
with s1:
    st.markdown(f'''<div class="summary-card"><div class="summary-label">Buying Power</div><div class="summary-value" style="font-size:1.35rem;">{money(total_bp)}</div></div>''', unsafe_allow_html=True)
with s2:
    st.markdown(f'''<div class="summary-card"><div class="summary-label">Open Risk</div><div class="summary-value" style="font-size:1.35rem;">{total_positions} pos / {total_orders} ord</div></div>''', unsafe_allow_html=True)

st.markdown('<div class="section-title">Bots</div>', unsafe_allow_html=True)

# Keep user's preferred order from BOT_SHEETS.
for row in fleet_rows:
    render_row(row)
    children = group_children.get(row["bot_name"], [])
    if children:
        with st.expander("Show Apex 50K bot details", expanded=False):
            for child in children:
                render_row(child, child=True)

if load_errors:
    with st.expander("Load warnings", expanded=False):
        for err in load_errors:
            st.warning(err)

st.caption("Fleet sleep-check layout. Refreshes every 30 seconds. Apex 50K child bots are detail rows only, so they are not double-counted in the fleet total.")
