import importlib
import os

class StrategyManager:
    def __init__(self, core):
        self.core = core
        self.strategies = {}
        self.strategy_templates = {}
        self.backtester = None
        self._load_strategies()

    def _load_strategies(self):
        strategy_dir = os.path.dirname(__file__)
        for fname in os.listdir(strategy_dir):
            if fname.startswith("strategy_") and fname.endswith(".py"):
                module_name = f"services.strategies.{fname[:-3]}"
                mod = importlib.import_module(module_name)
                if hasattr(mod, "Strategy"):
                    self.strategies[fname[9:-3]] = mod.Strategy(self.core)

    def run_all(self, context):
        for name, strat in self.strategies.items():
            strat.run(context)

    def get_strategy(self, name):
        return self.strategies.get(name)
