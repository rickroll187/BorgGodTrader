import streamlit as st
import pandas as pd
import plotly.graph_objs as go

def show_dashboard(trade_log, pnl_history, shap_values=None):
    st.title("Trading Analytics Dashboard")
    st.subheader("Live PnL")
    st.line_chart(pnl_history)
    st.subheader("Trade Log")
    st.dataframe(trade_log)
    if shap_values is not None:
        st.subheader("Explainable AI (SHAP)")
        st.bar_chart(shap_values)