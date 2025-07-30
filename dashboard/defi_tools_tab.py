import streamlit as st

def defi_tools_widget():
    st.header("🦾 DeFi Auto Sniping & Scalping")
    if st.session_state.toggles.get("auto_sniping"):
        st.success("Auto Sniping is ENABLED.")
    else:
        st.info("Auto Sniping is DISABLED.")
    if st.session_state.toggles.get("auto_scalping"):
        st.success("Auto Scalping is ENABLED.")
    else:
        st.info("Auto Scalping is DISABLED.")