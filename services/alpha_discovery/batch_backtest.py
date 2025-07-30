import concurrent.futures

def backtest_strategy(strategy, market_data):
    """
    Backtest a strategy on given market data. Should be fast and pure.
    Returns result dict.
    """
    try:
        result = strategy.backtest(market_data)
        return result
    except Exception as e:
        return {"error": str(e), "strategy": str(strategy)}

def run_batch_backtests(strategies, market_data, workers=8):
    """
    Runs backtests in parallel threads for speed.
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(backtest_strategy, s, market_data) for s in strategies]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return results