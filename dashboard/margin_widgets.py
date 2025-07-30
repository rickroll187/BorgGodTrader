import streamlit as st

def margin_trading_widget(margin_manager, symbols):
    st.header("📈 Margin Trading Control Panel")

    st.markdown("### Open Margin Position")
    with st.form("borrow_form"):
        symbol = st.selectbox("Asset Symbol", symbols, key="borrow_symbol")
        amount = st.number_input("Amount to Borrow", min_value=0.0001, step=0.0001, key="borrow_amount")
        rate = st.number_input("Interest Rate (Annual %)", min_value=0.0, step=0.01, key="borrow_rate")
        submit_borrow = st.form_submit_button("Borrow")
        if submit_borrow:
            try:
                tx = margin_manager.borrow(symbol, amount, rate/100 if rate else None)
                st.success(f"Borrowed {amount} {symbol} at {rate}% APR. TX: {tx}")
            except Exception as e:
                st.error(f"Borrow failed: {e}")

    st.markdown("---")
    st.markdown("### Repay Margin Debt")
    with st.form("repay_form"):
        symbol = st.selectbox("Asset Symbol", symbols, key="repay_symbol")
        amount = st.number_input("Amount to Repay", min_value=0.0001, step=0.0001, key="repay_amount")
        submit_repay = st.form_submit_button("Repay")
        if submit_repay:
            try:
                tx = margin_manager.repay(symbol, amount)
                st.success(f"Repaid {amount} {symbol}. TX: {tx}")
            except Exception as e:
                st.error(f"Repay failed: {e}")

    st.markdown("---")
    st.markdown("### Auto-Liquidate (Manual Trigger)")
    with st.form("autoliquidate_form"):
        symbol = st.selectbox("Asset Symbol", symbols, key="liquidate_symbol")
        submit_liq = st.form_submit_button("Auto-Liquidate")
        if submit_liq:
            try:
                tx = margin_manager.auto_liquidate(symbol)
                st.warning(f"Auto-liquidated {symbol}. TX: {tx}")
            except Exception as e:
                st.error(f"Auto-liquidation failed: {e}")

def margin_positions_widget(margin_manager):
    st.header("📊 Open Margin Positions")
    positions = margin_manager.get_all_positions()
    if positions:
        import pandas as pd
        df = pd.DataFrame.from_dict(positions, orient="index")
        st.dataframe(df)
    else:
        st.info("No open margin positions.")

def margin_event_log_widget(event_log_file='margin_events.jsonl'):
    st.header("📝 Margin Event Log")
    import os, json
    if os.path.isfile(event_log_file):
        with open(event_log_file, "r") as f:
            events = [json.loads(line) for line in f if line.strip()]
        if events:
            import pandas as pd
            df = pd.DataFrame(events)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            st.dataframe(df.sort_values("timestamp", ascending=False).head(100))
        else:
            st.info("No margin events logged yet.")
    else:
        st.info("No margin event log file found.")