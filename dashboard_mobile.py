import os
import json
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
.rank-badge { display: inline-block; margin-right: 7px; font-weight: 900; color: #ffd54f; }
.child-name { font-size: 0.86rem; }
.bot-pnl-positive, .bot-pnl-negative, .bot-pnl-flat { font-size: 1.15rem; font-weight: 900; white-space: nowrap; }
.bot-subline { display: flex; justify-content: space-between; gap: 8px; margin-top: 8px; color: #d6e2ea; font-size: 0.76rem; font-weight: 700; flex-wrap: wrap; }
.since-line { margin-top: 6px; font-size: 0.76rem; font-weight: 900; }
.tiny { color: #90a4ae; font-size: 0.68rem; margin-top: 5px; }
.section-title { color: #f5f7fa; font-size: 0.9rem; font-weight: 900; text-transform: uppercase; margin: 16px 0 8px 0; letter-spacing: 0.04em; }
div[data-testid="stExpander"] { border: 0 !important; background: transparent !important; }
div[data-testid="stExpander"] details { border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; background: rgba(255,255,255,0.04); margin-bottom: 10px; }
div[data-testid="stExpander"] summary { color: #f5f7fa !important; font-weight: 900; }
.trade-table { width: 100%; border-collapse: collapse; margin: 8px 0 14px 0; font-size: 0.72rem; color: #e9f1f5; }
.trade-table th { color: #d6e2ea; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.18); padding: 5px; }
.trade-table td { padding: 5px; border-bottom: 1px solid rgba(255,255,255,0.08); }
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
        # Trade tabs can be named "BOT Trades" or "BOT Trades (Legacy)".
        # Anything with "trade" in the title is treated as a trade log.
        if "trade" in title_lower:
            clean_title = title.replace("(Legacy)", "").replace("Trades", "").replace("trades", "").strip()
            trades[clean_title] = df
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


def all_trade_rows(trades):
    frames = []
    for title, df in (trades or {}).items():
        if df is None or df.empty:
            continue
        tdf = df.copy()
        tdf["trade_tab"] = title
        if "timestamp" in tdf.columns:
            tdf["timestamp"] = pd.to_datetime(tdf["timestamp"], errors="coerce", utc=True)
        frames.append(tdf)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    if "timestamp" in out.columns:
        out = out.dropna(subset=["timestamp"]).sort_values("timestamp")
    if "pnl" in out.columns:
        out["pnl"] = pd.to_numeric(out["pnl"], errors="coerce").fillna(0.0)
    return out


def filter_trade_rows(trades, bot_id=None, trade_date=None):
    df = all_trade_rows(trades)
    if df.empty:
        return df
    if bot_id and "bot_id" in df.columns:
        wanted = norm(bot_id)
        df = df[df["bot_id"].astype(str).map(norm) == wanted].copy()
    if df.empty:
        return df
    if "timestamp" in df.columns:
        et_times = df["timestamp"].dt.tz_convert("America/New_York")
        df["trade_day_et"] = et_times.dt.date
        df["time_et"] = et_times.dt.strftime("%H:%M")
        if trade_date is None:
            trade_date = df["trade_day_et"].max()
        df = df[df["trade_day_et"] == trade_date].copy()
    return df


def trade_pnl_and_rows(trades, bot_id=None, trade_date=None):
    df = filter_trade_rows(trades, bot_id=bot_id, trade_date=trade_date)
    if df.empty or "pnl" not in df.columns:
        return 0.0, df
    return float(df["pnl"].sum()), df


def trade_count_for_rows(df):
    return 0 if df is None or df.empty else len(df)


def trade_table_html(df):
    if df is None or df.empty:
        return "<div class='tiny'>No trades logged for this trading day.</div>"
    cols = [c for c in ["time_et", "symbol", "side", "qty", "entry_price", "exit_price", "pnl", "pnl_pct", "exit_reason", "status"] if c in df.columns]
    view = df[cols].copy()
    rename = {
        "time_et": "Time ET", "symbol": "Symbol", "side": "Side", "qty": "Qty",
        "entry_price": "Entry", "exit_price": "Exit", "pnl": "P/L", "pnl_pct": "%",
        "exit_reason": "Exit", "status": "Status",
    }
    view = view.rename(columns=rename)
    for col in ["Entry", "Exit"]:
        if col in view.columns:
            view[col] = pd.to_numeric(view[col], errors="coerce").map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
    if "P/L" in view.columns:
        view["P/L"] = pd.to_numeric(view["P/L"], errors="coerce").map(lambda x: "" if pd.isna(x) else f"${x:,.2f}")
    if "%" in view.columns:
        view["%"] = pd.to_numeric(view["%"], errors="coerce").map(lambda x: "" if pd.isna(x) else f"{x:+.2f}%")
    if "Qty" in view.columns:
        view["Qty"] = pd.to_numeric(view["Qty"], errors="coerce").map(lambda x: "" if pd.isna(x) else f"{x:,.0f}")
    return view.to_html(index=False, escape=True, classes="trade-table")


def render_trade_details(row, key_prefix="trade"):
    trades_df = row.get("trade_rows")
    trade_pnl = float(row.get("trade_pnl", 0) or 0)
    trade_day = row.get("trade_day", "")
    st.markdown(
        f"<div class='tiny'><b>Trades {trade_day}</b> | Total realised P/L {trade_pnl:+,.2f}</div>" + trade_table_html(trades_df),
        unsafe_allow_html=True,
    )


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


def allocation_fraction(value):
    """Convert allocation strings like '45%' or numbers like 0.45 into a fraction."""
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            s = value.strip().replace('%', '')
            if not s:
                return 0.0
            v = float(s)
            return v / 100.0 if v > 1 else v
        v = float(value)
        return v / 100.0 if v > 1 else v
    except Exception:
        return 0.0


def median_account_total_from_children(children, use_previous=False):
    """Estimate the shared Apex account total from child rows and allocations.

    Some Apex child snapshot rows can contain a strategy-specific figure that is
    stale or transformed. The reliable account total is the common account value
    implied by allocated rows: child_equity / allocation. Taking the median keeps
    one bad child row from breaking the whole Apex section.
    """
    estimates = []
    for child in children:
        frac = allocation_fraction(child.get('allocation'))
        if frac <= 0:
            continue
        value = child.get('previous_equity' if use_previous else 'equity', 0)
        try:
            value = float(value or 0)
        except Exception:
            value = 0.0
        if value > 0:
            estimates.append(value / frac)
    if not estimates:
        return 0.0
    estimates = sorted(estimates)
    mid = len(estimates) // 2
    if len(estimates) % 2:
        return estimates[mid]
    return (estimates[mid - 1] + estimates[mid]) / 2.0


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




BASELINE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sleep_check_leaderboard_baselines.json")


def baseline_key(row):
    key = str(row.get("bot_id") or row.get("bot_name") or "").strip()
    return key or str(row.get("bot_name", ""))


def load_baselines():
    try:
        if os.path.exists(BASELINE_FILE):
            with open(BASELINE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"created_at": datetime.now().isoformat(), "baselines": {}}


def save_baselines(data):
    try:
        tmp = BASELINE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, BASELINE_FILE)
    except Exception as e:
        st.warning(f"Could not save leaderboard baselines: {type(e).__name__}: {e}")


def apply_leaderboard_baselines(rows, children_by_group):
    """Set each bot's leaderboard start value and P/L.

    The old green 'Since allocation' line was not real P/L. This starts the
    leaderboard from the first run of this version, so current values show 0 and
    future movement is true P/L per bot/account.
    """
    data = load_baselines()
    baselines = data.setdefault("baselines", {})
    changed = False

    all_rows = list(rows)
    for child_list in children_by_group.values():
        all_rows.extend(child_list)

    for row in all_rows:
        key = baseline_key(row)
        if key not in baselines:
            baselines[key] = float(row.get("equity", 0) or 0)
            changed = True
        start = float(baselines.get(key, row.get("equity", 0)) or 0)
        equity = float(row.get("equity", 0) or 0)
        row["leaderboard_start"] = start
        if int(row.get("trades", 0) or 0) > 0:
            row["leaderboard_pnl"] = float(row.get("pnl", 0) or 0)
            row["leaderboard_pct"] = 0.0 if start == 0 else (float(row.get("pnl", 0) or 0) / start) * 100
        else:
            row["leaderboard_pnl"] = equity - start
            row["leaderboard_pct"] = 0.0 if start == 0 else ((equity - start) / start) * 100

    if changed:
        save_baselines(data)
    return data

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
    previous_equity = equity - pnl
    latest = df.iloc[-1]
    actual_bot_id = bot_id or str(latest.get("bot_id", "") or "")
    trade_pnl, trade_rows = trade_pnl_and_rows(trades, bot_id=actual_bot_id or None)
    trade_day = ""
    if trade_rows is not None and not trade_rows.empty and "trade_day_et" in trade_rows.columns:
        trade_day = str(trade_rows["trade_day_et"].max())
    return {
        "bot_name": display_name,
        "tab_name": tab_name,
        "equity": equity,
        "previous_equity": previous_equity,
        "pnl": trade_pnl if trade_count_for_rows(trade_rows) > 0 else pnl,
        "snapshot_pnl": pnl,
        "pct": (0.0 if previous_equity == 0 else ((trade_pnl if trade_count_for_rows(trade_rows) > 0 else pnl) / previous_equity) * 100),
        "buying_power": float(latest.get("buying_power", 0) or 0),
        "positions": safe_int(latest.get("open_positions", 0)),
        "orders": safe_int(latest.get("open_orders", 0)),
        "last_update": latest.get("timestamp", ""),
        "trades": trade_count_for_rows(trade_rows),
        "trade_pnl": trade_pnl,
        "trade_rows": trade_rows,
        "trade_day": trade_day,
        "detail_only": detail_only,
        "start_equity": float(start_equity or DEFAULT_START_EQUITY),
        "bot_id": actual_bot_id,
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
    # Use the shared account total implied by the bot_id rows, then recalculate
    # each child as its allocation of that total. This fixes cases where a child
    # row has a stale/transformed equity figure while the allocation is known.
    latest_child = max(children, key=lambda r: pd.to_datetime(r["last_update"], errors="coerce") if r["last_update"] != "" else pd.Timestamp.min)
    parent_equity = median_account_total_from_children(children, use_previous=False)
    previous_equity = median_account_total_from_children(children, use_previous=True) or parent_equity
    # Daily P/L for Apex should come from the exact bot_id trade tabs when trades exist.
    # This catches the case where bots traded/logged on the trade tabs but snapshots stayed flat.
    trade_parent_pnl = sum(float(c.get("trade_pnl", 0) or 0) for c in children)
    trade_parent_count = sum(int(c.get("trades", 0) or 0) for c in children)
    parent_pnl = trade_parent_pnl if trade_parent_count > 0 else (parent_equity - previous_equity)
    parent_pct = 0.0 if previous_equity == 0 else (parent_pnl / previous_equity) * 100

    for child in children:
        frac = allocation_fraction(child.get("allocation"))
        if frac > 0 and parent_equity > 0:
            child["equity"] = parent_equity * frac
            child["previous_equity"] = previous_equity * frac
            if int(child.get("trades", 0) or 0) <= 0:
                child["pnl"] = child["equity"] - child["previous_equity"]
            else:
                child["pnl"] = float(child.get("trade_pnl", 0) or 0)
            child["pct"] = 0.0 if child["previous_equity"] == 0 else (child["pnl"] / child["previous_equity"]) * 100

    parent_bp = sum(float(c.get("buying_power", 0) or 0) for c in children)

    parent = {
        "bot_name": config["name"],
        "tab_name": "account total inferred from bot_id allocations",
        "equity": parent_equity,
        "pnl": parent_pnl,
        "pct": parent_pct,
        "buying_power": parent_bp,
        "positions": max((c["positions"] for c in children), default=0),
        "orders": max((c["orders"] for c in children), default=0),
        "last_update": latest_child.get("last_update", ""),
        "trades": sum(c["trades"] for c in children),
        "trade_pnl": trade_parent_pnl,
        "trade_rows": pd.concat([c.get("trade_rows", pd.DataFrame()) for c in children if c.get("trade_rows") is not None and not c.get("trade_rows").empty], ignore_index=True) if any(c.get("trade_rows") is not None and not c.get("trade_rows").empty for c in children) else pd.DataFrame(),
        "trade_day": next((c.get("trade_day", "") for c in children if c.get("trade_day", "")), ""),
        "detail_only": False,
        "start_equity": float(config.get("start_equity", DEFAULT_START_EQUITY)),
        "bot_id": "APEX_50K_GROUP",
        "allocation": "100%",
    }
    return parent, children

def rank_badge(rank):
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    return f"#{rank}"


def render_row(row, child=False, rank=None):
    display_pnl = float(row.get("leaderboard_pnl", row.get("pnl", 0)) or 0)
    cls = pnl_class(display_pnl)
    lb_start = float(row.get("leaderboard_start", row.get("equity", 0)) or 0)
    lb_pct = float(row.get("leaderboard_pct", 0) or 0)
    since_cls = pnl_class(display_pnl)
    child_class = " child-row" if child else ""
    name_class = "bot-name child-name" if child else "bot-name"
    equity_label = "Bot Equity" if child else "Equity"
    source_label = "Apex bot source" if child else "Source"
    allocation_text = f"<span>Allocation {row.get('allocation')}</span>" if child and row.get("allocation") else ""
    bot_id_text = f" | bot_id: {row.get('bot_id')}" if child and row.get("bot_id") else ""
    badge_html = f'<span class="rank-badge">{rank_badge(rank)}</span>' if rank else ""
    st.markdown(
        f'''<div class="bot-row bot-row-{cls}{child_class}">
            <div class="bot-topline">
                <div class="{name_class}">{badge_html}{row["bot_name"]}</div>
                <div class="bot-pnl-{cls}">P/L {display_pnl:+,.0f}</div>
            </div>
            <div class="bot-subline"><span>{equity_label} {money(row["equity"])}</span><span>Daily {row["pnl"]:+,.0f} ({row["pct"]:+.2f}%)</span>{allocation_text}</div>
            <div class="since-line since-{since_cls}">Leaderboard from {money(lb_start)}: {display_pnl:+,.0f} ({lb_pct:+.2f}%)</div>
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

baseline_data = apply_leaderboard_baselines(fleet_rows, group_children)

# Grand total uses parent account rows only. Apex child rows stay detail-only.
total_equity = sum(r["equity"] for r in fleet_rows)
total_bp = sum(r["buying_power"] for r in fleet_rows)
total_pnl = sum(float(r.get("leaderboard_pnl", r.get("pnl", 0)) or 0) for r in fleet_rows)
total_daily_pnl = sum(r["pnl"] for r in fleet_rows)
total_positions = sum(r["positions"] for r in fleet_rows)
total_orders = sum(r["orders"] for r in fleet_rows)
total_start = sum(float(r.get("start_equity", DEFAULT_START_EQUITY) or DEFAULT_START_EQUITY) for r in fleet_rows)
total_since = total_equity - total_start
total_since_pct = 0.0 if total_start == 0 else (total_since / total_start) * 100
cls = pnl_class(total_pnl)
since_cls = pnl_class(total_pnl)

st.markdown(
    f'''<div class="summary-card"><div class="summary-label">Total Fleet Equity</div><div class="summary-value">{money(total_equity)}</div><div class="summary-pnl-{cls}">Leaderboard P/L {total_pnl:+,.0f}</div><div class="since-line since-{since_cls}">Daily total {total_daily_pnl:+,.0f} | Baseline file: {os.path.basename(BASELINE_FILE)}</div></div>''',
    unsafe_allow_html=True,
)

s1, s2 = st.columns(2)
with s1:
    st.markdown(f'''<div class="summary-card"><div class="summary-label">Buying Power</div><div class="summary-value" style="font-size:1.35rem;">{money(total_bp)}</div></div>''', unsafe_allow_html=True)
with s2:
    st.markdown(f'''<div class="summary-card"><div class="summary-label">Open Risk</div><div class="summary-value" style="font-size:1.35rem;">{total_positions} pos / {total_orders} ord</div></div>''', unsafe_allow_html=True)

st.markdown('<div class="section-title">Bots — ranked by P/L</div>', unsafe_allow_html=True)

# Leaderboard cards: best Today P/L at the top.
fleet_rows = sorted(fleet_rows, key=lambda r: (float(r.get("leaderboard_pnl", 0) or 0), float(r.get("equity", 0) or 0)), reverse=True)

for rank, row in enumerate(fleet_rows, start=1):
    render_row(row, rank=rank)
    children = group_children.get(row["bot_name"], [])
    if int(row.get("trades", 0) or 0) > 0:
        with st.expander(f"Show trades for {row['bot_name']} ({row['trades']})", expanded=False):
            render_trade_details(row, key_prefix=f"main-{rank}")
    if children:
        children = sorted(children, key=lambda r: (float(r.get("leaderboard_pnl", 0) or 0), float(r.get("equity", 0) or 0)), reverse=True)
        with st.expander("Show Apex 50K bot equity tracking", expanded=True):
            st.caption("Apex child cards are ranked separately by realised daily/session P/L. They are tracking only and are not added into Total Fleet Equity.")
            for child_rank, child in enumerate(children, start=1):
                render_row(child, child=True, rank=child_rank)
                if int(child.get("trades", 0) or 0) > 0:
                    if st.checkbox(f"Show trades for {child['bot_name']} ({child['trades']})", key=f"apex_child_trades_{child_rank}_{child.get('bot_id','')}"):
                        render_trade_details(child, key_prefix=f"child-{child_rank}")

if load_errors:
    with st.expander("Load warnings", expanded=False):
        for err in load_errors:
            st.warning(err)

st.caption("Fleet sleep-check layout. Refreshes every 30 seconds. Cards are ranked best-to-worst by realised trade P/L when trade tabs have entries; otherwise by the saved leaderboard baseline. Click a bot's trade expander to see the logged trades underneath.")
