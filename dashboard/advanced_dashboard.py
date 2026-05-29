import streamlit as st
import pandas as pd
import time
from datetime import datetime


def show_advanced_dashboard(core):
    """Main dashboard entry point."""

    st.set_page_config(
        page_title="BorgGodTrader",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🤖 BorgGodTrader")
    st.caption("Assimilate. Adapt. Advance.")

    # Sidebar navigation
    menu = st.sidebar.radio("Navigation", [
        "📊 Dashboard",
        "💹 Trade",
        "📈 Strategies",
        "🧪 Backtest",
        "💼 Portfolio",
        "🌐 Chains",
        "📜 Trade Log",
        "⚠️ Risk",
        "📰 News",
        "🔧 Settings",
    ])

    if menu == "📊 Dashboard":
        _show_dashboard_tab(core)
    elif menu == "💹 Trade":
        _show_trade_tab(core)
    elif menu == "📈 Strategies":
        _show_strategies_tab(core)
    elif menu == "🧪 Backtest":
        _show_backtest_tab(core)
    elif menu == "💼 Portfolio":
        _show_portfolio_tab(core)
    elif menu == "🌐 Chains":
        _show_chains_tab(core)
    elif menu == "📜 Trade Log":
        _show_logs_tab(core)
    elif menu == "⚠️ Risk":
        _show_risk_tab(core)
    elif menu == "📰 News":
        _show_news_tab(core)
    elif menu == "🔧 Settings":
        _show_settings_tab(core)


def _show_dashboard_tab(core):
    """Main dashboard overview."""

    # Health check
    col1, col2, col3 = st.columns(3)

    health = core.health_check()
    with col1:
        mode = "🟢 LIVE" if core.trading_mode == "live" else "🟡 PAPER"
        st.metric("Trading Mode", mode)

    with col2:
        defi_status = "🟢 Connected" if health.get("defi_connected") else "🔴 Disconnected"
        st.metric("DeFi", defi_status)

    with col3:
        exchanges_up = sum(1 for v in health.get("exchanges", {}).values() if v)
        st.metric("Exchanges", f"{exchanges_up} online")

    st.divider()

    # Quick stats
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Market Data")

        # Get some prices
        prices = core.tokeninfo_service.get_multiple_prices(["BTC", "ETH", "SOL"])

        for symbol, price in prices.items():
            if price:
                st.metric(symbol, f"${price:,.2f}")

    with col2:
        st.subheader("Recent Activity")

        trades = core.trade_logger.get_trades(limit=5)
        if trades:
            for trade in trades:
                side_icon = "🟢" if trade.get("side") == "buy" else "🔴"
                st.text(f"{side_icon} {trade.get('side', '').upper()} {trade.get('amount', 0)} {trade.get('symbol', '')} @ {trade.get('exchange', 'unknown')}")
        else:
            st.info("No recent trades")

    # Market sentiment
    st.subheader("Market Sentiment")
    fear_greed = core.data_sources.get_fear_greed_index()
    fg_value = fear_greed.get("value", 50)
    fg_class = fear_greed.get("classification", "Neutral")

    st.progress(fg_value / 100)
    st.caption(f"Fear & Greed Index: {fg_value} - {fg_class}")


def _show_trade_tab(core):
    """Manual trading interface."""
    st.subheader("Manual Trading")

    col1, col2 = st.columns(2)

    with col1:
        symbol = st.selectbox("Asset", ["BTC/USD", "ETH/USD", "SOL/USD", "MATIC/USD"])
        side = st.radio("Side", ["buy", "sell"], horizontal=True)
        amount = st.number_input("Amount", min_value=0.0001, value=0.01, step=0.001)

    with col2:
        exchange = st.selectbox("Exchange", ["auto", "kraken", "gemini", "defi", "paper"])
        order_type = st.selectbox("Order Type", ["market", "limit"])
        if order_type == "limit":
            price = st.number_input("Limit Price", min_value=0.01, value=100.0)
        else:
            price = None

    st.divider()

    # Natural language input
    st.subheader("Or use natural language:")
    nl_command = st.text_input("Enter command", placeholder="e.g., 'buy 0.1 ETH when BTC drops 2%'")

    if nl_command:
        from services.extensibility.natural_language_strategy import parse_natural_language_command
        parsed = parse_natural_language_command(nl_command)
        st.json(parsed)

    st.divider()

    if st.button("Execute Trade", type="primary"):
        with st.spinner("Executing..."):
            result = core.execute_trade(
                symbol=symbol,
                side=side,
                amount=amount,
                exchange=None if exchange == "auto" else exchange
            )
            if result.get("status") == "failed":
                st.error(f"Trade failed: {result.get('error')}")
            else:
                st.success(f"Trade executed: {result}")


def _show_strategies_tab(core):
    """Strategy management."""
    st.subheader("Trading Strategies")

    strategies = core.strategy_manager.list_strategies()

    if not strategies:
        st.info("No strategies loaded")
        return

    for name in strategies:
        strategy = core.strategy_manager.get_strategy(name)
        with st.expander(f"📈 {name}", expanded=False):
            enabled = getattr(strategy, 'enabled', True)
            st.write(f"**Status:** {'✅ Enabled' if enabled else '❌ Disabled'}")

            last_run = getattr(strategy, 'last_run', None)
            if last_run:
                st.write(f"**Last Run:** {datetime.fromtimestamp(last_run).strftime('%Y-%m-%d %H:%M:%S')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Run {name}", key=f"run_{name}"):
                    result = core.strategy_manager.run_strategy(name)
                    st.json(result)
            with col2:
                if enabled:
                    if st.button(f"Disable {name}", key=f"disable_{name}"):
                        core.strategy_manager.disable_strategy(name)
                        st.rerun()
                else:
                    if st.button(f"Enable {name}", key=f"enable_{name}"):
                        core.strategy_manager.enable_strategy(name)
                        st.rerun()


def _show_backtest_tab(core):
    """Backtesting engine UI."""
    st.subheader("Strategy Backtester")

    col1, col2, col3 = st.columns(3)

    available_strategies = [
        "ma_cross", "rsi_mean_reversion", "momentum",
        "fear_greed_contrarian", "funding_rate", "arbitrage",
    ]

    with col1:
        strategy_name = st.selectbox("Strategy", available_strategies)
        symbol = st.selectbox("Symbol", ["BTC/USD", "ETH/USD", "SOL/USD", "MATIC/USD", "AVAX/USD"])

    with col2:
        interval = st.selectbox("Interval", ["1d", "4h", "1h", "1w"])
        days = st.slider("Days of History", min_value=30, max_value=365, value=180)

    with col3:
        initial_capital = st.number_input("Starting Capital ($)", value=10000.0, step=1000.0)
        commission = st.number_input("Commission %", value=0.1, step=0.05) / 100
        stop_loss = st.number_input("Stop Loss %", value=0.0, step=0.5) / 100
        take_profit = st.number_input("Take Profit %", value=0.0, step=0.5) / 100

    if st.button("Run Backtest", type="primary"):
        with st.spinner(f"Backtesting {strategy_name} on {symbol}..."):
            try:
                from services.backtest.runner import BacktestRunner

                runner = BacktestRunner()
                result = runner.run_strategy(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    interval=interval,
                    days=days,
                    initial_capital=initial_capital,
                    commission_pct=commission,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                )

                # Summary metrics
                st.divider()
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Return", f"{result.total_return_pct:+.1f}%")
                m2.metric("Max Drawdown", f"{result.max_drawdown_pct:.1f}%")
                m3.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
                m4.metric("Win Rate", f"{result.win_rate:.0f}%")
                m5.metric("Total Trades", result.total_trades)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Annual Return", f"{result.annualized_return_pct:+.1f}%")
                    st.metric("Profit Factor", f"{result.profit_factor:.2f}" if result.profit_factor != float("inf") else "∞")
                    st.metric("Expectancy", f"${result.expectancy:+.2f}/trade")
                with col2:
                    final = result.equity_curve[-1] if result.equity_curve else initial_capital
                    st.metric("Final Equity", f"${final:,.2f}", f"${final - initial_capital:+,.2f}")
                    st.metric("Sortino Ratio", f"{result.sortino_ratio:.2f}")
                    st.metric("Calmar Ratio", f"{result.calmar_ratio:.2f}")

                # Equity curve
                if result.equity_curve:
                    st.subheader("Equity Curve")
                    eq_df = pd.DataFrame({
                        "Equity": result.equity_curve,
                        "Bar": list(range(len(result.equity_curve)))
                    })
                    st.line_chart(eq_df.set_index("Bar")["Equity"])

                # Trade list
                if result.trades:
                    st.subheader(f"Trades ({result.total_trades})")
                    trade_data = [{
                        "Entry Bar": t.entry_time,
                        "Exit Bar": t.exit_time,
                        "Side": t.side,
                        "Entry Price": f"${t.entry_price:,.2f}",
                        "Exit Price": f"${t.exit_price:,.2f}" if t.exit_price else "-",
                        "P&L": f"${t.pnl:+,.2f}",
                        "P&L %": f"{t.pnl_pct * 100:+.2f}%",
                        "Exit Reason": t.reason,
                    } for t in result.trades[:100]]
                    st.dataframe(pd.DataFrame(trade_data), use_container_width=True)

            except Exception as e:
                st.error(f"Backtest failed: {e}")
                import traceback
                st.code(traceback.format_exc())


def _show_chains_tab(core):
    """Multi-chain status and balances."""
    st.subheader("Chain Status")

    try:
        chain_registry = getattr(core, 'chain_registry', None)
        if not chain_registry:
            from services.chains.chain_registry import ChainRegistry
            chain_registry = ChainRegistry()

        status = chain_registry.get_chain_status()

        for chain_name, info in status.items():
            connected = info.get("connected", False)
            icon = "🟢" if connected else "⚪"
            using_public = info.get("using_public_rpc", True)
            rpc_label = "public RPC" if using_public else "configured RPC"

            with st.expander(f"{icon} {info.get('name', chain_name)}", expanded=connected):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Chain ID:** {info.get('chain_id')}")
                col2.write(f"**Native:** {info.get('native_token')}")
                col3.write(f"**Block time:** {info.get('block_time')}s")

                if connected:
                    st.write(f"**Block:** {info.get('block_number', 'N/A')} | {rpc_label}")
                else:
                    st.write(f"Not connected ({rpc_label})")
                    if using_public:
                        env_vars = {
                            "ethereum": "ETH_RPC_URL",
                            "polygon": "POLYGON_RPC_URL",
                            "arbitrum": "ARBITRUM_RPC_URL",
                            "optimism": "OPTIMISM_RPC_URL",
                            "bsc": "BSC_RPC_URL",
                            "avalanche": "AVAX_RPC_URL",
                            "base": "BASE_RPC_URL",
                        }
                        if chain_name in env_vars:
                            st.caption(f"Set {env_vars[chain_name]} in .env for dedicated RPC")

        # Wallet balance across chains
        wallet = getattr(core, 'wallet_address', None)
        if wallet:
            st.divider()
            st.subheader("Wallet Balances Across Chains")
            if st.button("Fetch All Balances"):
                with st.spinner("Checking all chains..."):
                    balances = chain_registry.get_all_balances(wallet)
                    if balances:
                        for chain, balance in balances.items():
                            token = chain_registry.get_native_token(chain)
                            st.write(f"**{chain}:** {balance:.6f} {token}")
                    else:
                        st.info("No balances found (chains may not be connected)")

    except Exception as e:
        st.error(f"Chain status failed: {e}")


def _show_portfolio_tab(core):
    """Portfolio overview."""
    st.subheader("Portfolio Overview")

    # Try to get portfolio data
    try:
        portfolio = core.portfolio_service.get_portfolio_overview(core.tokeninfo_service)

        st.metric("Total Value (USD)", f"${portfolio.get('total_usd', 0):,.2f}")

        # On-chain balances
        st.write("**On-Chain Balances:**")
        on_chain = portfolio.get("on_chain", {})
        if on_chain:
            df = pd.DataFrame([
                {"Asset": k, "Balance": v.get("balance", 0), "Price": v.get("price", 0), "Value": v.get("value_usd", 0)}
                for k, v in on_chain.items()
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No on-chain balances found (check wallet address and API key)")

        # CEX balances
        st.write("**Exchange Balances:**")
        cex = portfolio.get("cex", {})
        if cex:
            for exchange, balances in cex.items():
                st.write(f"_{exchange}_")
                st.json(balances)
        else:
            st.info("No exchange balances tracked")

    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")


def _show_logs_tab(core):
    """Trade history and logs."""
    st.subheader("Trade History")

    trades = core.trade_logger.get_trades(limit=100)

    if trades:
        df = pd.DataFrame(trades)
        if 'timestamp' in df.columns:
            df['time'] = pd.to_datetime(df['timestamp'], unit='s')

        st.dataframe(df, use_container_width=True)

        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export CSV"):
                core.trade_logger.export_csv("trade_export.csv")
                st.success("Exported to trade_export.csv")

        # Summary
        summary = core.trade_logger.get_summary(24)
        st.write("**24h Summary:**")
        st.json(summary)
    else:
        st.info("No trades recorded yet")


def _show_risk_tab(core):
    """Risk management."""
    st.subheader("Risk Management")

    # Current risk settings
    st.write("**Risk Limits:**")
    st.write(f"- Max Position Size: {core.max_position_size * 100:.1f}%")
    st.write(f"- Max Drawdown: {core.max_drawdown * 100:.1f}%")
    st.write(f"- Default Slippage: {core.default_slippage * 100:.2f}%")

    # Exposure report
    st.divider()
    st.write("**Current Exposure:**")
    exposure = core.position_manager.get_exposure_report()
    st.json(exposure)

    # Anomaly alerts
    st.divider()
    st.write("**Recent Anomalies:**")
    anomalies = core.anomaly_detector.get_recent_anomalies(24)
    if anomalies:
        for a in anomalies[-5:]:
            st.warning(f"{a.get('type')}: {a.get('symbol')} - z-score: {a.get('z_score', 0):.2f}")
    else:
        st.success("No anomalies detected in last 24h")


def _show_news_tab(core):
    """Crypto news feed."""
    st.subheader("Crypto News")

    news = core.news_scraper.fetch_latest(limit=10)

    for item in news:
        sentiment = item.get("sentiment", "neutral")
        if sentiment == "bullish":
            icon = "🟢"
        elif sentiment == "bearish":
            icon = "🔴"
        else:
            icon = "⚪"

        st.markdown(f"{icon} **[{item.get('title')}]({item.get('url')})**")
        st.caption(f"Source: {item.get('source')} | Currencies: {', '.join(item.get('currencies', []))}")
        st.divider()

    # Sentiment summary
    sentiment_summary = core.news_scraper.get_sentiment_summary()
    st.metric("Overall Sentiment", sentiment_summary.get("overall", "Neutral").upper())


def _show_settings_tab(core):
    """Settings and configuration."""
    st.subheader("Settings")

    st.write("**Current Configuration:**")
    st.write(f"- Trading Mode: `{core.trading_mode}`")
    st.write(f"- RPC URL: `{core.rpc_url[:20]}...`" if core.rpc_url else "- RPC URL: Not configured")
    st.write(f"- Wallet: `{core.wallet_address[:10]}...`" if core.wallet_address else "- Wallet: Not configured")

    st.divider()

    st.write("**Service Health:**")
    health = core.health_check()
    st.json(health)

    st.divider()

    st.info("""
    **Configuration:**

    Edit `.env` file to configure:
    - Exchange API keys (Kraken, Gemini)
    - Ethereum RPC URL and wallet
    - Notification settings (Telegram, Discord)
    - Risk parameters

    Copy `.env.example` to `.env` to get started.
    """)
