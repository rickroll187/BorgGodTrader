import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class StrategyScheduler:
    """
    Schedules and runs strategies at specified intervals.
    Supports cron-like scheduling and event-based triggers.
    """

    def __init__(self, strategies: Dict[str, Any] = None):
        self.strategies = strategies or {}
        self.schedules: Dict[str, Dict] = {}
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def add_schedule(self, strategy_name: str, interval_seconds: int,
                     enabled: bool = True, context: Dict = None):
        """Add a strategy to the schedule."""
        self.schedules[strategy_name] = {
            "interval": interval_seconds,
            "enabled": enabled,
            "context": context or {},
            "last_run": 0,
            "run_count": 0,
            "errors": 0,
        }
        logger.info(f"Scheduled {strategy_name} every {interval_seconds}s")

    def remove_schedule(self, strategy_name: str):
        """Remove a strategy from the schedule."""
        self.schedules.pop(strategy_name, None)

    def enable_schedule(self, strategy_name: str):
        """Enable a scheduled strategy."""
        if strategy_name in self.schedules:
            self.schedules[strategy_name]["enabled"] = True

    def disable_schedule(self, strategy_name: str):
        """Disable a scheduled strategy."""
        if strategy_name in self.schedules:
            self.schedules[strategy_name]["enabled"] = False

    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Strategy scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Strategy scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop."""
        while self.running and not self._stop_event.is_set():
            now = time.time()

            for name, schedule in self.schedules.items():
                if not schedule["enabled"]:
                    continue

                elapsed = now - schedule["last_run"]
                if elapsed >= schedule["interval"]:
                    self._execute_strategy(name, schedule)
                    schedule["last_run"] = now

            # Sleep for a bit before checking again
            self._stop_event.wait(timeout=1)

    def _execute_strategy(self, name: str, schedule: Dict):
        """Execute a scheduled strategy."""
        strategy = self.strategies.get(name)
        if not strategy:
            logger.warning(f"Strategy {name} not found")
            return

        try:
            context = schedule.get("context", {})
            context["scheduled"] = True
            context["run_number"] = schedule["run_count"] + 1

            if hasattr(strategy, "run"):
                strategy.run(context)

            schedule["run_count"] += 1
            logger.debug(f"Executed scheduled strategy: {name}")

        except Exception as e:
            schedule["errors"] += 1
            logger.error(f"Scheduled strategy {name} failed: {e}")

    def run_now(self, strategy_name: str, context: Dict = None) -> Dict[str, Any]:
        """Manually trigger a strategy to run immediately."""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return {"error": f"Strategy {strategy_name} not found"}

        try:
            if hasattr(strategy, "run"):
                result = strategy.run(context or {})
                return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return {"status": "unknown"}

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self.running,
            "schedules": {
                name: {
                    "interval": s["interval"],
                    "enabled": s["enabled"],
                    "last_run": s["last_run"],
                    "run_count": s["run_count"],
                    "errors": s["errors"],
                    "next_run": s["last_run"] + s["interval"] if s["last_run"] else 0,
                }
                for name, s in self.schedules.items()
            }
        }

    def update_strategies(self, strategies: Dict[str, Any]):
        """Update the strategies dictionary."""
        self.strategies = strategies
