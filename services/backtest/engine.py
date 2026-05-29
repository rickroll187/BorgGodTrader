import time
import logging
import math
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class BacktestConfig:
    symbol: str = "BTC/USD"
    initial_capital: float = 10000.0
    commission_pct: float = 0.001        # 0.1% per trade
    slippage_pct: float = 0.0005         # 0.05% slippage
    position_size_pct: float = 0.95      # Use 95% of capital per trade
    max_open_positions: int = 1
    stop_loss_pct: float = 0.0           # 0 = disabled
    take_profit_pct: float = 0.0         # 0 = disabled
    allow_short: bool = False
    risk_free_rate: float = 0.05         # 5% annual for Sharpe calculation


@dataclass
class Trade:
    entry_time: int                       # bar index
    exit_time: Optional[int]
    side: str                             # "long" or "short"
    entry_price: float
    exit_price: Optional[float]
    size: float                           # units of base asset
    commission: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""                      # why exited


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[Any] = field(default_factory=list)

    # Computed metrics
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_trade_duration: float = 0.0      # bars
    calmar_ratio: float = 0.0
    expectancy: float = 0.0


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Supports:
    - Long and short positions
    - Commission and slippage modeling
    - Stop-loss and take-profit
    - Multiple concurrent positions
    - Comprehensive performance metrics
    """

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.reset()

    def reset(self):
        """Reset engine state for a fresh backtest."""
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Dict] = {}     # active positions
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.bar_index = 0
        self.current_price = 0.0

    def run(self, price_data: List[float], signal_fn: Callable,
            timestamps: List = None) -> BacktestResult:
        """
        Run backtest over price data.

        Args:
            price_data: List of OHLCV dicts or just close prices
            signal_fn: Callable(bar_index, prices_so_far) -> dict with
                       keys: signal ("buy"/"sell"/"hold"), confidence (0-1)
            timestamps: Optional list of timestamps for each bar

        Returns:
            BacktestResult with all metrics
        """
        self.reset()

        # Normalize to OHLCV if just prices given
        bars = self._normalize_data(price_data)

        for i, bar in enumerate(bars):
            self.bar_index = i
            self.current_price = bar["close"]

            # Check stop-losses and take-profits first
            self._check_exits(bar)

            # Get signal
            context = {
                "bar_index": i,
                "price": bar["close"],
                "open": bar.get("open", bar["close"]),
                "high": bar.get("high", bar["close"]),
                "low": bar.get("low", bar["close"]),
                "volume": bar.get("volume", 0),
                "prices": [b["close"] for b in bars[:i + 1]],
            }

            signal_result = signal_fn(context)

            if signal_result:
                self._process_signal(signal_result, bar)

            # Record equity
            equity = self._calculate_equity(bar["close"])
            self.equity_curve.append(equity)

        # Close any open positions at end
        if bars:
            final_price = bars[-1]["close"]
            for pos_id in list(self.positions.keys()):
                self._close_position(pos_id, final_price, "end_of_data")

        # Compute metrics
        result = self._compute_metrics(timestamps)
        return result

    def run_strategy(self, price_data: List[float],
                     strategy_class, strategy_kwargs: Dict = None,
                     timestamps: List = None) -> 'BacktestResult':
        """
        Run backtest using a strategy class (like the real trading strategies).

        Creates a mock core and runs the strategy's analyze() method each bar.
        """
        mock_core = MockCore(self.config.symbol)

        strategy = strategy_class(mock_core, **(strategy_kwargs or {}))

        def signal_fn(context):
            prices = context.get("prices", [])
            mock_core.set_prices(prices)
            return strategy.analyze(context)

        return self.run(price_data, signal_fn, timestamps)

    def _normalize_data(self, data) -> List[Dict]:
        """Normalize input data to list of OHLCV dicts."""
        if not data:
            return []

        # Already OHLCV dicts
        if isinstance(data[0], dict):
            for bar in data:
                if "close" not in bar:
                    bar["close"] = bar.get("price", 0)
            return data

        # Just close prices
        return [{"open": p, "high": p, "low": p, "close": p, "volume": 0}
                for p in data]

    def _process_signal(self, signal: Dict[str, Any], bar: Dict):
        """Process a trading signal."""
        signal_type = signal.get("signal", "hold")
        confidence = signal.get("confidence", 0)

        if signal_type == "hold":
            return

        # Check we don't exceed max positions
        if len(self.positions) >= self.config.max_open_positions:
            # Close existing position if signal flips
            for pos_id, pos in list(self.positions.items()):
                if signal_type == "buy" and pos["side"] == "short":
                    self._close_position(pos_id, bar["close"], "signal_flip")
                elif signal_type == "sell" and pos["side"] == "long":
                    self._close_position(pos_id, bar["close"], "signal_flip")
            return

        if signal_type == "buy":
            if self.cash > 0:
                self._open_position("long", bar)
        elif signal_type == "sell" and self.config.allow_short:
            self._open_position("short", bar)
        elif signal_type == "sell":
            # Close any long positions
            for pos_id, pos in list(self.positions.items()):
                if pos["side"] == "long":
                    self._close_position(pos_id, bar["close"], "sell_signal")

    def _open_position(self, side: str, bar: Dict):
        """Open a new position."""
        # Apply slippage
        if side == "long":
            entry_price = bar["close"] * (1 + self.config.slippage_pct)
        else:
            entry_price = bar["close"] * (1 - self.config.slippage_pct)

        # Calculate position size
        capital_to_use = self.cash * self.config.position_size_pct
        size = capital_to_use / entry_price

        # Deduct commission
        commission = capital_to_use * self.config.commission_pct
        self.cash -= capital_to_use + commission

        pos_id = f"pos_{self.bar_index}_{side}"
        self.positions[pos_id] = {
            "side": side,
            "entry_price": entry_price,
            "size": size,
            "commission": commission,
            "entry_bar": self.bar_index,
            "stop_loss": None,
            "take_profit": None,
        }

        # Set stop-loss / take-profit
        if self.config.stop_loss_pct > 0:
            if side == "long":
                self.positions[pos_id]["stop_loss"] = entry_price * (1 - self.config.stop_loss_pct)
            else:
                self.positions[pos_id]["stop_loss"] = entry_price * (1 + self.config.stop_loss_pct)

        if self.config.take_profit_pct > 0:
            if side == "long":
                self.positions[pos_id]["take_profit"] = entry_price * (1 + self.config.take_profit_pct)
            else:
                self.positions[pos_id]["take_profit"] = entry_price * (1 - self.config.take_profit_pct)

    def _close_position(self, pos_id: str, price: float, reason: str):
        """Close a position."""
        pos = self.positions.pop(pos_id)

        # Apply slippage
        if pos["side"] == "long":
            exit_price = price * (1 - self.config.slippage_pct)
        else:
            exit_price = price * (1 + self.config.slippage_pct)

        # Calculate P&L
        if pos["side"] == "long":
            pnl = (exit_price - pos["entry_price"]) * pos["size"]
        else:
            pnl = (pos["entry_price"] - exit_price) * pos["size"]

        # Deduct exit commission
        exit_commission = exit_price * pos["size"] * self.config.commission_pct
        pnl -= exit_commission + pos["commission"]

        # Return capital to cash
        self.cash += exit_price * pos["size"] - exit_commission

        pnl_pct = pnl / (pos["entry_price"] * pos["size"])

        trade = Trade(
            entry_time=pos["entry_bar"],
            exit_time=self.bar_index,
            side=pos["side"],
            entry_price=pos["entry_price"],
            exit_price=exit_price,
            size=pos["size"],
            commission=pos["commission"] + exit_commission,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason,
        )
        self.closed_trades.append(trade)

    def _check_exits(self, bar: Dict):
        """Check stop-loss and take-profit for all positions."""
        for pos_id, pos in list(self.positions.items()):
            # Check stop-loss
            if pos.get("stop_loss"):
                if pos["side"] == "long" and bar["low"] <= pos["stop_loss"]:
                    self._close_position(pos_id, pos["stop_loss"], "stop_loss")
                    continue
                elif pos["side"] == "short" and bar["high"] >= pos["stop_loss"]:
                    self._close_position(pos_id, pos["stop_loss"], "stop_loss")
                    continue

            # Check take-profit
            if pos.get("take_profit"):
                if pos["side"] == "long" and bar["high"] >= pos["take_profit"]:
                    self._close_position(pos_id, pos["take_profit"], "take_profit")
                    continue
                elif pos["side"] == "short" and bar["low"] <= pos["take_profit"]:
                    self._close_position(pos_id, pos["take_profit"], "take_profit")
                    continue

    def _calculate_equity(self, current_price: float) -> float:
        """Calculate total equity (cash + unrealized P&L)."""
        equity = self.cash
        for pos in self.positions.values():
            if pos["side"] == "long":
                equity += current_price * pos["size"]
            else:
                equity += (2 * pos["entry_price"] - current_price) * pos["size"]
        return equity

    def _compute_metrics(self, timestamps: List = None) -> BacktestResult:
        """Compute all performance metrics."""
        result = BacktestResult(config=self.config)
        result.trades = self.closed_trades
        result.equity_curve = self.equity_curve
        result.timestamps = timestamps or list(range(len(self.equity_curve)))
        result.total_trades = len(self.closed_trades)

        if not self.equity_curve:
            return result

        initial = self.config.initial_capital
        final = self.equity_curve[-1]

        # Total return
        result.total_return_pct = (final - initial) / initial * 100

        # Annualized return (assuming each bar = 1 day)
        n_bars = len(self.equity_curve)
        if n_bars > 1:
            years = n_bars / 365
            result.annualized_return_pct = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Max drawdown
        result.max_drawdown_pct = self._max_drawdown(self.equity_curve)

        # Sharpe ratio (daily)
        if len(self.equity_curve) > 1:
            returns = [(self.equity_curve[i] - self.equity_curve[i - 1]) / self.equity_curve[i - 1]
                       for i in range(1, len(self.equity_curve))]
            result.sharpe_ratio = self._sharpe_ratio(returns, self.config.risk_free_rate)
            result.sortino_ratio = self._sortino_ratio(returns, self.config.risk_free_rate)

        # Trade stats
        if self.closed_trades:
            wins = [t for t in self.closed_trades if t.pnl > 0]
            losses = [t for t in self.closed_trades if t.pnl <= 0]

            result.winning_trades = len(wins)
            result.losing_trades = len(losses)
            result.win_rate = len(wins) / len(self.closed_trades) * 100

            total_profit = sum(t.pnl for t in wins)
            total_loss = abs(sum(t.pnl for t in losses))
            result.profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

            result.avg_win_pct = sum(t.pnl_pct for t in wins) / len(wins) * 100 if wins else 0
            result.avg_loss_pct = sum(t.pnl_pct for t in losses) / len(losses) * 100 if losses else 0

            durations = [t.exit_time - t.entry_time for t in self.closed_trades
                         if t.exit_time is not None]
            result.avg_trade_duration = sum(durations) / len(durations) if durations else 0

            # Expectancy: average $ gained per trade
            result.expectancy = sum(t.pnl for t in self.closed_trades) / len(self.closed_trades)

            # Calmar ratio
            if result.max_drawdown_pct > 0:
                result.calmar_ratio = result.annualized_return_pct / result.max_drawdown_pct

        return result

    def _max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown percentage."""
        if not equity_curve:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.05) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2:
            return 0.0

        daily_rf = risk_free_rate / 365
        excess = [r - daily_rf for r in returns]
        mean = sum(excess) / len(excess)
        std = (sum((x - mean) ** 2 for x in excess) / len(excess)) ** 0.5

        if std == 0:
            return 0.0

        return (mean / std) * (365 ** 0.5)  # Annualize

    def _sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.05) -> float:
        """Calculate annualized Sortino ratio (penalizes downside only)."""
        if len(returns) < 2:
            return 0.0

        daily_rf = risk_free_rate / 365
        excess = [r - daily_rf for r in returns]
        mean = sum(excess) / len(excess)

        downside = [x for x in excess if x < 0]
        if not downside:
            return float("inf")

        downside_std = (sum(x ** 2 for x in downside) / len(downside)) ** 0.5

        if downside_std == 0:
            return 0.0

        return (mean / downside_std) * (365 ** 0.5)


class MockCore:
    """Minimal mock core for backtesting strategies without real network calls."""

    def __init__(self, symbol: str = "BTC/USD"):
        self.symbol = symbol
        self._prices: List[float] = []
        self.max_position_size = 0.1

        # Minimal mocks
        from services.data.data_sources import DataSources
        self.data_sources = _MockDataSources()
        self.tokeninfo_service = _MockTokenInfo()
        self.news_scraper = _MockNewsScraper()
        self.ml_manager = None

    def set_prices(self, prices: List[float]):
        self._prices = prices
        if prices:
            asset = self.symbol.split("/")[0]
            self.tokeninfo_service._prices[asset] = prices[-1]

    def execute_trade(self, **kwargs) -> Dict:
        return {"status": "simulated"}


class _MockTokenInfo:
    def __init__(self):
        self._prices: Dict[str, float] = {}

    def get_token_price(self, symbol: str) -> Optional[float]:
        clean = symbol.replace("/USD", "").replace("USD", "")
        return self._prices.get(clean, 0)

    def get_market_data(self, symbol: str) -> Dict:
        return {}


class _MockDataSources:
    def get_fear_greed_index(self) -> Dict:
        return {"value": 50, "classification": "Neutral"}

    def get_futures_data(self, symbol: str = "ETHUSDT") -> Dict:
        return {"rate": 0.0001, "open_interest": 0, "long_short_ratio": 1.0}


class _MockNewsScraper:
    def get_sentiment_summary(self, symbols=None) -> Dict:
        return {"overall": "neutral", "score": 0}
