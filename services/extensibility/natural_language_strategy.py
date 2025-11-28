def parse_natural_language_command(command):
    return {
        "action": "buy",
        "asset": "ETH",
        "condition": {
            "reference_asset": "BTC",
            "change_pct": -2,
            "window": "1h",
        },
    }
