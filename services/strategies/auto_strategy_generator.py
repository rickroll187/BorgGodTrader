import random
import json

class AutoStrategyGenerator:
    """
    Evolves and generates trading strategies using parameter sweeps or genetic programming.
    """
    def __init__(self, backtester, strategy_templates, results_file="generated_strategies.jsonl"):
        self.backtester = backtester
        self.strategy_templates = strategy_templates
        self.results_file = results_file

    def random_parameters(self, param_space):
        return {k: random.choice(v) for k, v in param_space.items()}

    def generate_and_test(self, n=20):
        results = []
        for _ in range(n):
            template = random.choice(self.strategy_templates)
            params = self.random_parameters(template["param_space"])
            strat = template["builder"](params)
            perf = self.backtester.backtest(strat)
            result = {"params": params, "performance": perf}
            results.append(result)
            with open(self.results_file, "a") as f:
                f.write(json.dumps(result) + "\n")
        return sorted(results, key=lambda x: x["performance"]["sharpe"], reverse=True)

    def top_strategies(self, top_n=5):
        strategies = []
        try:
            with open(self.results_file) as f:
                for line in f:
                    strategies.append(json.loads(line))
        except Exception:
            pass
        return sorted(strategies, key=lambda x: x["performance"]["sharpe"], reverse=True)[:top_n]