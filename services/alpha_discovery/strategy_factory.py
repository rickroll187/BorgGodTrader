import itertools
from typing import Dict, List, Type, Iterator

class StrategyFactory:
    """
    Generates and parameterizes strategies for automated alpha discovery.
    """
    def __init__(self, strategy_classes: List[Type]):
        self.strategy_classes = strategy_classes

    def generate_strategies(self, param_grid: Dict, strategy_class=None) -> Iterator:
        """
        Given a param grid (dict: param -> list of values), yield instantiated strategies with all param combinations.
        If strategy_class is None, use all registered classes.
        """
        keys, values = zip(*param_grid.items())
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            if strategy_class is not None:
                yield strategy_class(**params)
            else:
                for strat_cls in self.strategy_classes:
                    yield strat_cls(**params)