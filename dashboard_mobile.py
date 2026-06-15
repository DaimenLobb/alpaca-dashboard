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
.summary-pnl-positive, .bot-pnl-positive, .since-positive { color: #00e676; }
.summary-pnl-negative, .bot-pnl-negative, .since-negative { color: #ff5252; }
.summary-pnl-flat, .bot-pnl-flat, .since-flat { color: #cfd8dc; }
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
.since-line { margin-top: 6px; font-size: 0.76rem; font-weight: 900; }
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
DEFAULT_START_EQUITY = 50000.0

# Apex 50K is one account split across three strategy allocations, not three separate $50k bots.
APEX_50K_CHILDREN = [
    {"name": "METALS ORB", "bot_id": "METALS_ORB", "start_equity": 22500.0, "allocation": "45%"},
    {"name": "STRUCTURE HUNTER ORB", "bot_id": "STRUCTURE_ORB", "start_equity": 17500.0, "allocation": "35%"},
    {"name": "QUALITY SIZER", "bot_id": "QUALITY_SIZER", "start_equity": 10000.0, "allocation": "20%"},
]


BOT_SHEETS = [
    {
        "name": "Fusion Portfolio",
        "spreadsheet_id": "1fRCRhiJ_5eNwJCBRW9EXwZRW4Gu6WkEXld_a760EiPY",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
    {
        "name": "Fusion 15",
        "spreadsheet_id": "1jP2KCG06Ai0PcZ9_zjcZ6sOx0srv_ZoUVWujvnfZDmk",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
    {
        "name": "Fusion Smart SL",
        "spreadsheet_id": "1AD9Zkr1DRBUl74JbMxdQDbtdeVqV97s-3qac-hiddjo",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
    {
        "name": "Fusion Half Runner",
        "spreadsheet_id": "18OiMDUaOWyF0LhHdmVrJUCUhsQU2bT7o0ArDWaCmLjs",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
    {
        "name": "Apex 50K 3-Bot Portfolio",
        "spreadsheet_id": "1pgYoFqiWDGLXh-GYCkFQ76oxT8v-kSQJ9EpSJkEAuHk",
        "type": "group",
        "start_equity": DEFAULT_START_EQUITY,
        "children": APEX_50K_CHILDREN,
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


def row_identity_text(df):
    """Return searchable identity text from the newest row.

    Some Apex 50K tabs are named differently from the display labels, so matching
    only the worksheet title can accidentally reuse the newest tab for more than
    one child bot. This also checks bot_name/account_name/bot_id fields.
    """
    if df is None or df.empty:
        return ""
    latest = df.iloc[-1]
    parts = []
    for col in ["bot_name", "account_name", "bot_id"]:
        if col in df.columns:
            value = latest.get(col, "")
            if value is not None:
                parts.append(str(value))
    return " ".join(parts)


def identity_matches(text, wanted_name):
    text_n = norm(text)
    wanted_n = norm(wanted_name)
    if not text_n or not wanted_n:
        return False
    if wanted_n in text_n or text_n in wanted_n:
        return True
    # Strong aliases used by the Apex 50K three-bot account.
    aliases = {
        "metals orb": ["metals orb", "metals orb retest", "light trend"],
        "structure hunter orb": ["structure hunter orb", "apex structure hunter"],
        "quality sizer": ["quality sizer", "apex quality sizer"],
    }
    for alias in aliases.get(wanted_n, []):
        if norm(alias) in text_n:
            return True
    return False


def filter_snapshot_by_bot_id(snapshots, wanted_bot_id):
    """Return the rows for one bot_id across all snapshot tabs.

    Apex 50K writes three strategies into the same sheet/account. Matching by
    worksheet name or newest timestamp can reuse the wrong bot. This function
    uses the bot_id column first, which is the reliable identifier:
    METALS_ORB, STRUCTURE_ORB, QUALITY_SIZER.
    """
    if not snapshots or not wanted_bot_id:
        return None, pd.DataFrame()

    wanted = norm(wanted_bot_id)
    matches = []

    for title, df in snapshots.items():
        if df is None or df.empty or "bot_id" not in df.columns:
            continue
        mask = df["bot_id"].astype(str).map(norm) == wanted
        filtered = df.loc[mask].copy()
        if filtered.empty:
            continue
        source_name = title
        if "bot_name" in filtered.columns:
            latest_name = str(filtered.iloc[-1].get("bot_name", "") or "").strip()
            if latest_name:
                source_name = latest_name
        matches.append((source_name, filtered))

    if not matches:
        return None, pd.DataFrame()

    # If the same bot_id appears in more than one tab, combine and sort so daily
    # P/L uses the last two rows for that exact bot only.
    combined = pd.concat([m[1] for m in matches], ignore_index=True)
    if "timestamp" in combined.columns:
        combined = combined.dropna(subset=["timestamp"]).sort_values("timestamp")
    source_names = []
    for source_name, _ in matches:
        if source_name not in source_names:
            source_names.append(source_name)
    return " / ".join(source_names), combined


def trade_count_for_bot_id(trades, wanted_bot_id):
    if not trades or not wanted_bot_id:
        return 0
    wanted = norm(wanted_bot_id)
    total = 0
    for _, df in trades.items():
        if df is None or df.empty or "bot_id" not in df.columns:
            continue
        total += int((df["bot_id"].astype(str).map(norm) == wanted).sum())
    return total


def best_snapshot_for_name(snapshots, wanted_name, allow_fallback=True):
    if not snapshots:
        return None, pd.DataFrame()

    wanted = norm(wanted_name)

    # 1) Exact worksheet title match.
    for title, df in snapshots.items():
        if norm(title) == wanted:
            return title, df

    # 2) Exact/latest row identity match from bot_name/account_name/bot_id.
    for title, df in snapshots.items():
        if identity_matches(row_identity_text(df), wanted_name):
            return title, df

    # 3) Partial worksheet title match.
    for title, df in snapshots.items():
        if wanted in norm(title) or norm(title) in wanted:
            return title, df

    # 4) Fallback to newest tab only for single-account sheets. For grouped child
    # rows, fallback is disabled so the same newest tab is not reused incorrectly.
    if not allow_fallback:
        return None, pd.DataFrame()

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


def since_start_values(row):
    start = float(row.get("start_equity", DEFAULT_START_EQUITY) or DEFAULT_START_EQUITY)
    equity = float(row.get("equity", 0) or 0)
    gain = equity - start
    pct = 0.0 if start == 0 else (gain / start) * 100
    return start, gain, pct


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


def trade_count(trades, tab_name, bot_id=None):
    if bot_id:
        return trade_count_for_bot_id(trades, bot_id)
    if not trades:
        return 0
    title, df = best_snapshot_for_name(trades, tab_name)
    if df is None or df.empty:
        return 0
    return len(df)


def row_from_snapshot(display_name, tab_name, df, trades, detail_only=False, start_equity=DEFAULT_START_EQUITY, bot_id=None, allocation=None):
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
        "trades": trade_count(trades, tab_name, bot_id=bot_id),
        "detail_only": detail_only,
        "start_equity": float(start_equity or DEFAULT_START_EQUITY),
        "bot_id": bot_id or str(latest.get("bot_id", "") or ""),
        "allocation": allocation or "",
    }


def make_single_row(config, snapshots, trades):
    tab_name, df = best_snapshot_for_name(snapshots, config["name"])
    if df is None or df.empty:
        return None
    return row_from_snapshot(config["name"], tab_name, df, trades, start_equity=config.get("start_equity", DEFAULT_START_EQUITY))


def make_group_row(config, snapshots, trades):
    children = []

    for child in config.get("children", []):
        child_name = child.get("name", "")
        child_bot_id = child.get("bot_id", "")
        tab_name, df = filter_snapshot_by_bot_id(snapshots, child_bot_id)

        # Fallback only if the sheet does not have bot_id. With bot_id available,
        # no fallback is used because it can reuse another bot's newest row.
        if (df is None or df.empty) and not any("bot_id" in s.columns for s in snapshots.values()):
            tab_name, df = best_snapshot_for_name(snapshots, child_name, allow_fallback=False)

        if df is not None and not df.empty:
            children.append(row_from_snapshot(
                child_name,
                tab_name,
                df,
                trades,
                detail_only=True,
                start_equity=child.get("start_equity", DEFAULT_START_EQUITY),
                bot_id=child_bot_id,
                allocation=child.get("allocation", ""),
            ))

    if not children:
        return None, []

    # Parent account card: Apex 50K is one Alpaca account split by allocation.
    # The child rows are already the allocated equity rows for each bot_id, so
    # the parent equity is the sum of METALS_ORB + STRUCTURE_ORB + QUALITY_SIZER.
    latest_child = max(children, key=lambda r: pd.to_datetime(r["last_update"], errors="coerce") if r["last_update"] != "" else pd.Timestamp.min)
    parent_equity = sum(float(c.get("equity", 0) or 0) for c in children)
    parent_bp = sum(float(c.get("buying_power", 0) or 0) for c in children)
    parent_pnl = sum(float(c.get("pnl", 0) or 0) for c in children)
    previous_equity = parent_equity - parent_pnl
    parent_pct = 0.0 if previous_equity == 0 else (parent_pnl / previous_equity) * 100

    parent = {
        "bot_name": config["name"],
        "tab_name": "account total from summed bot_id allocations",
        "equity": parent_equity,
        "pnl": parent_pnl,
        "pct": parent_pct,
        "buying_power": parent_bp,
        "positions": max((c["positions"] for c in children), default=0),
        "orders": max((c["orders"] for c in children), default=0),
        "last_update": latest_child.get("last_update", ""),
        "trades": sum(c["trades"] for c in children),
        "detail_only": False,
        "start_equity": float(config.get("start_equity", DEFAULT_START_EQUITY)),
        "bot_id": "APEX_50K_GROUP",
        "allocation": "100%",
    }
    return parent, children

def render_row(row, child=False):
    cls = pnl_class(row["pnl"])
    start, since_gain, since_pct = since_start_values(row)
    since_cls = pnl_class(since_gain)
    child_class = " child-row" if child else ""
    name_class = "bot-name child-name" if child else "bot-name"
    equity_label = "Bot Equity" if child else "Equity"
    source_label = "Apex bot source" if child else "Source"
    allocation_text = f"<span>Allocation {row.get('allocation')}</span>" if child and row.get("allocation") else ""
    bot_id_text = f" | bot_id: {row.get('bot_id')}" if child and row.get("bot_id") else ""
    st.markdown(
        f'''<div class="bot-row bot-row-{cls}{child_class}">
            <div class="bot-topline">
                <div class="{name_class}">{row["bot_name"]}</div>
                <div class="bot-pnl-{cls}">Today {row["pnl"]:+,.0f}</div>
            </div>
            <div class="bot-subline"><span>{equity_label} {money(row["equity"])}</span><span>Daily {row["pct"]:+.2f}%</span>{allocation_text}</div>
            <div class="since-line since-{since_cls}">Since {money(start)}: {since_gain:+,.0f} ({since_pct:+.2f}%)</div>
            <div class="bot-subline"><span>Pos {row["positions"]}</span><span>Orders {row["orders"]}</span><span>Trades {row["trades"]}</span></div>
            <div class="tiny">Last: {fmt_time(row["last_update"])} | {source_label}: {row["tab_name"]}{bot_id_text}</div>
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
total_start = sum(float(r.get("start_equity", DEFAULT_START_EQUITY) or DEFAULT_START_EQUITY) for r in fleet_rows)
total_since = total_equity - total_start
total_since_pct = 0.0 if total_start == 0 else (total_since / total_start) * 100
cls = pnl_class(total_pnl)
since_cls = pnl_class(total_since)

st.markdown(
    f'''<div class="summary-card"><div class="summary-label">Total Fleet Equity</div><div class="summary-value">{money(total_equity)}</div><div class="summary-pnl-{cls}">Today {total_pnl:+,.0f}</div><div class="since-line since-{since_cls}">Since {money(total_start)}: {total_since:+,.0f} ({total_since_pct:+.2f}%)</div></div>''',
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
        with st.expander("Show Apex 50K bot equity tracking", expanded=True):
            st.caption("These three equity rows are shown for tracking only and are not added into Total Fleet Equity.")
            for child in children:
                render_row(child, child=True)

if load_errors:
    with st.expander("Load warnings", expanded=False):
        for err in load_errors:
            st.warning(err)

st.caption("Fleet sleep-check layout. Refreshes every 30 seconds. Today P/L stays prominent; Apex 50K parent equity is the summed account total from exact bot_id rows; child rows show Metals 45%, Structure 35%, Quality 20% and are not double-counted.")
