import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def parse_natural_language_command(command: str) -> Dict[str, Any]:
    """
    Parse natural language trading commands into structured actions.

    Examples:
    - "buy 0.1 ETH when BTC drops 2%"
    - "sell half my BTC if price above 70000"
    - "set stop loss at 65000 for BTC"
    - "what's my portfolio balance"

    Returns structured dict with action, asset, conditions, etc.
    """
    command = command.lower().strip()

    # Try each parser in order
    parsers = [
        _parse_buy_sell_command,
        _parse_stop_loss_command,
        _parse_take_profit_command,
        _parse_query_command,
        _parse_condition_command,
    ]

    for parser in parsers:
        result = parser(command)
        if result:
            return result

    # Default fallback - couldn't parse
    return {
        "action": "unknown",
        "raw_command": command,
        "parsed": False,
        "suggestion": "Try: 'buy 0.1 ETH' or 'sell 100 USDC worth of BTC'"
    }


def _parse_buy_sell_command(command: str) -> Optional[Dict[str, Any]]:
    """Parse buy/sell commands."""

    # Pattern: buy/sell [amount] [asset] [conditions]
    buy_pattern = r'^(buy|long)\s+(\d+\.?\d*)\s+(\w+)'
    sell_pattern = r'^(sell|short)\s+(\d+\.?\d*)\s+(\w+)'

    # Try buy pattern
    match = re.search(buy_pattern, command)
    if match:
        return _build_trade_action("buy", match, command)

    # Try sell pattern
    match = re.search(sell_pattern, command)
    if match:
        return _build_trade_action("sell", match, command)

    # Pattern: buy/sell [amount] worth of [asset]
    worth_pattern = r'^(buy|sell)\s+(\d+\.?\d*)\s+(usd|usdc|usdt)?\s*worth\s+of\s+(\w+)'
    match = re.search(worth_pattern, command)
    if match:
        action = match.group(1)
        amount_usd = float(match.group(2))
        asset = match.group(4).upper()
        return {
            "action": action,
            "asset": asset,
            "amount_usd": amount_usd,
            "amount_type": "notional",
            "parsed": True,
            "conditions": _extract_conditions(command),
        }

    return None


def _build_trade_action(action: str, match, command: str) -> Dict[str, Any]:
    """Build trade action from regex match."""
    amount = float(match.group(2))
    asset = match.group(3).upper()

    return {
        "action": action,
        "asset": asset,
        "amount": amount,
        "amount_type": "units",
        "parsed": True,
        "conditions": _extract_conditions(command),
    }


def _extract_conditions(command: str) -> Dict[str, Any]:
    """Extract conditional triggers from command."""
    conditions = {}

    # When price drops/rises X%
    pct_pattern = r'when\s+(\w+)\s+(drops?|falls?|rises?|gains?)\s+(\d+\.?\d*)%'
    match = re.search(pct_pattern, command)
    if match:
        ref_asset = match.group(1).upper()
        direction = match.group(2)
        pct = float(match.group(3))
        conditions["reference_asset"] = ref_asset
        conditions["direction"] = "down" if direction in ("drop", "drops", "fall", "falls") else "up"
        conditions["change_pct"] = pct if conditions["direction"] == "up" else -pct

    # If price above/below X
    price_pattern = r'(if|when)\s+price\s+(above|below|at)\s+(\d+\.?\d*)'
    match = re.search(price_pattern, command)
    if match:
        direction = match.group(2)
        price = float(match.group(3))
        conditions["trigger_price"] = price
        conditions["trigger_direction"] = direction

    # Time window
    time_pattern = r'in\s+(the\s+)?(next\s+)?(\d+)\s*(h|hour|m|min|minute|d|day)'
    match = re.search(time_pattern, command)
    if match:
        amount = int(match.group(3))
        unit = match.group(4)[0]
        multiplier = {"h": 3600, "m": 60, "d": 86400}
        conditions["window_seconds"] = amount * multiplier.get(unit, 3600)

    return conditions


def _parse_stop_loss_command(command: str) -> Optional[Dict[str, Any]]:
    """Parse stop loss commands."""
    pattern = r'(set\s+)?stop\s*loss\s+(at\s+)?(\d+\.?\d*)\s*(for\s+)?(\w+)?'
    match = re.search(pattern, command)

    if match:
        price = float(match.group(3))
        asset = match.group(5).upper() if match.group(5) else None

        return {
            "action": "set_stop_loss",
            "price": price,
            "asset": asset,
            "parsed": True,
        }
    return None


def _parse_take_profit_command(command: str) -> Optional[Dict[str, Any]]:
    """Parse take profit commands."""
    pattern = r'(set\s+)?take\s*profit\s+(at\s+)?(\d+\.?\d*)\s*(for\s+)?(\w+)?'
    match = re.search(pattern, command)

    if match:
        price = float(match.group(3))
        asset = match.group(5).upper() if match.group(5) else None

        return {
            "action": "set_take_profit",
            "price": price,
            "asset": asset,
            "parsed": True,
        }
    return None


def _parse_query_command(command: str) -> Optional[Dict[str, Any]]:
    """Parse query/information commands."""

    queries = {
        r'(what|show|get).*(balance|portfolio|holdings)': "get_portfolio",
        r'(what|show|get).*(price|worth|value)\s+of\s+(\w+)': "get_price",
        r'(what|show|get).*(open|active)\s*(positions?|orders?)': "get_positions",
        r'(what|show|get).*pnl|profit|loss': "get_pnl",
        r'how\s+much\s+(\w+)\s+do\s+i\s+have': "get_balance",
    }

    for pattern, action in queries.items():
        match = re.search(pattern, command)
        if match:
            # Extract asset if present
            asset_match = re.search(r'of\s+(\w+)', command)
            asset = asset_match.group(1).upper() if asset_match else None

            return {
                "action": action,
                "asset": asset,
                "parsed": True,
            }

    return None


def _parse_condition_command(command: str) -> Optional[Dict[str, Any]]:
    """Parse conditional/alert commands."""

    # Alert me when X
    alert_pattern = r'alert\s+(me\s+)?(when|if)\s+(\w+)\s+(reaches?|hits?|crosses?)\s+(\d+\.?\d*)'
    match = re.search(alert_pattern, command)

    if match:
        asset = match.group(3).upper()
        price = float(match.group(5))

        return {
            "action": "set_alert",
            "asset": asset,
            "trigger_price": price,
            "parsed": True,
        }

    return None


# Convenience function for executing parsed commands
def execute_parsed_command(parsed: Dict[str, Any], core) -> Dict[str, Any]:
    """
    Execute a parsed natural language command using the core instance.
    """
    action = parsed.get("action")

    if action == "buy":
        return core.execute_trade(
            symbol=f"{parsed['asset']}/USD",
            side="buy",
            amount=parsed.get("amount", 0)
        )
    elif action == "sell":
        return core.execute_trade(
            symbol=f"{parsed['asset']}/USD",
            side="sell",
            amount=parsed.get("amount", 0)
        )
    elif action == "get_portfolio":
        return core.get_portfolio_summary()
    elif action == "get_price":
        price = core.tokeninfo_service.get_token_price(parsed.get("asset"))
        return {"asset": parsed.get("asset"), "price": price}
    elif action == "get_positions":
        return {"positions": core.position_manager.get_positions()}

    return {"error": "Action not implemented", "parsed": parsed}
