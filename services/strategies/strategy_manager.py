import os
import importlib
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Manages trading strategies - loading, running, and monitoring.
    """

    def __init__(self, core):
        self.core = core
        self.strategies: Dict[str, Any] = {}
        self.strategy_templates: Dict[str, type] = {}
        self.backtester = None
        self._load_strategies()

    def _load_strategies(self):
        """Dynamically load strategy classes from the strategies directory."""
        strategy_dir = os.path.dirname(__file__)

        for fname in os.listdir(strategy_dir):
            if fname.startswith("strategy_") and fname.endswith(".py"):
                module_name = fname[:-3]  # Remove .py
                try:
                    mod = importlib.import_module(f"services.strategies.{module_name}")
                    if hasattr(mod, "Strategy"):
                        strategy_name = module_name.replace("strategy_", "")
                        strategy_class = mod.Strategy
                        self.strategy_templates[strategy_name] = strategy_class
                        self.strategies[strategy_name] = strategy_class(self.core)
                        logger.info(f"Loaded strategy: {strategy_name}")
                except Exception as e:
                    logger.warning(f"Failed to load strategy {fname}: {e}")

        logger.info(f"Loaded {len(self.strategies)} strategies")

    def get_strategy(self, name: str) -> Optional[Any]:
        """Get a strategy by name."""
        return self.strategies.get(name)

    def list_strategies(self) -> List[str]:
        """List all available strategies."""
        return list(self.strategies.keys())

    def run_strategy(self, name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a specific strategy."""
        strategy = self.strategies.get(name)
        if not strategy:
            return {"error": f"Strategy '{name}' not found"}

        try:
            result = strategy.run(context or {})
            return {"status": "success", "strategy": name, "result": result}
        except Exception as e:
            logger.error(f"Strategy {name} failed: {e}")
            return {"status": "error", "strategy": name, "error": str(e)}

    def run_all(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run all enabled strategies."""
        results = {}
        for name, strategy in self.strategies.items():
            if getattr(strategy, 'enabled', True):
                results[name] = self.run_strategy(name, context)
        return results

    def enable_strategy(self, name: str):
        """Enable a strategy."""
        if name in self.strategies:
            self.strategies[name].enabled = True
            logger.info(f"Enabled strategy: {name}")

    def disable_strategy(self, name: str):
        """Disable a strategy."""
        if name in self.strategies:
            self.strategies[name].enabled = False
            logger.info(f"Disabled strategy: {name}")

    def get_strategy_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all strategies."""
        status = {}
        for name, strategy in self.strategies.items():
            status[name] = {
                "enabled": getattr(strategy, 'enabled', True),
                "last_run": getattr(strategy, 'last_run', None),
                "last_signal": getattr(strategy, 'last_signal', None),
            }
        return status

    def add_strategy(self, name: str, strategy_instance):
        """Add a custom strategy instance."""
        self.strategies[name] = strategy_instance
        logger.info(f"Added custom strategy: {name}")

    def remove_strategy(self, name: str):
        """Remove a strategy."""
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"Removed strategy: {name}")
