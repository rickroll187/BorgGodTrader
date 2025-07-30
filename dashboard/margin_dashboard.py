import streamlit as st
import pandas as pd
import time

def margin_dashboard(margin_manager, interest_tracker, liquidation_events=[]):
    st.title("Margin Debt Lifecycle Dashboard")

    # Live positions
    st.subheader("Open Margin Positions")
    positions = margin_manager.get_all_positions()
    if positions:
        df = pd.DataFrame.from_dict(positions, orient="index")
        st.dataframe(df)
    else:
        st.info("No open margin positions.")

    # Interest
    st.subheader("Accrued Interest by Symbol")
    interest = interest_tracker.get_all_accrued()
    if interest:
        st.table(pd.DataFrame(list(interest.items()), columns=["Symbol", "Accrued Interest"]))
    else:
        st.info("No accrued interest.")

    # Liquidation Events
    st.subheader("Recent Liquidation Warnings/Actions")
    if liquidation_events:
        for e in liquidation_events[-10:]:
            st.warning(e)
    else:
        st.info("No recent liquidation warnings.")

    st.caption(f"Last update: {time.ctime()} (refresh to update)")