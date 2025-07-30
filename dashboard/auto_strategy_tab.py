import streamlit as st

def auto_strategy_widget(auto_strategy_gen):
    st.header("🧬 Auto Strategy Generation")
    n = st.number_input("Number of Strategies to Generate", min_value=1, value=10)
    if st.button("Generate & Backtest"):
        results = auto_strategy_gen.generate_and_test(n=n)
        st.success(f"Generated {n} new strategies!")
        st.dataframe([{**r['params'], **r['performance']} for r in results[:5]])
    st.markdown("### Top Past Strategies")
    top = auto_strategy_gen.top_strategies()
    st.table([{**r['params'], **r['performance']} for r in top])