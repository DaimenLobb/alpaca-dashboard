import os
import json
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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
.trade-card { border-radius: 14px; padding: 10px 11px; margin: 8px 0; border: 1px solid rgba(255,255,255,0.14); }
.trade-card-positive { background: rgba(0,200,83,0.16); border-left: 5px solid #00e676; }
.trade-card-negative { background: rgba(255,82,82,0.16); border-left: 5px solid #ff5252; }
.trade-card-flat { background: rgba(96,125,139,0.16); border-left: 5px solid #b0bec5; }
.trade-card-top { display: flex; justify-content: space-between; gap: 10px; color: #f5f7fa; font-size: 0.82rem; font-weight: 900; }
.trade-card-sub { color: #d6e2ea; font-size: 0.70rem; font-weight: 700; margin-top: 5px; }

.heartbeat-live {
    display: inline-block;
    color: #00e676;
    font-weight: 900;
    animation: pulse-heart 2s infinite;
    transform-origin: center;
}
.heartbeat-stale {
    color: #ffd54f;
    font-weight: 900;
}
.heartbeat-offline {
    color: #ff5252;
    font-weight: 900;
}
@keyframes pulse-heart {
    0%   { transform: scale(1); }
    25%  { transform: scale(1.12); }
    50%  { transform: scale(1.28); }
    75%  { transform: scale(1.12); }
    100% { transform: scale(1); }
}

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

# Parent-card trade rollups.
# The heartbeat row for a Fusion parent can use a parent bot_id, while completed
# trades are logged by engine/child bot_id. These child ids are counted into the
# parent card and also shown as child sections inside the trade dropdown.
TRADE_CHILDREN = {
    "FUSION_HALF_RUNNER": ["METALS_ORB", "STRUCTURE_ORB", "QUALITY_SIZER"],
    # Fusion 15 currently logs its heartbeat/trades under engine ids, especially QUALITY_SIZER.
    "FUSION_15": ["QUALITY_SIZER", "METALS_ORB", "STRUCTURE_ORB"],
    # Tech Hunter variants seen across bot/logger naming. Harmless if some have no rows.
    "MARKOV_TECH_HUNTER": ["TECH_HUNTER", "MARKOV_TECH_HUNTER", "APEX_MARKOV_TECH_HUNTER"],
}


BOT_SHEETS = [
{
        "name": "Fusion Portfolio",
        "spreadsheet_id": "1fRCRhiJ_5eNwJCBRW9EXwZRW4Gu6WkEXld_a760EiPY",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
        # This account can log rows under the portfolio name and under its engines.
        # Pick the newest matching heartbeat row, not the first/oldest matching tab.
        "source_hints": [
            "FUSION_PORTFOLIO",
            "APEX FUSION PORTFOLIO",
            "METALS_ORB",
            "STRUCTURE_ORB",
            "QUALITY_SIZER",
        ],
        "strict_source_hints": False,
        # Use broker-source daily P/L from the bot snapshot when available.
        "card_pnl_source": "snapshot",
    },
{
        "name": "Fusion 15",
        "spreadsheet_id": "1jP2KCG06Ai0PcZ9_zjcZ6sOx0srv_ZoUVWujvnfZDmk",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
        # The live bot is writing bot_id=QUALITY_SIZER, so do not require the old
        # FUSION_PORTFOLIO_15 id. Use source hints to select the newest row in
        # this Fusion 15 spreadsheet, then roll engine trades into the dropdown.
        "source_hints": [
            "APEX FUSION PORTFOLIO 15 MIN DELAY PAPER BOT",
            "QUALITY_SIZER",
            "METALS_ORB",
            "STRUCTURE_ORB",
        ],
        "strict_source_hints": False,
        "trade_child_ids": TRADE_CHILDREN["FUSION_15"],
        # Card daily P/L must come from Alpaca/account snapshot, not child trade rows.
        # Child trades remain visible/countable in the dropdown.
        "card_pnl_source": "snapshot",
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
        "bot_id": "FUSION_HALF_RUNNER",
        "trade_child_ids": TRADE_CHILDREN["FUSION_HALF_RUNNER"],
    },
{
        "name": "Markov Scout",
        "spreadsheet_id": "1UO6F2RU0spc1JxvJUQT5Z38eD5nohmllcZ6wFH80RtU",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
{
        "name": "Markov Tech Hunter",
        "spreadsheet_id": "1LzOtfEqRsqhGuxbrdiCjAXq7mNLwWfpQYKOgf3wUv9Q",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
        "bot_id": "MARKOV_TECH_HUNTER",
        "source_hints": [
            "APEX MARKOV TECH HUNTER PAPER ACCOUNT",
            "MARKOV_TECH_HUNTER",
            "TECH_HUNTER",
        ],
        "strict_source_hints": False,
        "trade_child_ids": TRADE_CHILDREN["MARKOV_TECH_HUNTER"],
    },
{
        "name": "Structure OG",
        "spreadsheet_id": "1cENU425SU6pzDsCRMjIhhmH2qJ0JtxgAdPpx9eRB3Do",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
{
        "name": "Structure Markov Runner",
        "spreadsheet_id": "1hvg37r1c51xIO4pIbxfYYAYBuLhCxNapWMJye2OwQrY",
        "type": "single",
        "start_equity": DEFAULT_START_EQUITY,
    },
{
        "name": "Structure Quality Runner",
        "spreadsheet_id": "1XNARri_KElpXnybGz-lpPP2tDKFHRjD_0B2T_qTIyUk",
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
    """Load one Google spreadsheet with very few Sheets API read requests.

    The earlier version called worksheet.get_all_records() once per tab. With
    five bot spreadsheets plus trade tabs, Streamlit refreshes could hit the
    Google Sheets per-minute quota. This version gets the worksheet list once,
    then reads all tab values in one batch request per spreadsheet.
    """
    client = gspread.authorize(get_credentials())
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheets = spreadsheet.worksheets()
    snapshots = {}
    trades = {}

    if not worksheets:
        return snapshots, trades

    ranges = [f"'{ws.title.replace(chr(39), chr(39)+chr(39))}'!A:AZ" for ws in worksheets]
    try:
        batch = spreadsheet.values_batch_get(ranges=ranges)
        value_ranges = batch.get("valueRanges", [])
    except Exception:
        # Fallback keeps the app usable if the gspread version lacks batch_get,
        # but the normal path above is what avoids 429 quota errors.
        value_ranges = []
        for ws in worksheets:
            value_ranges.append({"values": ws.get_all_values()})

    for ws, vr in zip(worksheets, value_ranges):
        values = vr.get("values", [])
        if not values or len(values) < 2:
            continue
        headers = [str(h).strip() for h in values[0]]
        rows = []
        for raw in values[1:]:
            padded = list(raw) + [""] * max(0, len(headers) - len(raw))
            row = dict(zip(headers, padded[:len(headers)]))
            if any(str(v).strip() for v in row.values()):
                rows.append(row)
        if not rows:
            continue

        df = clean_dataframe(rows)
        if df.empty:
            continue

        title = ws.title.strip()
        title_lower = title.lower()
        if "trade" in title_lower:
            clean_title = title.replace("(Legacy)", "").replace("Trades", "").replace("trades", "").strip()
            trades[clean_title] = df
            continue

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


def _normalised_id_list(bot_id=None, bot_ids=None):
    values = []
    if bot_ids:
        values.extend(bot_ids)
    elif bot_id:
        values.append(bot_id)
    return [norm(v) for v in values if str(v).strip()]


def filter_trade_rows(trades, bot_id=None, bot_ids=None, trade_date=None):
    df = all_trade_rows(trades)
    if df.empty:
        return df

    wanted_ids = _normalised_id_list(bot_id=bot_id, bot_ids=bot_ids)
    if wanted_ids and "bot_id" in df.columns:
        df = df[df["bot_id"].astype(str).map(norm).isin(wanted_ids)].copy()

    if df.empty:
        return df
    if "timestamp" in df.columns:
        et_times = df["timestamp"].dt.tz_convert("America/New_York")
        df["trade_day_et"] = et_times.dt.date
        df["time_et"] = et_times.dt.strftime("%H:%M")
        if trade_date is None:
            trade_date = current_session_date_et()
        df = df[df["trade_day_et"] == trade_date].copy()
    return df


def trade_pnl_and_rows(trades, bot_id=None, bot_ids=None, trade_date=None):
    df = filter_trade_rows(trades, bot_id=bot_id, bot_ids=bot_ids, trade_date=trade_date)
    if df.empty or "pnl" not in df.columns:
        return 0.0, df
    return float(df["pnl"].sum()), df


def logged_trade_totaliser(trades, bot_id=None):
    """Sum logged trade P/L without applying the daily/session date filter."""
    df = all_trade_rows(trades)
    if df.empty:
        return 0.0, df
    if bot_id and "bot_id" in df.columns:
        wanted = norm(bot_id)
        df = df[df["bot_id"].astype(str).map(norm) == wanted].copy()
    if df.empty or "pnl" not in df.columns:
        return 0.0, df
    if "timestamp" in df.columns:
        try:
            et_times = df["timestamp"].dt.tz_convert("America/New_York")
            df["trade_day_et"] = et_times.dt.date
            df["time_et"] = et_times.dt.strftime("%H:%M")
        except Exception:
            pass
    return float(df["pnl"].sum()), df


def trade_count_for_rows(df):
    return 0 if df is None or df.empty else len(df)


def trade_table_html(df):
    if df is None or df.empty:
        return "<div class='tiny'>No trades logged for this trading day.</div>"

    cards = []
    for _, r in df.iterrows():
        pnl = pd.to_numeric(pd.Series([r.get("pnl", 0)]), errors="coerce").fillna(0).iloc[0]
        cls = pnl_class(float(pnl))
        symbol = str(r.get("symbol", "") or r.get("ticker", "") or "Trade").upper()
        side = str(r.get("side", "") or "").upper()
        qty = r.get("qty", "")
        try:
            qty_txt = f"{float(qty):,.0f}"
        except Exception:
            qty_txt = str(qty or "")
        reason = str(r.get("exit_reason", "") or r.get("status", "") or "").strip()
        time_txt = str(r.get("time_et", "") or "")
        pct = r.get("pnl_pct", "")
        try:
            pct_txt = f" ({float(pct):+.2f}%)" if str(pct).strip() != "" else ""
        except Exception:
            pct_txt = ""
        sub_bits = []
        if time_txt:
            sub_bits.append(time_txt)
        if side:
            sub_bits.append(side)
        if qty_txt:
            sub_bits.append(f"Qty {qty_txt}")
        if reason:
            sub_bits.append(reason)
        sub = " | ".join(sub_bits)
        cards.append(
            f"<div class='trade-card trade-card-{cls}'>"
            f"<div class='trade-card-top'><span>{symbol}</span><span>${float(pnl):+,.2f}{pct_txt}</span></div>"
            f"<div class='trade-card-sub'>{sub}</div>"
            f"</div>"
        )
    return "".join(cards)


def render_trade_details(row, key_prefix=""):
    trades_df = row.get("trade_rows")
    trade_pnl = float(row.get("trade_pnl", 0) or 0)
    trade_day = row.get("trade_day", "")

    if (trades_df is None or trades_df.empty) and row.get("totaliser_trade_rows") is not None:
        trades_df = row.get("totaliser_trade_rows")
        trade_pnl = float(row.get("totaliser_pnl", 0) or 0)
        trade_day = "logged total"

    if trades_df is None or trades_df.empty:
        st.markdown("<div class='tiny'>No trades logged for this bot today/session.</div>", unsafe_allow_html=True)
        return

    st.markdown(
        f"<div class='tiny'><b>Trades {trade_day}</b> | Total realised P/L {trade_pnl:+,.2f}</div>" + trade_table_html(trades_df),
        unsafe_allow_html=True,
    )

    # Parent bot child trade breakdown. Do not use nested Streamlit expanders here;
    # this function already runs inside the bot's trade dropdown.
    child_ids = row.get("trade_child_ids") or []
    if child_ids and "bot_id" in trades_df.columns:
        for child_id in child_ids:
            child_df = trades_df[trades_df["bot_id"].astype(str).map(norm) == norm(child_id)].copy()
            if child_df.empty:
                continue
            child_pnl = float(child_df["pnl"].sum()) if "pnl" in child_df.columns else 0.0
            st.markdown(
                f"<div class='tiny' style='margin-top:12px;'><b>{child_id} child trades</b> | {len(child_df)} trades | P/L {child_pnl:+,.2f}</div>" + trade_table_html(child_df),
                unsafe_allow_html=True,
            )


def newest_time_from_df(df):
    if df is None or df.empty or "timestamp" not in df.columns:
        return pd.Timestamp.min
    values = df["timestamp"].dropna()
    if values.empty:
        return pd.Timestamp.min
    return values.iloc[-1]


def newest_match(matches):
    """Return the matching snapshot with the newest timestamp.

    This matters for portfolio sheets where several tabs/rows can match the
    display name or engine IDs. The heartbeat must follow the newest Google
    Sheets write, not the first matching tab returned by the API.
    """
    if not matches:
        return None, pd.DataFrame()
    return max(matches, key=lambda item: newest_time_from_df(item[1]))


def best_snapshot_for_name(snapshots, wanted_name, allow_fallback=True):
    if not snapshots:
        return None, pd.DataFrame()

    wanted = norm(wanted_name)

    # 1) Exact worksheet title matches. If more than one matches, use newest.
    matches = [(title, df) for title, df in snapshots.items() if norm(title) == wanted]
    if matches:
        return newest_match(matches)

    # 2) Latest row identity match from bot_name/account_name/bot_id.
    matches = [(title, df) for title, df in snapshots.items() if identity_matches(row_identity_text(df), wanted_name)]
    if matches:
        return newest_match(matches)

    # 3) Partial worksheet title match. Again, use newest matching tab.
    matches = [(title, df) for title, df in snapshots.items() if wanted in norm(title) or norm(title) in wanted]
    if matches:
        return newest_match(matches)

    # 4) Fallback to newest tab only for single-account sheets. For grouped child
    # rows, fallback is disabled so the same newest tab is not reused incorrectly.
    if not allow_fallback:
        return None, pd.DataFrame()

    return newest_match(list(snapshots.items()))


def best_snapshot_by_hints(snapshots, source_hints, allow_fallback=True):
    """Find the newest snapshot tab/row using explicit source hints.

    This is used for similarly named bots and portfolio accounts. The previous
    version returned the first matching tab, which can make the heartbeat look
    offline while a newer engine/portfolio row is still writing to Sheets.
    """
    hints = [norm(h) for h in (source_hints or []) if str(h).strip()]
    if not hints:
        return None, pd.DataFrame()

    matches = []

    # Prefer latest row identity text first because tab names can be generic.
    for title, df in snapshots.items():
        identity = norm(row_identity_text(df))
        title_norm = norm(title)
        if any(h in identity or h in title_norm for h in hints):
            matches.append((title, df))

    if matches:
        return newest_match(matches)

    if not allow_fallback:
        return None, pd.DataFrame()

    return newest_match(list(snapshots.items()))


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


def heartbeat_status(value):
    """Return timed heartbeat status from latest Google Sheets timestamp.

    Fusion Portfolio writes to Sheets about every 20-30 seconds while running.
    The card stays live while the latest timestamp is under 3 minutes old.
    If the bot stops writing, it turns offline after roughly 3 minutes, plus
    the Streamlit cache refresh delay.
    """
    if pd.isna(value) or str(value).strip() == "":
        return "<span class='heartbeat-offline'>💔 OFFLINE</span>"

    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return "<span class='heartbeat-offline'>💔 BAD HEARTBEAT</span>"

        if getattr(ts, "tzinfo", None) is None:
            ts = ts.tz_localize(ET)
        else:
            ts = ts.tz_convert(ET)

        age_minutes = (datetime.now(ET) - ts).total_seconds() / 60

        if age_minutes <= 3:
            return "<span class='heartbeat-live'>💚 LIVE</span>"

        return f"<span class='heartbeat-offline'>💔 OFFLINE {age_minutes:.0f}m</span>"

    except Exception:
        return "<span class='heartbeat-offline'>💔 OFFLINE</span>"






ET = ZoneInfo("America/New_York")
SESSION_RESET_HOUR_ET = 4
BASELINE_VERSION = "premarket_v2_strict_fusion15_apex_total"


def current_session_date_et():
    """Trading day used for the sleep-check daily P/L.

    The reset happens at the start of the following premarket session.
    Before 04:00 ET, the app still treats the rows as the prior session;
    from 04:00 ET onward it starts a new daily baseline.
    """
    now = datetime.now(ET)
    if now.hour < SESSION_RESET_HOUR_ET:
        return (now - timedelta(days=1)).date()
    return now.date()


def current_session_key():
    return current_session_date_et().isoformat()


BASELINE_FILE = os.path.join(tempfile.gettempdir(), "sleep_check_daily_premarket_baselines_v2.json")


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
    return {"created_at": datetime.now().isoformat(), "session_key": current_session_key(), "baselines": {}}


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
    session_key = current_session_key()
    if data.get("session_key") != session_key or data.get("version") != BASELINE_VERSION:
        data = {
            "created_at": datetime.now().isoformat(),
            "session_key": session_key,
            "version": BASELINE_VERSION,
            "reset_rule": f"Resets at {SESSION_RESET_HOUR_ET:02d}:00 ET premarket",
            "baselines": {},
        }
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



def snapshot_card_pnl(latest, fallback_pnl):
    try:
        for key in ("daily_pl_alpaca", "alpaca_daily_pl", "daily_pnl", "daily_pl"):
            if key in latest and str(latest.get(key, "")).strip() not in ("", "nan", "None", "-"):
                return float(str(latest.get(key)).replace("$", "").replace(",", ""))
    except Exception:
        pass

    try:
        equity_val = latest.get("alpaca_equity", latest.get("equity", None))
        last_eq_val = latest.get("alpaca_last_equity", latest.get("last_equity", None))
        if equity_val is not None and last_eq_val is not None:
            equity_f = float(str(equity_val).replace("$", "").replace(",", ""))
            last_f = float(str(last_eq_val).replace("$", "").replace(",", ""))
            return equity_f - last_f
    except Exception:
        pass

    return fallback_pnl


def row_from_snapshot(display_name, tab_name, df, trades, detail_only=False, start_equity=DEFAULT_START_EQUITY, bot_id=None, allocation=None, trade_child_ids=None, card_pnl_source='trades_if_present'):
    equity, pnl, pct = calc_delta(df)
    previous_equity = equity - pnl
    latest = df.iloc[-1]
    actual_bot_id = bot_id or str(latest.get("bot_id", "") or "")
    actual_bot_id = "" if str(actual_bot_id).strip().lower() in ("", "nan", "none") else str(actual_bot_id).strip()

    # Trade matching rule:
    # - Apex 50K child rows pass bot_id explicitly, so filter by that exact bot_id.
    # - Fusion parent rows can have child engines that log their own bot_id. For those,
    #   count parent + child ids into the parent card and show child sections below.
    # - Other single-bot Fusion sheets with no explicit bot_id still use all trades from
    #   their own spreadsheet because older trade tabs sometimes had no stable bot_id.
    trade_child_ids = list(trade_child_ids or [])
    trade_filter_bot_ids = None
    if bot_id and trade_child_ids:
        trade_filter_bot_ids = [bot_id] + trade_child_ids
    elif bot_id:
        trade_filter_bot_ids = [bot_id]

    trade_pnl, trade_rows = trade_pnl_and_rows(trades, bot_ids=trade_filter_bot_ids)
    trade_day = ""
    if trade_rows is not None and not trade_rows.empty and "trade_day_et" in trade_rows.columns:
        trade_day = str(trade_rows["trade_day_et"].max())

    # Default behaviour is unchanged from v3.
    card_snapshot_pnl = snapshot_card_pnl(latest, pnl)
    if str(card_pnl_source).lower() == "snapshot":
        card_pnl = card_snapshot_pnl
    else:
        card_pnl = trade_pnl if trade_count_for_rows(trade_rows) > 0 else card_snapshot_pnl

    card_pct = 0.0 if previous_equity == 0 else (card_pnl / previous_equity) * 100

    return {
        "bot_name": display_name,
        "tab_name": tab_name,
        "equity": equity,
        "previous_equity": previous_equity,
        "pnl": card_pnl,
        "snapshot_pnl": card_snapshot_pnl,
        "pct": card_pct,
        "buying_power": float(latest.get("buying_power", 0) or 0),
        "positions": safe_int(latest.get("open_positions", 0)),
        "orders": safe_int(latest.get("open_orders", 0)),
        "last_update": latest.get("timestamp", ""),
        "trades": trade_count_for_rows(trade_rows),
        "trade_pnl": trade_pnl,
        "trade_rows": trade_rows,
        "trade_day": trade_day,
        "trade_child_ids": trade_child_ids,
        "detail_only": detail_only,
        "start_equity": float(start_equity or DEFAULT_START_EQUITY),
        "bot_id": actual_bot_id,
        "allocation": allocation or "",
    }


def make_single_row(config, snapshots, trades):
    # Prefer an exact bot_id match when supplied. This avoids name/tab clashes
    # between Fusion Portfolio and Fusion 15 when both use similar worksheet names.
    if config.get("bot_id"):
        tab_name, df = filter_snapshot_by_bot_id(snapshots, config["bot_id"])
    elif config.get("source_hints"):
        tab_name, df = best_snapshot_by_hints(
            snapshots,
            config.get("source_hints"),
            allow_fallback=not bool(config.get("strict_source_hints")),
        )
    else:
        tab_name, df = best_snapshot_for_name(snapshots, config["name"])

    if df is None or df.empty:
        return None

    return row_from_snapshot(
        config["name"],
        tab_name,
        df,
        trades,
        start_equity=config.get("start_equity", DEFAULT_START_EQUITY),
        bot_id=config.get("bot_id"),
        trade_child_ids=config.get("trade_child_ids"),
        card_pnl_source=config.get("card_pnl_source", "trades_if_present"),
    )


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
            child_row = row_from_snapshot(
                child_name,
                tab_name,
                df,
                trades,
                detail_only=True,
                start_equity=child.get("start_equity", DEFAULT_START_EQUITY),
                bot_id=child_bot_id,
                allocation=child.get("allocation", ""),
            )
            totaliser_pnl, totaliser_rows = logged_trade_totaliser(trades, bot_id=child_bot_id)
            child_row["totaliser_pnl"] = totaliser_pnl
            child_row["totaliser_trades"] = trade_count_for_rows(totaliser_rows)
            child_row["totaliser_trade_rows"] = totaliser_rows
            children.append(child_row)

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


def is_waiting_for_trading_day():
    """Before premarket begins, keep cards visually grey."""
    return datetime.now(ET).hour < 4


def display_card_class(row, child=False):
    if is_waiting_for_trading_day():
        return "flat"
    return pnl_class(float(row.get("leaderboard_pnl", row.get("pnl", 0)) or 0))


def rank_badge(rank):
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    return f"#{rank}"


def render_row(row, child=False, rank=None):
    daily_pnl = float(row.get("pnl", 0) or 0)
    daily_pct = float(row.get("pct", 0) or 0)

    # Card background is daily/live status. Flat daily = grey.
    cls = pnl_class(daily_pnl)
    child_class = " child-row" if child else ""
    name_class = "bot-name child-name" if child else "bot-name"
    equity_label = "Bot Equity" if child else "Equity"
    source_label = "Apex bot source" if child else "Source"
    allocation_text = f"<span>Allocation {row.get('allocation')}</span>" if child and row.get("allocation") else ""
    bot_id_text = f" | bot_id: {row.get('bot_id')}" if child and row.get("bot_id") else ""
    badge_html = f'<span class="rank-badge">{rank_badge(rank)}</span>' if rank else ""

    # Main cards: permanent total equity change from original starting balance.
    if child:
        overall_html = ""
    else:
        overall_start = float(row.get("start_equity", DEFAULT_START_EQUITY) or DEFAULT_START_EQUITY)
        overall_pnl = float(row.get("equity", 0) or 0) - overall_start
        overall_pct = 0.0 if overall_start == 0 else (overall_pnl / overall_start) * 100
        overall_cls = pnl_class(overall_pnl)
        overall_html = (
            f"<div class='since-line since-{overall_cls}'>"
            f"Overall from {money(overall_start)}: {overall_pnl:+,.0f} ({overall_pct:+.2f}%)"
            f"</div>"
        )

    # Apex child cards: realised logged-trade totaliser from the trade tabs.
    totaliser_html = ""
    trades_display = row.get("trades", 0)
    if child and int(row.get("totaliser_trades", 0) or 0) > 0:
        totaliser_pnl = float(row.get("totaliser_pnl", 0) or 0)
        totaliser_cls = pnl_class(totaliser_pnl)
        totaliser_html = (
            f"<div class='since-line since-{totaliser_cls}'>"
            f"Realised total P/L: {totaliser_pnl:+,.0f} from {int(row.get('totaliser_trades', 0))} trades"
            f"</div>"
        )
        trades_display = int(row.get("totaliser_trades", 0) or 0)

    card_html = (
        f'<div class="bot-row bot-row-{cls}{child_class}">'
        f'<div class="bot-topline">'
        f'<div class="{name_class}">{badge_html}{row["bot_name"]}</div>'
        f'<div class="bot-pnl-{cls}">Today {daily_pnl:+,.0f}</div>'
        f'</div>'
        f'<div class="bot-subline"><span>{equity_label} {money(row["equity"])}</span><span>Daily {daily_pnl:+,.0f} ({daily_pct:+.2f}%)</span>{allocation_text}</div>'
        f'{overall_html}'
        f'{totaliser_html}'
        f'<div class="bot-subline"><span>Pos {row["positions"]}</span><span>Orders {row["orders"]}</span><span>Trades {trades_display}</span></div>'
        f'<div class="tiny">{heartbeat_status(row["last_update"])} | Last: {fmt_time(row["last_update"])} | {source_label}: {row["tab_name"]}{bot_id_text}</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)



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
    f'''<div class="summary-card"><div class="summary-label">Total Fleet Equity</div><div class="summary-value">{money(total_equity)}</div><div class="summary-pnl-{cls}">Today P/L {total_pnl:+,.0f}</div><div class="since-line since-{since_cls}">Session reset {SESSION_RESET_HOUR_ET:02d}:00 ET | Session {current_session_key()}</div></div>''',
    unsafe_allow_html=True,
)

s1, s2 = st.columns(2)
with s1:
    st.markdown(f'''<div class="summary-card"><div class="summary-label">Buying Power</div><div class="summary-value" style="font-size:1.35rem;">{money(total_bp)}</div></div>''', unsafe_allow_html=True)
with s2:
    st.markdown(f'''<div class="summary-card"><div class="summary-label">Open Risk</div><div class="summary-value" style="font-size:1.35rem;">{total_positions} pos / {total_orders} ord</div></div>''', unsafe_allow_html=True)

st.markdown('<div class="section-title">Bots — daily status, overall score shown</div>', unsafe_allow_html=True)

# Cards show daily status; permanent overall score is shown under equity.
fleet_rows = sorted(fleet_rows, key=lambda r: (float(r.get("leaderboard_pnl", 0) or 0), float(r.get("equity", 0) or 0)), reverse=True)

for rank, row in enumerate(fleet_rows, start=1):
    render_row(row, rank=rank)
    children = group_children.get(row["bot_name"], [])
    # Phone-friendly: no checkboxes. Tap the expander bar directly under each card
    # to reveal that bot's trades underneath the card. It is shown even when the
    # count is zero so you can confirm there were no matching trades.
    with st.expander(f"👆 Tap to show trades for {row['bot_name']} ({row['trades']})", expanded=False):
        render_trade_details(row, key_prefix=f"main-{rank}")

    if children:
        children = sorted(children, key=lambda r: (float(r.get("leaderboard_pnl", 0) or 0), float(r.get("equity", 0) or 0)), reverse=True)
        with st.expander("Show Apex 50K bot equity tracking", expanded=True):
            st.caption("Apex child cards stay grey while waiting for the trading day. Their realised total P/L remains red/green and is not added into Total Fleet Equity.")
            apex_child_total_pnl = sum(float(c.get("totaliser_pnl", 0) or 0) for c in children)
            apex_child_total_trades = sum(int(c.get("totaliser_trades", 0) or 0) for c in children)
            apex_child_total_cls = pnl_class(apex_child_total_pnl)
            st.markdown(
                f"<div class='summary-card' style='padding:10px 12px; margin-bottom:10px;'><div class='summary-label'>Apex realised total P/L</div><div class='summary-pnl-{apex_child_total_cls}'>{apex_child_total_pnl:+,.0f}</div><div class='tiny'>From {apex_child_total_trades} logged trades. Daily P/L resets separately.</div></div>",
                unsafe_allow_html=True,
            )
            for child_rank, child in enumerate(children, start=1):
                render_row(child, child=True, rank=child_rank)
                with st.expander(f"👆 Tap to show trades for {child['bot_name']} ({child.get('totaliser_trades', child['trades'])})", expanded=False):
                    render_trade_details(child, key_prefix=f"child-{child_rank}")

if load_errors:
    with st.expander("Load warnings", expanded=False):
        for err in load_errors:
            st.warning(err)

st.caption("Fleet sleep-check layout. Refreshes every 30 seconds. Right-side Today P/L resets each premarket. The Overall line under equity is permanent from the original account start balance. Tap the trade bar under any bot card to see logged trades.")

# ============================================================
# CARD P/L SAFETY PATCH
# ============================================================
# Parent cards must NOT derive daily P/L from child clean-trade rows.
# Child trades are for dropdown counts/details only.
#
# Preferred card-level daily P/L source:
#   1) Alpaca account snapshot: equity - last_equity
#   2) Parent heartbeat/snapshot daily value
#   3) Existing fallback
#
# This prevents cases like Fusion 15 showing -8390 from child trade history
# while Alpaca account is actually up +1168 on the day.

def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        s = str(value).replace("$", "").replace(",", "").replace("%", "").strip()
        if s in ("", "nan", "None", "-"):
            return default
        return float(s)
    except Exception:
        return default


def calc_card_daily_from_alpaca_like_snapshot(snapshot_row, existing_daily=None):
    """
    Use this for the main card daily P/L.

    snapshot_row may be a dict/Series containing:
      - equity
      - last_equity / previous_equity / prev_equity / yesterday_equity

    Returns existing_daily if no previous equity reference exists.
    """
    if snapshot_row is None:
        return existing_daily

    def get_any(row, keys):
        for k in keys:
            try:
                if hasattr(row, "get"):
                    v = row.get(k, None)
                else:
                    v = row[k]
                if v not in (None, "", "-"):
                    return v
            except Exception:
                pass
        return None

    equity = get_any(snapshot_row, ["equity", "Equity", "account_equity", "Account Equity"])
    last_equity = get_any(snapshot_row, [
        "last_equity",
        "Last Equity",
        "previous_equity",
        "Previous Equity",
        "prev_equity",
        "Prev Equity",
        "yesterday_equity",
        "Yesterday Equity",
    ])

    if equity is not None and last_equity is not None:
        return round(_safe_float(equity) - _safe_float(last_equity), 2)

    return existing_daily


def get_trade_rollup_ids_for_dropdown(parent_bot_id):
    """
    Child trades are included for dropdown/detail only.
    They should not override parent card equity/daily P/L.
    """
    try:
        return [parent_bot_id] + BOT_TRADE_CHILDREN.get(parent_bot_id, [])
    except Exception:
        return [parent_bot_id]
