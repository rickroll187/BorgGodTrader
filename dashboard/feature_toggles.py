import streamlit as st

def feature_toggles():
    st.sidebar.header("⚙️ Feature Toggles")
    if "toggles" not in st.session_state:
        st.session_state.toggles = {
            "auto_run": False,
            "auto_trading": False,
            "auto_strategy": False,
            "advanced_ml": True,
            "multi_chain": ["ethereum"],
            "margin_trading": True,
            "learning": False,
            "backtesting": False,
            "auto_sniping": False,
            "auto_scalping": False
        }

    st.session_state.toggles["auto_run"] = st.sidebar.checkbox(
        "Auto Run Bot (Master Switch)", value=st.session_state.toggles["auto_run"]
    )
    st.session_state.toggles["auto_trading"] = st.sidebar.checkbox(
        "Enable Auto Trading", value=st.session_state.toggles["auto_trading"]
    )
    st.session_state.toggles["auto_strategy"] = st.sidebar.checkbox(
        "Auto Strategy Generation", value=st.session_state.toggles["auto_strategy"]
    )
    st.session_state.toggles["advanced_ml"] = st.sidebar.checkbox(
        "Use Advanced ML", value=st.session_state.toggles["advanced_ml"]
    )
    chains = ["ethereum", "polygon", "arbitrum"]
    st.session_state.toggles["multi_chain"] = st.sidebar.multiselect(
        "Active Chains", chains, default=st.session_state.toggles["multi_chain"]
    )
    st.session_state.toggles["margin_trading"] = st.sidebar.checkbox(
        "Enable Margin Trading", value=st.session_state.toggles["margin_trading"]
    )
    st.session_state.toggles["learning"] = st.sidebar.checkbox(
        "Enable Continuous ML Learning", value=st.session_state.toggles["learning"]
    )
    st.session_state.toggles["backtesting"] = st.sidebar.checkbox(
        "Enable Backtesting", value=st.session_state.toggles["backtesting"]
    )
    st.session_state.toggles["auto_sniping"] = st.sidebar.checkbox(
        "Enable Auto Sniping (DeFi)", value=st.session_state.toggles["auto_sniping"]
    )
    st.session_state.toggles["auto_scalping"] = st.sidebar.checkbox(
        "Enable Auto Scalping (DeFi)", value=st.session_state.toggles["auto_scalping"]
    )