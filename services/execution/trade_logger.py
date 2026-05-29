import os
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TradeLogger:
    """
    Thread-safe trade logging with multiple output formats.
    Logs to file, keeps in-memory history, and supports export.
    """

    def __init__(self, log_file: str = "trade_log.jsonl", log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / log_file
        self.trades: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._load_existing()

    def _load_existing(self):
        """Load existing trades from log file."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            self.trades.append(json.loads(line))
                logger.info(f"Loaded {len(self.trades)} existing trades")
            except Exception as e:
                logger.error(f"Failed to load trade log: {e}")

    def log_trade(self, trade: Dict[str, Any]):
        """Log a trade with timestamp."""
        with self._lock:
            # Add metadata
            trade['logged_at'] = time.time()
            trade['logged_at_iso'] = datetime.utcnow().isoformat()

            if 'timestamp' not in trade:
                trade['timestamp'] = trade['logged_at']

            # Append to memory
            self.trades.append(trade)

            # Append to file
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(trade) + '\n')
            except Exception as e:
                logger.error(f"Failed to write trade to log: {e}")

            logger.info(f"Trade logged: {trade.get('side', 'unknown')} {trade.get('amount', 0)} {trade.get('symbol', 'unknown')}")

    def info(self, message: str):
        """Log an info message (for compatibility)."""
        self.log_trade({"type": "info", "message": message})

    def get_trades(self, limit: int = None, exchange: str = None,
                   symbol: str = None, start_time: float = None) -> List[Dict]:
        """Get filtered trade history."""
        with self._lock:
            trades = self.trades.copy()

        # Apply filters
        if exchange:
            trades = [t for t in trades if t.get('exchange') == exchange]
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol]
        if start_time:
            trades = [t for t in trades if t.get('timestamp', 0) >= start_time]

        # Sort by timestamp descending
        trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)

        if limit:
            trades = trades[:limit]

        return trades

    def get_log_dataframe(self):
        """Get trades as a pandas DataFrame."""
        try:
            import pandas as pd
            with self._lock:
                return pd.DataFrame(self.trades)
        except ImportError:
            logger.error("pandas not installed")
            return None

    def get_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """Get trading summary for a period."""
        cutoff = time.time() - (period_hours * 3600)
        recent = [t for t in self.trades if t.get('timestamp', 0) >= cutoff]

        buys = [t for t in recent if t.get('side') == 'buy']
        sells = [t for t in recent if t.get('side') == 'sell']

        return {
            "period_hours": period_hours,
            "total_trades": len(recent),
            "buys": len(buys),
            "sells": len(sells),
            "exchanges": list(set(t.get('exchange') for t in recent if t.get('exchange'))),
            "symbols": list(set(t.get('symbol') for t in recent if t.get('symbol'))),
            "failed": len([t for t in recent if t.get('status') == 'failed']),
        }

    def get_pnl_by_symbol(self) -> Dict[str, Dict[str, float]]:
        """Calculate basic P&L by symbol (requires prices to be accurate)."""
        pnl = {}

        for trade in self.trades:
            symbol = trade.get('symbol')
            if not symbol:
                continue

            if symbol not in pnl:
                pnl[symbol] = {'bought': 0, 'sold': 0, 'buy_value': 0, 'sell_value': 0}

            amount = float(trade.get('amount', 0))
            price = float(trade.get('price', 0)) or float(trade.get('avg_execution_price', 0))

            if trade.get('side') == 'buy':
                pnl[symbol]['bought'] += amount
                pnl[symbol]['buy_value'] += amount * price
            elif trade.get('side') == 'sell':
                pnl[symbol]['sold'] += amount
                pnl[symbol]['sell_value'] += amount * price

        # Calculate realized P&L
        for symbol in pnl:
            sold = pnl[symbol]['sold']
            if sold > 0:
                avg_buy = pnl[symbol]['buy_value'] / pnl[symbol]['bought'] if pnl[symbol]['bought'] > 0 else 0
                avg_sell = pnl[symbol]['sell_value'] / sold if sold > 0 else 0
                pnl[symbol]['realized_pnl'] = (avg_sell - avg_buy) * sold
            else:
                pnl[symbol]['realized_pnl'] = 0

        return pnl

    def export_csv(self, filepath: str):
        """Export trades to CSV."""
        df = self.get_log_dataframe()
        if df is not None:
            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(df)} trades to {filepath}")

    def export_json(self, filepath: str):
        """Export trades to JSON."""
        with self._lock:
            with open(filepath, 'w') as f:
                json.dump(self.trades, f, indent=2)
        logger.info(f"Exported {len(self.trades)} trades to {filepath}")

    def clear(self, backup: bool = True):
        """Clear trade history."""
        with self._lock:
            if backup and self.trades:
                backup_file = self.log_dir / f"trade_log_backup_{int(time.time())}.jsonl"
                with open(backup_file, 'w') as f:
                    for trade in self.trades:
                        f.write(json.dumps(trade) + '\n')
                logger.info(f"Backed up {len(self.trades)} trades to {backup_file}")

            self.trades = []
            if self.log_file.exists():
                self.log_file.unlink()
            logger.info("Trade log cleared")
