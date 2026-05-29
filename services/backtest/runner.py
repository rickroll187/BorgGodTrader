"""
Backtest Runner - easy interface for running strategy backtests.

Usage:
    from services.backtest.runner import BacktestRunner

    runner = BacktestRunner()
    result = runner.run_strategy(
        strategy_name="ma_cross",
        symbol="BTC/USD",
        interval="1d",
        days=365
    )
    runner.print_report(result)
"""

import time
import logging
from typing import Dict, Any, Optional, Type

from services.backtest.engine import BacktestEngine, BacktestConfig, BacktestResult
from services.backtest.data_fetcher import BacktestDataFetcher

logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    High-level interface for backtesting strategies.
    """

    def __init__(self):
        self.fetcher = BacktestDataFetcher()
        self.results_history: list = []

    def run_strategy(
        self,
        strategy_name: str,
        symbol: str = "BTC/USD",
        interval: str = "1d",
        days: int = 365,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005,
        stop_loss_pct: float = 0.0,
        take_profit_pct: float = 0.0,
        allow_short: bool = False,
        strategy_kwargs: Dict = None,
    ) -> BacktestResult:
        """
        Fetch data and run a named strategy through the backtest engine.

        Args:
            strategy_name: Name matching services/strategies/strategy_<name>.py
            symbol: Trading pair (e.g., "BTC/USD")
            interval: Bar interval ("1h", "4h", "1d")
            days: How many days of history to backtest
            initial_capital: Starting capital in USD
            commission_pct: Commission per trade (0.001 = 0.1%)
            slippage_pct: Slippage per trade (0.0005 = 0.05%)
            stop_loss_pct: Stop loss % (0 = disabled)
            take_profit_pct: Take profit % (0 = disabled)
            allow_short: Allow short selling
            strategy_kwargs: Extra kwargs to pass to strategy constructor
        """
        logger.info(f"Backtesting {strategy_name} on {symbol} {days}d @ {interval}")

        # Fetch price data
        limit = self._estimate_bars(interval, days)
        bars = self.fetcher.fetch_ohlcv(symbol, interval, limit=min(limit, 1000))

        if not bars:
            logger.warning(f"No data fetched for {symbol}, trying CoinGecko...")
            coin_map = {
                "BTC/USD": "bitcoin", "ETH/USD": "ethereum",
                "SOL/USD": "solana", "MATIC/USD": "matic-network",
                "AVAX/USD": "avalanche-2", "DOT/USD": "polkadot",
                "LINK/USD": "chainlink", "AAVE/USD": "aave",
            }
            coin_id = coin_map.get(symbol, symbol.split("/")[0].lower())
            bars = self.fetcher.fetch_coingecko_history(coin_id, days=min(days, 365))

        if not bars:
            raise ValueError(f"Could not fetch price data for {symbol}")

        logger.info(f"Running backtest on {len(bars)} bars")

        # Load strategy class
        strategy_class = self._load_strategy(strategy_name)
        if not strategy_class:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        # Configure engine
        config = BacktestConfig(
            symbol=symbol,
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            allow_short=allow_short,
        )

        engine = BacktestEngine(config)
        timestamps = [b.get("timestamp", i) for i, b in enumerate(bars)]

        result = engine.run_strategy(
            bars,
            strategy_class,
            strategy_kwargs=strategy_kwargs or {"symbol": symbol},
            timestamps=timestamps,
        )

        self.results_history.append({
            "strategy": strategy_name,
            "symbol": symbol,
            "interval": interval,
            "days": days,
            "result": result,
            "run_at": time.time(),
        })

        return result

    def run_custom(self, signal_fn, price_data, config: BacktestConfig = None,
                   timestamps=None) -> BacktestResult:
        """Run backtest with a custom signal function."""
        engine = BacktestEngine(config or BacktestConfig())
        return engine.run(price_data, signal_fn, timestamps)

    def _load_strategy(self, name: str) -> Optional[Type]:
        """Load strategy class by name."""
        import importlib

        # Try strategy_<name> module pattern
        module_names = [
            f"services.strategies.strategy_{name}",
            f"services.strategies.{name}",
        ]

        for module_name in module_names:
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, "Strategy"):
                    return mod.Strategy
            except ImportError:
                continue
            except Exception as e:
                logger.error(f"Error loading strategy {name}: {e}")

        logger.error(f"Strategy '{name}' not found")
        return None

    def _estimate_bars(self, interval: str, days: int) -> int:
        """Estimate number of bars for given interval and days."""
        bars_per_day = {
            "1m": 1440, "5m": 288, "15m": 96, "30m": 48,
            "1h": 24, "4h": 6, "1d": 1, "1w": 0.143,
        }
        bpd = bars_per_day.get(interval, 24)
        return int(days * bpd)

    def compare_strategies(self, strategies: list, symbol: str = "BTC/USD",
                            interval: str = "1d", days: int = 365) -> Dict[str, BacktestResult]:
        """Run multiple strategies and compare performance."""
        results = {}
        for strategy_name in strategies:
            try:
                results[strategy_name] = self.run_strategy(
                    strategy_name, symbol, interval, days
                )
                time.sleep(0.5)  # Avoid hammering APIs
            except Exception as e:
                logger.error(f"Strategy {strategy_name} backtest failed: {e}")

        return results

    def print_report(self, result: BacktestResult, strategy_name: str = "Strategy"):
        """Print a nicely formatted backtest report."""
        print(f"\n{'='*55}")
        print(f"  BACKTEST REPORT: {strategy_name}")
        print(f"{'='*55}")
        print(f"  Symbol:          {result.config.symbol}")
        print(f"  Capital:         ${result.config.initial_capital:,.2f}")
        print(f"  Bars tested:     {len(result.equity_curve)}")
        print(f"{'='*55}")
        print(f"  RETURNS")
        print(f"  Total Return:    {result.total_return_pct:+.2f}%")
        print(f"  Annual Return:   {result.annualized_return_pct:+.2f}%")
        final = result.equity_curve[-1] if result.equity_curve else result.config.initial_capital
        print(f"  Final Equity:    ${final:,.2f}")
        print(f"{'='*55}")
        print(f"  RISK")
        print(f"  Max Drawdown:    {result.max_drawdown_pct:.2f}%")
        print(f"  Sharpe Ratio:    {result.sharpe_ratio:.3f}")
        print(f"  Sortino Ratio:   {result.sortino_ratio:.3f}")
        print(f"  Calmar Ratio:    {result.calmar_ratio:.3f}")
        print(f"{'='*55}")
        print(f"  TRADES")
        print(f"  Total Trades:    {result.total_trades}")
        print(f"  Win Rate:        {result.win_rate:.1f}%")
        print(f"  Profit Factor:   {result.profit_factor:.2f}")
        print(f"  Avg Win:         {result.avg_win_pct:+.2f}%")
        print(f"  Avg Loss:        {result.avg_loss_pct:+.2f}%")
        print(f"  Expectancy:      ${result.expectancy:+.2f}")
        print(f"  Avg Duration:    {result.avg_trade_duration:.1f} bars")
        print(f"{'='*55}\n")

    def to_dict(self, result: BacktestResult, strategy_name: str = "") -> Dict[str, Any]:
        """Convert result to plain dict for JSON/dashboard display."""
        return {
            "strategy": strategy_name,
            "symbol": result.config.symbol,
            "initial_capital": result.config.initial_capital,
            "final_equity": result.equity_curve[-1] if result.equity_curve else result.config.initial_capital,
            "total_return_pct": result.total_return_pct,
            "annualized_return_pct": result.annualized_return_pct,
            "max_drawdown_pct": result.max_drawdown_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "calmar_ratio": result.calmar_ratio,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "avg_win_pct": result.avg_win_pct,
            "avg_loss_pct": result.avg_loss_pct,
            "expectancy": result.expectancy,
            "equity_curve": result.equity_curve,
        }
