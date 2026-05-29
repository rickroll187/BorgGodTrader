import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta


def show_advanced_dashboard(core):
    """Main dashboard entry point - Crypto Trader Friendly."""

    st.set_page_config(
        page_title="BorgGodTrader",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better trading UI
    st.markdown("""
    <style>
    .stMetric {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 5px;
    }
    .stMetric > div {
        color: #00ff88;
    }
    .price-up { color: #00ff88 !important; }
    .price-down { color: #ff4444 !important; }
    .big-font { font-size: 24px !important; font-weight: bold; }
    div[data-testid="stSidebar"] {
        background-color: #0e1117;
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1a1a2e/00ff88?text=BORG+TRADER", width=150)
        st.markdown("---")

        # Trading mode indicator
        mode = core.trading_mode
        if mode == "live":
            st.error("🔴 LIVE TRADING")
        else:
            st.success("🟢 PAPER MODE")

        st.markdown("---")

        menu = st.radio("", [
            "📊 Dashboard",
            "💹 Quick Trade",
            "📈 Strategies",
            "🧪 Backtest",
            "💼 Portfolio",
            "🌐 Multi-Chain",
            "📜 Trade Log",
            "⚠️ Risk Manager",
            "📰 News & Sentiment",
            "⚙️ Settings",
        ], label_visibility="collapsed")

        st.markdown("---")

        # Quick price ticker in sidebar
        st.caption("QUICK PRICES")
        _show_sidebar_prices(core)

    # Main content
    if menu == "📊 Dashboard":
        _show_main_dashboard(core)
    elif menu == "💹 Quick Trade":
        _show_trade_tab(core)
    elif menu == "📈 Strategies":
        _show_strategies_tab(core)
    elif menu == "🧪 Backtest":
        _show_backtest_tab(core)
    elif menu == "💼 Portfolio":
        _show_portfolio_tab(core)
    elif menu == "🌐 Multi-Chain":
        _show_chains_tab(core)
    elif menu == "📜 Trade Log":
        _show_logs_tab(core)
    elif menu == "⚠️ Risk Manager":
        _show_risk_tab(core)
    elif menu == "📰 News & Sentiment":
        _show_news_tab(core)
    elif menu == "⚙️ Settings":
        _show_settings_tab(core)


def _show_sidebar_prices(core):
    """Show quick prices in sidebar."""
    try:
        prices = core.tokeninfo_service.get_multiple_prices(["BTC", "ETH", "SOL"])
        for symbol, price in prices.items():
            if price:
                st.metric(symbol, f"${price:,.0f}" if price > 100 else f"${price:,.2f}")
    except:
        st.caption("Prices loading...")


def _show_main_dashboard(core):
    """Main dashboard with live data."""
    st.title("🤖 BorgGodTrader Dashboard")

    # Top row - Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    health = core.health_check()

    with col1:
        mode_icon = "🟢" if core.trading_mode == "live" else "🟡"
        st.metric("Mode", f"{mode_icon} {'LIVE' if core.trading_mode == 'live' else 'PAPER'}")

    with col2:
        exchanges_up = sum(1 for v in health.get("exchanges", {}).values() if v)
        st.metric("Exchanges", f"{exchanges_up}/4 Online")

    with col3:
        defi = "✅" if health.get("defi_connected") else "❌"
        st.metric("DeFi", defi)

    with col4:
        trades_24h = core.trade_logger.get_summary(24)
        st.metric("Trades (24h)", trades_24h.get("total_trades", 0))

    with col5:
        # Fear & Greed
        fg = core.data_sources.get_fear_greed_index()
        fg_val = fg.get("value", 50)
        fg_delta = "Greed" if fg_val > 50 else "Fear"
        st.metric("Fear/Greed", fg_val, fg_delta)

    st.markdown("---")

    # Main content area
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("📈 Live Market Prices")

        # Price cards
        symbols = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK"]
        prices = core.tokeninfo_service.get_multiple_prices(symbols)

        price_cols = st.columns(3)
        for i, (symbol, price) in enumerate(prices.items()):
            with price_cols[i % 3]:
                if price:
                    # Get market data for change %
                    mkt = core.tokeninfo_service.get_market_data(symbol)
                    change_24h = mkt.get("price_change_24h", 0) if mkt else 0

                    delta_color = "normal" if change_24h >= 0 else "inverse"
                    st.metric(
                        symbol,
                        f"${price:,.2f}" if price < 1000 else f"${price:,.0f}",
                        f"{change_24h:+.2f}%" if change_24h else None,
                        delta_color=delta_color
                    )

        st.markdown("---")

        # Market sentiment bar
        st.subheader("📊 Market Sentiment")
        fg_value = fg.get("value", 50)
        fg_class = fg.get("classification", "Neutral")

        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            st.write("😨 Fear")
        with col2:
            st.progress(fg_value / 100)
        with col3:
            st.write("🤑 Greed")

        sentiment_color = "🟢" if fg_value > 60 else "🔴" if fg_value < 40 else "🟡"
        st.markdown(f"**{sentiment_color} {fg_class}** ({fg_value}/100)")

        # Funding rates
        st.markdown("---")
        st.subheader("💰 Funding Rates")
        fund_cols = st.columns(3)
        for i, sym in enumerate(["BTCUSDT", "ETHUSDT", "SOLUSDT"]):
            with fund_cols[i]:
                try:
                    futures = core.data_sources.get_futures_data(sym)
                    rate = futures.get("rate", 0) * 100
                    rate_color = "🟢" if rate > 0 else "🔴"
                    st.metric(sym.replace("USDT", ""), f"{rate_color} {rate:.4f}%")
                except:
                    st.metric(sym.replace("USDT", ""), "N/A")

    with right_col:
        st.subheader("📋 Recent Trades")
        trades = core.trade_logger.get_trades(limit=10)
        if trades:
            for trade in trades[:8]:
                side = trade.get("side", "")
                icon = "🟢" if side == "buy" else "🔴"
                symbol = trade.get("symbol", "")
                amount = trade.get("amount", 0)
                status = trade.get("status", "")

                ts = trade.get("timestamp", 0)
                time_str = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else ""

                st.markdown(f"`{time_str}` {icon} **{side.upper()}** {amount:.4f} {symbol}")
        else:
            st.info("No recent trades")

        st.markdown("---")

        # Quick actions
        st.subheader("⚡ Quick Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 Buy BTC", use_container_width=True):
                result = core.execute_trade("BTC/USD", "buy", 0.001)
                if result.get("status") != "failed":
                    st.success("Order sent!")
                else:
                    st.error(result.get("error", "Failed"))

        with col2:
            if st.button("🔴 Sell BTC", use_container_width=True):
                result = core.execute_trade("BTC/USD", "sell", 0.001)
                if result.get("status") != "failed":
                    st.success("Order sent!")
                else:
                    st.error(result.get("error", "Failed"))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 Buy ETH", use_container_width=True):
                result = core.execute_trade("ETH/USD", "buy", 0.01)
                if result.get("status") != "failed":
                    st.success("Order sent!")
                else:
                    st.error(result.get("error", "Failed"))

        with col2:
            if st.button("🔴 Sell ETH", use_container_width=True):
                result = core.execute_trade("ETH/USD", "sell", 0.01)
                if result.get("status") != "failed":
                    st.success("Order sent!")
                else:
                    st.error(result.get("error", "Failed"))

        st.markdown("---")

        # Strategies status
        st.subheader("🤖 Active Strategies")
        strategies = core.strategy_manager.list_strategies()
        enabled_count = sum(1 for s in strategies
                          if getattr(core.strategy_manager.get_strategy(s), 'enabled', False))
        st.metric("Strategies", f"{enabled_count}/{len(strategies)} Active")


def _show_trade_tab(core):
    """Enhanced trading interface."""
    st.title("💹 Quick Trade")

    # Asset selector with prices
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Place Order")

        asset_options = {
            "BTC/USD": "Bitcoin",
            "ETH/USD": "Ethereum",
            "SOL/USD": "Solana",
            "AVAX/USD": "Avalanche",
            "MATIC/USD": "Polygon",
            "LINK/USD": "Chainlink",
            "AAVE/USD": "Aave",
            "UNI/USD": "Uniswap",
        }

        symbol = st.selectbox("Asset", list(asset_options.keys()),
                             format_func=lambda x: f"{x} - {asset_options[x]}")

        # Show current price
        asset = symbol.split("/")[0]
        price = core.tokeninfo_service.get_token_price(asset)
        if price:
            st.info(f"Current Price: **${price:,.2f}**")

        col_side1, col_side2 = st.columns(2)
        with col_side1:
            buy_btn = st.button("🟢 BUY", use_container_width=True, type="primary")
        with col_side2:
            sell_btn = st.button("🔴 SELL", use_container_width=True)

        side = "buy" if buy_btn else "sell" if sell_btn else None

        amount = st.number_input("Amount", min_value=0.0001, value=0.01, step=0.001,
                                format="%.4f")

        # Calculate USD value
        if price:
            usd_value = amount * price
            st.caption(f"≈ ${usd_value:,.2f} USD")

        order_type = st.radio("Order Type", ["Market", "Limit"], horizontal=True)

        limit_price = None
        if order_type == "Limit":
            limit_price = st.number_input("Limit Price", min_value=0.01,
                                         value=price if price else 100.0, step=0.01)

        exchange = st.selectbox("Exchange",
                               ["Auto (Best Price)", "Kraken", "Gemini", "DeFi (Uniswap)", "Paper"])
        exchange_map = {
            "Auto (Best Price)": None,
            "Kraken": "kraken",
            "Gemini": "gemini",
            "DeFi (Uniswap)": "defi",
            "Paper": "cex",
        }

        st.markdown("---")

        if st.button("📤 Execute Order", type="primary", use_container_width=True):
            if not side:
                st.warning("Select BUY or SELL first")
            else:
                with st.spinner("Executing..."):
                    result = core.execute_trade(
                        symbol=symbol,
                        side=side,
                        amount=amount,
                        exchange=exchange_map.get(exchange)
                    )

                    if result.get("status") == "failed":
                        st.error(f"❌ Order failed: {result.get('error')}")
                    else:
                        st.success(f"✅ Order executed!")
                        st.json(result)

    with col2:
        st.subheader("Order Book")
        st.caption(f"Simulated depth for {symbol}")

        # Simulated order book display
        if price:
            asks = [(price * (1 + i * 0.001), round(0.1 + i * 0.05, 2)) for i in range(5, 0, -1)]
            bids = [(price * (1 - i * 0.001), round(0.1 + i * 0.05, 2)) for i in range(1, 6)]

            st.markdown("**ASKS (Sell)**")
            for p, qty in asks:
                st.markdown(f"<span style='color: #ff4444'>${p:,.2f}</span> | {qty}", unsafe_allow_html=True)

            st.markdown(f"**→ ${price:,.2f} ←**")

            st.markdown("**BIDS (Buy)**")
            for p, qty in bids:
                st.markdown(f"<span style='color: #00ff88'>${p:,.2f}</span> | {qty}", unsafe_allow_html=True)

        st.markdown("---")

        # Natural language
        st.subheader("🗣️ Voice Command")
        nl_command = st.text_input("", placeholder="buy 0.1 ETH when BTC drops 2%")

        if nl_command:
            from services.extensibility.natural_language_strategy import parse_natural_language_command
            parsed = parse_natural_language_command(nl_command)

            if parsed.get("parsed"):
                st.success(f"Understood: {parsed.get('action')} {parsed.get('amount', '')} {parsed.get('asset', '')}")
                if st.button("Execute This"):
                    # Execute the parsed command
                    if parsed.get("action") in ["buy", "sell"]:
                        result = core.execute_trade(
                            symbol=f"{parsed.get('asset')}/USD",
                            side=parsed.get("action"),
                            amount=parsed.get("amount", 0.01)
                        )
                        st.json(result)
            else:
                st.warning("Couldn't parse command")


def _show_strategies_tab(core):
    """Strategy management."""
    st.title("📈 Trading Strategies")

    strategies = core.strategy_manager.list_strategies()

    if not strategies:
        st.info("No strategies loaded")
        return

    # Strategy overview
    col1, col2, col3 = st.columns(3)
    total = len(strategies)
    enabled = sum(1 for s in strategies if getattr(core.strategy_manager.get_strategy(s), 'enabled', True))

    col1.metric("Total Strategies", total)
    col2.metric("Enabled", enabled)
    col3.metric("Disabled", total - enabled)

    st.markdown("---")

    # Run all button
    if st.button("🚀 Run All Enabled Strategies", type="primary"):
        with st.spinner("Running strategies..."):
            results = core.strategy_manager.run_all({})
            for name, result in results.items():
                signal = result.get("signal", {})
                st.write(f"**{name}:** {signal.get('signal', 'N/A')} (conf: {signal.get('confidence', 0):.2f})")

    st.markdown("---")

    # Individual strategies
    for name in sorted(strategies):
        strategy = core.strategy_manager.get_strategy(name)
        enabled = getattr(strategy, 'enabled', True)
        description = getattr(strategy, 'description', 'No description')

        icon = "✅" if enabled else "⬜"

        with st.expander(f"{icon} **{name}** - {description}", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                last_run = getattr(strategy, 'last_run', None)
                if last_run:
                    st.write(f"Last run: {datetime.fromtimestamp(last_run).strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.write("Never run")

            with col2:
                last_signal = getattr(strategy, 'last_signal', None)
                if last_signal:
                    sig = last_signal.get('signal', 'N/A')
                    conf = last_signal.get('confidence', 0)
                    st.write(f"Last signal: **{sig}** ({conf:.0%})")

            with col3:
                if st.button(f"Run Now", key=f"run_{name}"):
                    result = core.strategy_manager.run_strategy(name)
                    st.json(result)

            # Enable/disable toggle
            new_enabled = st.checkbox("Enabled", value=enabled, key=f"enable_{name}")
            if new_enabled != enabled:
                if new_enabled:
                    core.strategy_manager.enable_strategy(name)
                else:
                    core.strategy_manager.disable_strategy(name)
                st.rerun()


def _show_backtest_tab(core):
    """Backtesting engine UI."""
    st.title("🧪 Strategy Backtester")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Configuration")

        available_strategies = [
            "ma_cross", "rsi_mean_reversion", "momentum",
            "fear_greed", "funding_rate", "arbitrage", "ml_ensemble"
        ]

        strategy_name = st.selectbox("Strategy", available_strategies)

        symbol = st.selectbox("Symbol", [
            "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD",
            "MATIC/USD", "LINK/USD", "AAVE/USD"
        ])

        interval = st.select_slider("Timeframe",
                                    options=["1h", "4h", "1d", "1w"],
                                    value="1d")

        days = st.slider("History (days)", 30, 365, 180)

        st.markdown("---")

        initial_capital = st.number_input("Capital ($)", value=10000.0, step=1000.0)
        commission = st.slider("Commission %", 0.0, 0.5, 0.1, 0.01)
        stop_loss = st.slider("Stop Loss %", 0.0, 10.0, 0.0, 0.5)
        take_profit = st.slider("Take Profit %", 0.0, 20.0, 0.0, 0.5)

        run_btn = st.button("🚀 Run Backtest", type="primary", use_container_width=True)

    with col2:
        if run_btn:
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
                        commission_pct=commission / 100,
                        stop_loss_pct=stop_loss / 100,
                        take_profit_pct=take_profit / 100,
                    )

                    # Results header
                    st.subheader("📊 Results")

                    # Key metrics
                    m1, m2, m3, m4 = st.columns(4)

                    ret_color = "normal" if result.total_return_pct >= 0 else "inverse"
                    m1.metric("Total Return", f"{result.total_return_pct:+.1f}%", delta_color=ret_color)
                    m2.metric("Max Drawdown", f"{result.max_drawdown_pct:.1f}%", delta_color="inverse")
                    m3.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
                    m4.metric("Win Rate", f"{result.win_rate:.0f}%")

                    m1, m2, m3, m4 = st.columns(4)
                    final = result.equity_curve[-1] if result.equity_curve else initial_capital
                    profit = final - initial_capital
                    m1.metric("Final Equity", f"${final:,.0f}", f"${profit:+,.0f}")
                    m2.metric("Profit Factor", f"{result.profit_factor:.2f}" if result.profit_factor < 100 else "∞")
                    m3.metric("Total Trades", result.total_trades)
                    m4.metric("Avg Trade", f"${result.expectancy:+.2f}")

                    st.markdown("---")

                    # Equity curve
                    if result.equity_curve:
                        st.subheader("Equity Curve")
                        eq_df = pd.DataFrame({
                            "Equity ($)": result.equity_curve,
                        })
                        st.line_chart(eq_df)

                    # Trade list
                    if result.trades:
                        st.subheader(f"Trade Log ({len(result.trades)} trades)")

                        trade_data = []
                        for t in result.trades[-50:]:
                            pnl_icon = "🟢" if t.pnl > 0 else "🔴"
                            trade_data.append({
                                "Entry": t.entry_time,
                                "Exit": t.exit_time,
                                "Side": t.side.upper(),
                                "Entry $": f"${t.entry_price:,.2f}",
                                "Exit $": f"${t.exit_price:,.2f}" if t.exit_price else "-",
                                "P&L": f"{pnl_icon} ${t.pnl:+,.2f}",
                                "Return": f"{t.pnl_pct * 100:+.1f}%",
                                "Reason": t.reason,
                            })

                        st.dataframe(pd.DataFrame(trade_data), use_container_width=True)

                except Exception as e:
                    st.error(f"Backtest failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.info("Configure backtest parameters and click Run")

            # Show strategy info
            strategy_info = {
                "ma_cross": "EMA crossover (12/26) with RSI filter. Good for trending markets.",
                "rsi_mean_reversion": "Buys RSI oversold + Bollinger lower band. Good for ranging markets.",
                "momentum": "ROC + MACD + Volume. Catches breakouts and strong trends.",
                "fear_greed": "Contrarian strategy using Fear & Greed Index. Buys fear, sells greed.",
                "funding_rate": "Trades on extreme perpetual funding rates (basis trade).",
                "arbitrage": "Cross-exchange spread detection. Requires accounts on multiple exchanges.",
                "ml_ensemble": "Machine learning ensemble. Trains on live data and adapts.",
            }

            st.markdown("### Strategy Info")
            st.info(strategy_info.get(strategy_name, "No description available"))


def _show_chains_tab(core):
    """Multi-chain status."""
    st.title("🌐 Multi-Chain Dashboard")

    try:
        chain_registry = getattr(core, 'chain_registry', None)
        if not chain_registry:
            from services.chains.chain_registry import ChainRegistry
            chain_registry = ChainRegistry()

        status = chain_registry.get_chain_status()

        # Summary
        connected = sum(1 for s in status.values() if s.get("connected"))
        total = len(status)

        col1, col2, col3 = st.columns(3)
        col1.metric("Chains Supported", total)
        col2.metric("Connected", connected)
        col3.metric("Offline", total - connected)

        st.markdown("---")

        # Chain grid
        chain_cols = st.columns(4)

        for i, (chain_name, info) in enumerate(status.items()):
            with chain_cols[i % 4]:
                connected = info.get("connected", False)
                icon = "🟢" if connected else "⚪"
                native = info.get("native_token", "?")

                st.markdown(f"### {icon} {chain_name.title()}")
                st.caption(f"Chain ID: {info.get('chain_id')} | {native}")

                if connected:
                    block = info.get("block_number", "N/A")
                    st.write(f"Block: `{block}`")
                else:
                    st.write("Not connected")

        # Wallet balances
        wallet = getattr(core, 'wallet_address', None)
        if wallet:
            st.markdown("---")
            st.subheader("💰 Wallet Balances")
            st.caption(f"Wallet: `{wallet[:10]}...{wallet[-6:]}`")

            if st.button("🔄 Fetch All Balances"):
                with st.spinner("Scanning chains..."):
                    balances = chain_registry.get_all_balances(wallet)

                    if balances:
                        bal_cols = st.columns(4)
                        for i, (chain, balance) in enumerate(balances.items()):
                            with bal_cols[i % 4]:
                                token = chain_registry.get_native_token(chain)
                                st.metric(f"{chain.title()}", f"{balance:.4f} {token}")
                    else:
                        st.info("No balances found")

    except Exception as e:
        st.error(f"Chain status failed: {e}")


def _show_portfolio_tab(core):
    """Portfolio overview."""
    st.title("💼 Portfolio")

    try:
        portfolio = core.portfolio_service.get_portfolio_overview(core.tokeninfo_service)
        total_usd = portfolio.get('total_usd', 0)

        st.metric("Total Portfolio Value", f"${total_usd:,.2f}")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔗 On-Chain Holdings")
            on_chain = portfolio.get("on_chain", {})
            if on_chain:
                data = []
                for asset, info in on_chain.items():
                    data.append({
                        "Asset": asset,
                        "Balance": f"{info.get('balance', 0):.6f}",
                        "Price": f"${info.get('price', 0):,.2f}",
                        "Value": f"${info.get('value_usd', 0):,.2f}",
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("No on-chain balances (configure wallet + Covalent API)")

        with col2:
            st.subheader("🏦 Exchange Balances")
            cex = portfolio.get("cex", {})
            if cex:
                for exchange, balances in cex.items():
                    st.write(f"**{exchange.title()}**")
                    for asset, info in balances.items():
                        st.write(f"  {asset}: {info.get('balance', 0):.6f}")
            else:
                st.info("No exchange balances tracked")

            # Paper trading balance
            if core.trading_mode == "paper":
                st.markdown("---")
                st.subheader("📝 Paper Trading")
                paper_bal = core.cex_executor.paper_balances
                for asset, bal in paper_bal.items():
                    if bal > 0:
                        st.write(f"**{asset}:** {bal:,.4f}")

    except Exception as e:
        st.error(f"Portfolio error: {e}")


def _show_logs_tab(core):
    """Trade log."""
    st.title("📜 Trade History")

    trades = core.trade_logger.get_trades(limit=200)

    if not trades:
        st.info("No trades recorded yet. Execute some trades to see history here.")
        return

    # Summary stats
    summary = core.trade_logger.get_summary(24)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Trades (24h)", summary.get("total_trades", 0))
    col2.metric("Buys", summary.get("buys", 0))
    col3.metric("Sells", summary.get("sells", 0))
    col4.metric("Failed", summary.get("failed", 0))

    st.markdown("---")

    # Trade table
    df = pd.DataFrame(trades)
    if 'timestamp' in df.columns:
        df['Time'] = pd.to_datetime(df['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M')

    display_cols = ['Time', 'side', 'amount', 'symbol', 'exchange', 'status', 'price']
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    # Export
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export CSV"):
            core.trade_logger.export_csv("trade_history.csv")
            st.success("Exported to trade_history.csv")


def _show_risk_tab(core):
    """Risk management."""
    st.title("⚠️ Risk Manager")

    # Risk limits
    col1, col2, col3 = st.columns(3)
    col1.metric("Max Position Size", f"{core.max_position_size * 100:.0f}%")
    col2.metric("Max Drawdown", f"{core.max_drawdown * 100:.0f}%")
    col3.metric("Slippage Tolerance", f"{core.default_slippage * 100:.2f}%")

    st.markdown("---")

    # Current exposure
    st.subheader("📊 Current Exposure")
    exposure = core.position_manager.get_exposure_report()

    col1, col2, col3 = st.columns(3)
    col1.metric("Open Positions", exposure.get("open_positions", 0))
    col2.metric("Unrealized P&L", f"${exposure.get('unrealized_pnl', 0):+,.2f}")
    col3.metric("Realized P&L", f"${exposure.get('realized_pnl', 0):+,.2f}")

    # Position details
    positions = core.position_manager.get_positions()
    if positions:
        st.subheader("Open Positions")
        pos_data = []
        for pos in positions:
            pos_data.append({
                "Symbol": pos.get("symbol"),
                "Side": pos.get("side"),
                "Amount": pos.get("amount"),
                "Entry": f"${pos.get('entry_price', 0):,.2f}",
                "Current": f"${pos.get('current_price', 0):,.2f}",
                "P&L": f"${pos.get('unrealized_pnl', 0):+,.2f}",
            })
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)

    # Anomalies
    st.markdown("---")
    st.subheader("🚨 Anomaly Detection")
    anomalies = core.anomaly_detector.get_recent_anomalies(24)
    if anomalies:
        for a in anomalies[-5:]:
            st.warning(f"**{a.get('type')}** on {a.get('symbol')} - Z-score: {a.get('z_score', 0):.2f}")
    else:
        st.success("✅ No anomalies detected in the last 24 hours")


def _show_news_tab(core):
    """News and sentiment."""
    st.title("📰 News & Sentiment")

    # Sentiment summary
    sentiment = core.news_scraper.get_sentiment_summary()

    col1, col2, col3 = st.columns(3)

    overall = sentiment.get("overall", "neutral")
    icon = "🟢" if overall == "bullish" else "🔴" if overall == "bearish" else "🟡"

    col1.metric("Sentiment", f"{icon} {overall.upper()}")
    col2.metric("Score", f"{sentiment.get('score', 0):+.2f}")
    col3.metric("Articles", sentiment.get("total", 0))

    st.markdown("---")

    # News feed
    news = core.news_scraper.fetch_latest(limit=15)

    for item in news:
        sentiment = item.get("sentiment", "neutral")
        icon = "🟢" if sentiment == "bullish" else "🔴" if sentiment == "bearish" else "⚪"

        with st.container():
            st.markdown(f"{icon} **{item.get('title', 'No title')}**")
            st.caption(f"{item.get('source', 'Unknown')} | {', '.join(item.get('currencies', []))}")
            if item.get('url'):
                st.markdown(f"[Read more]({item.get('url')})")
            st.markdown("---")


def _show_settings_tab(core):
    """Settings."""
    st.title("⚙️ Settings")

    st.subheader("Current Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Trading**")
        st.write(f"- Mode: `{core.trading_mode}`")
        st.write(f"- Max Position: `{core.max_position_size * 100}%`")
        st.write(f"- Max Drawdown: `{core.max_drawdown * 100}%`")

    with col2:
        st.write("**Connections**")
        rpc = core.rpc_url[:30] + "..." if core.rpc_url else "Not set"
        wallet = core.wallet_address[:15] + "..." if core.wallet_address else "Not set"
        st.write(f"- RPC: `{rpc}`")
        st.write(f"- Wallet: `{wallet}`")

    st.markdown("---")

    st.subheader("Service Health")
    health = core.health_check()

    for service, status in health.get("exchanges", {}).items():
        icon = "✅" if status else "❌"
        st.write(f"{icon} {service.title()}")

    defi_icon = "✅" if health.get("defi_connected") else "❌"
    st.write(f"{defi_icon} DeFi (Web3)")

    st.markdown("---")

    st.info("""
    **To configure BorgGodTrader:**

    1. Copy `.env.example` to `.env`
    2. Add your API keys:
       - Kraken / Gemini for CEX trading
       - Ethereum RPC URL for DeFi
       - CoinGecko / Covalent for data
    3. Restart the dashboard

    **Important:** Keep `TRADING_MODE=paper` until you're confident!
    """)
