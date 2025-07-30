import streamlit as st
from dashboard.feature_toggles import feature_toggles
from dashboard.trading_status_tab import trading_status_widget
from dashboard.defi_tools_tab import defi_tools_widget
from core.auto_trading import AutoTrader

# --- Borg Color Theme and Branding ---
st.markdown("""
    <style>
    body, .stApp {
        background-color: #101612 !important;
        color: #39ff14 !important;
    }
    .st-bh, .st-cg, .st-cf, .st-cd, .st-ce, .st-c6, .st-c7, .st-c8, .st-c9, .st-ca, .st-cb, .st-cc, .st-ci, .st-cj, .st-cl, .st-cm, .st-cn, .st-co, .st-cp, .st-cq, .st-cr, .st-cs, .st-ct, .st-cu, .st-cv, .st-cw, .st-cx, .st-cy, .st-cz, .st-da, .st-db, .st-dc, .st-dd, .st-de, .st-df, .st-dg, .st-dh, .st-di, .st-dj, .st-dk, .st-dl, .st-dm, .st-dn, .st-do, .st-dp, .st-dq, .st-dr, .st-ds, .st-dt, .st-du, .st-dv, .st-dw, .st-dx, .st-dy, .st-dz {
        color: #39ff14 !important;
        background-color: #101612 !important;
    }
    .sidebar .sidebar-content {
        background-color: #151b16 !important;
    }
    .stButton>button {
        color: #101612 !important;
        background-color: #39ff14 !important;
        border-radius: 8px;
        border: none;
    }
    .st-bx {
        background-color: #232b24 !important;
    }
    .st-cz, .st-da, .st-db {
        color: #39ff14 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Margin Trading Bot Dashboard", layout="wide", page_icon="🤖")
st.title("🤖 Margin Trading Bot Dashboard")
st.markdown(
    '<div style="font-size: 18px; color: #39ff14;">Assimilate. Adapt. Advance.<br>'
    '<b>Created by Chemothearpy/Eviscerate</b></div>',
    unsafe_allow_html=True)
st.caption("Forever assimilating. Always improving.")

ISO_COMPLIANT_COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT", "XLMUSDT",
    "HBARUSDT", "ALGOUSDT", "QNTUSDT", "MIOTAUSDT", "TRXUSDT", "XDCUSDT"
]
EXTRA_SYMBOLS = [
    "DOGEUSDT", "SHIBUSDT", "AVAXUSDT", "MATICUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
    "ATOMUSDT", "ARBUSDT", "OPUSDT", "FDUSDUSDT", "WIFUSDT", "PEPEUSDT"
]
ALL_SYMBOLS = sorted(list(set(ISO_COMPLIANT_COINS + EXTRA_SYMBOLS)))

feature_toggles()

st.sidebar.subheader("Symbol Selection")
if "selected_symbols" not in st.session_state:
    st.session_state.selected_symbols = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "XLMUSDT"]

selected_symbols = st.sidebar.multiselect(
    "Active Trading Symbols (auto-selects top ISO coins, can edit):",
    options=ALL_SYMBOLS,
    default=st.session_state.selected_symbols
)
st.session_state.selected_symbols = selected_symbols

if "trading_logs" not in st.session_state:
    st.session_state.trading_logs = []

# Dummy executors for demonstration—replace with real implementations
class DummySpotExecutor:
    def buy(self, symbol):
        if symbol == "BTCUSDT":
            raise Exception("API Error: Insufficient funds")
    def sell(self, symbol):
        if symbol == "SHIBUSDT":
            raise Exception("API Error: Sell not allowed")
class DummyMarginExecutor:
    def open_long(self, symbol, amount):
        if symbol == "ETHUSDT":
            raise Exception("API Error: Exchange maintenance")
    def open_short(self, symbol, amount):
        pass

spot_executor = DummySpotExecutor()
margin_executor = DummyMarginExecutor()

auto_trader = AutoTrader(
    spot_executor=spot_executor,
    margin_executor=margin_executor,
    symbols=st.session_state.selected_symbols,
    trading_logs=st.session_state.trading_logs
)

tabs = st.tabs([
    "Trade Margin",
    "Open Positions",
    "Event Log",
    "Auto Strategy Generator",
    "DeFi Tools",
    "Trading Status",
    "Feedback"
])

# Feedback tab (always visible)
with tabs[6]:
    st.header("Feedback & Ideas")
    feedback = st.text_area("What should BorgGod assimilate next?", "")
    if st.button("Submit Feedback"):
        try:
            with open("feedback.txt", "a") as f:
                f.write(feedback + "\n")
            st.success("Thank you! Your feedback will be assimilated.")
        except Exception as e:
            st.error(f"Could not save feedback: {e}")

# Trading Status Tab (always visible)
with tabs[5]:
    trading_status_widget(st.session_state.trading_logs)

# Event Log tab (always visible, with robust error handling)
with tabs[2]:
    try:
        from dashboard.margin_widgets import margin_event_log_widget
        from core.borggod_core import BorgGodCore
        if "core" not in st.session_state:
            st.session_state.core = BorgGodCore({})
        core = st.session_state.core
        liquidation_events = core.liquidation_events
        margin_event_log_widget()
        st.subheader("Recent Liquidation Actions")
        if liquidation_events:
            for e in liquidation_events[-10:]:
                st.warning(e)
        else:
            st.info("No recent liquidation events.")
    except Exception as e:
        st.error(f"Error in Event Log: {e}")

if st.session_state.toggles.get("auto_run", False):
    # Trade Margin tab
    with tabs[0]:
        try:
            from dashboard.margin_widgets import margin_trading_widget
            if st.session_state.toggles["margin_trading"]:
                if st.session_state.selected_symbols:
                    margin_manager = core.margin_manager
                    margin_trading_widget(margin_manager, st.session_state.selected_symbols)
                else:
                    st.warning("Please select at least one trading symbol.")
            else:
                st.info("Margin trading is currently disabled in toggles.")
        except Exception as e:
            st.error(f"Error in Trade Margin tab: {e}")

    # Open Positions tab
    with tabs[1]:
        try:
            from dashboard.margin_widgets import margin_positions_widget
            if st.session_state.toggles["margin_trading"]:
                margin_positions_widget(core.margin_manager)
            else:
                st.info("Margin trading is currently disabled in toggles.")
        except Exception as e:
            st.error(f"Error in Open Positions tab: {e}")

    # Auto Strategy tab
    with tabs[3]:
        try:
            from dashboard.auto_strategy_tab import auto_strategy_widget
            if st.session_state.toggles["auto_strategy"]:
                auto_strategy_widget(core.auto_strategy_gen)
            else:
                st.info("Auto strategy generation is currently disabled in toggles.")
        except Exception as e:
            st.error(f"Error in Auto Strategy tab: {e}")

    # DeFi Tools tab
    with tabs[4]:
        try:
            defi_tools_widget()
        except Exception as e:
            st.error(f"Error in DeFi Tools tab: {e}")

    # AUTO Spot and Margin trading (robust error handling, logs to status tab)
    try:
        if st.session_state.toggles.get("auto_trading", False):
            auto_trader.run_spot_trading()
    except Exception as e:
        auto_trader.log(f"Auto spot trading encountered a fatal error: {e}", "error")

    try:
        if st.session_state.toggles.get("margin_trading", False):
            auto_trader.run_margin_trading()
    except Exception as e:
        auto_trader.log(f"Auto margin trading encountered a fatal error: {e}", "error")

else:
    st.warning("Auto Run is turned OFF. Enable 'Auto Run Bot (Master Switch)' in the sidebar to activate the bot and all features.")

st.markdown("---")
st.caption('<span style="color:#39ff14;">© 2025 BorgGodTrader. Assimilate and thrive.</span>', unsafe_allow_html=True)