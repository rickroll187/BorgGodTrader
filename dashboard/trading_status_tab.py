import streamlit as st

def trading_status_widget(trading_logs):
    st.header("📈 Trading Status & Logs")
    if trading_logs:
        for log in trading_logs[-20:][::-1]:
            if log.get("type") == "error":
                st.error(f"[{log['time']}] {log['message']}")
            elif log.get("type") == "success":
                st.success(f"[{log['time']}] {log['message']}")
            elif log.get("type") == "info":
                st.info(f"[{log['time']}] {log['message']}")
            else:
                st.write(f"[{log['time']}] {log['message']}")
    else:
        st.info("No trading activity yet.")