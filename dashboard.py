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
            max-width: 1600px;
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
            color: #9fb0bd !important;
            font-size: 0.9rem;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(255,255,255,0.095), rgba(255,255,255,0.035));
            border: 1px solid rgba(255,255,255,0.16);
            padding: 13px;
            border-radius: 18px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.28);
        }

        div[data-testid="stMetricLabel"] p {
            color: #b8c7d3 !important;
            font-size: 0.78rem !important;
            font-weight: 800 !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.65rem !important;
            font-weight: 900 !important;
            color: white !important;
        }

        div[data-testid="stMetricDelta"] {
            font-size: 0.78rem !important;
            font-weight: 800 !important;
        }

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

        .mini-box {
            padding: 9px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.045);
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

        .last-seen {
            color: #90a4ae;
            font-size: 0.68rem;
            margin-top: 8px;
            line-height: 1.1rem;
        }

        .divider-soft {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
            margin: 14px 0;
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

            div[data-testid="stMetric"] {
                padding: 10px;
                border-radius: 15px;
            }

            div[data-testid="stMetricValue"] {
                font-size: 1.35rem !important;
            }

            .bot-header {
                font-size: 0.78rem;
                min-height: 42px;
                padding: 10px 11px;
            }

            .bot-body {
                padding: 10px;
            }

            .mini-box {
                min-height: 56px;
                padding: 8px;
            }

            .mini-value {
                font-size: 0.95rem;
            }

            .status-pill {
                font-size: 0.64rem;
                padding: 4px 7px;
            }
        }
    </style>
    ''',
    unsafe_allow_html=True,
)

st.title("Alpaca Bot Dashboard")
st.caption("Live Google Sheets feed from your Alpaca trading bots")


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
            "equity", "buying_power", "open_positions", "open_orders",
            "qty", "buy_price", "sell_price", "pnl", "pnl_pct",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        title = worksheet.title
        if title.endswith(" Trades"):
            trade_tabs[title.replace(" Trades", "")] = df
        else:
            snapshot_tabs[title] = df

    return snapshot_tabs, trade_tabs


def calc_delta(df: pd.DataFrame, value_col: str = "equity"):
    if df.empty or value_col not in df.columns:
        return 0.0, 0.0, 0.0, 0.0

    latest_value = float(df.iloc[-1].get(value_col, 0) or 0)
    previous_value = float(df.iloc[-2].get(value_col, latest_value) or latest_value) if len(df) > 1 else latest_value
    delta = latest_value - previous_value
    delta_pct = 0.0 if previous_value == 0 else (delta / previous_value) * 100
    return latest_value, previous_value, delta, delta_pct


def trend_style(delta: float):
    if delta > 0:
        return "header-positive", "🟢 UP", "normal"
    if delta < 0:
        return "header-negative", "🔴 DOWN", "inverse"
    return "header-flat", "⚪ FLAT", "off"


def money(value):
    return f"${float(value or 0):,.0f}"


def fmt_price(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def render_bot_card(bot_name, df, trades_by_tab):
    latest = df.iloc[-1]
    equity, _, delta, delta_pct = calc_delta(df)
    header_class, status_text, delta_color = trend_style(delta)

    buying_power = float(latest.get("buying_power", 0) or 0)
    open_positions = int(latest.get("open_positions", 0) or 0)
    open_orders = int(latest.get("open_orders", 0) or 0)

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
        f"${equity:,.0f}",
        f"{delta:+,.0f} ({delta_pct:+.2f}%)",
        delta_color=delta_color,
    )

    if "equity" in df.columns and "timestamp" in df.columns:
        chart_df = df.set_index("timestamp")[["equity"]].apply(pd.to_numeric, errors="coerce")
        st.line_chart(chart_df, height=125)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">BP</div>
                <div class="mini-value">{money(buying_power)}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">Pos</div>
                <div class="mini-value">{open_positions}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f'''
            <div class="mini-box">
                <div class="mini-label">Orders</div>
                <div class="mini-value">{open_orders}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    if "timestamp" in df.columns:
        last_seen = latest.get("timestamp")
        st.markdown(
            f'<div class="last-seen">Last update: {last_seen}</div>',
            unsafe_allow_html=True,
        )

    trade_df = trades_by_tab.get(bot_name)

    with st.expander("Recent trades", expanded=False):
        if trade_df is None or trade_df.empty:
            st.caption("No completed trades logged yet.")
        else:
            trade_show = trade_df.tail(8).sort_values("timestamp", ascending=False)

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
                            <div style="
                                font-weight:800;
                                font-size:15px;
                                color:white;
                            ">
                                {symbol} • {side}
                            </div>
                            <div style="
                                color:{trade_color};
                                font-weight:900;
                                font-size:15px;
                            ">
                                ${pnl:+,.2f}
                            </div>
                        </div>
                        <div style="
                            color:#cfd8dc;
                            font-size:12px;
                            margin-bottom:4px;
                        ">
                            Qty {qty} | Buy ${buy_price} → Sell ${sell_price}
                        </div>
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                        ">
                            <div style="
                                color:{trade_color};
                                font-size:12px;
                                font-weight:700;
                            ">
                                {pnl_pct:+.2f}%
                            </div>
                            <div style="
                                color:#90a4ae;
                                font-size:11px;
                            ">
                                {status}
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

    st.markdown("</div></div>", unsafe_allow_html=True)


try:
    data_by_tab, trades_by_tab = load_sheet_data()
except Exception as e:
    st.error(f"Could not load Google Sheet: {e}")
    st.stop()

if not data_by_tab:
    st.warning("No bot rows found yet.")
    st.stop()


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
    total_buying_power = pd.to_numeric(latest_df.get("buying_power", 0), errors="coerce").sum()
    total_positions = pd.to_numeric(latest_df.get("open_positions", 0), errors="coerce").fillna(0).sum()
    total_orders = pd.to_numeric(latest_df.get("open_orders", 0), errors="coerce").fillna(0).sum()

    total_delta = 0.0
    total_previous = 0.0
    for _, df in data_by_tab.items():
        _, previous_equity, delta, _ = calc_delta(df)
        total_delta += delta
        total_previous += previous_equity

    total_delta_pct = 0 if total_previous == 0 else (total_delta / total_previous) * 100

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Equity", f"${total_equity:,.0f}", f"{total_delta:+,.0f} ({total_delta_pct:+.2f}%)")
    s2.metric("Buying Power", f"${total_buying_power:,.0f}")
    s3.metric("Positions", int(total_positions))
    s4.metric("Orders", int(total_orders))

st.markdown('<div class="divider-soft"></div>', unsafe_allow_html=True)


bot_names = sorted(data_by_tab.keys())

# Desktop/tablet: Streamlit columns naturally show 3-across on wide screens and collapse on phones.
for row_start in range(0, len(bot_names), 3):
    cols = st.columns(3)

    for col, bot_name in zip(cols, bot_names[row_start:row_start + 3]):
        df = data_by_tab[bot_name]

        if df.empty:
            continue

        with col:
            render_bot_card(bot_name, df, trades_by_tab)

st.caption("Responsive layout. Dashboard refreshes every 30 seconds.")
