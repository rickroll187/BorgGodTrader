# 🤖 BorgGodTrader

**Assimilate. Adapt. Advance.**

A modular crypto trading bot with ML-powered strategies, multi-exchange support, and real-time DeFi integration.

## Features

- **Multi-Exchange Support**: Kraken, Gemini, and generic CEX integration
- **DeFi Trading**: Direct Uniswap V3 swaps via Web3
- **Smart Order Routing**: Automatically finds best execution across venues
- **ML Strategies**: Ensemble models with drift detection and auto-retraining
- **Risk Management**: Position limits, stop-loss, drawdown protection
- **Real-Time Data**: Fear & Greed Index, funding rates, orderbook imbalance
- **Natural Language Commands**: "buy 0.1 ETH when BTC drops 5%"
- **Paper Trading**: Full simulation mode for testing strategies
- **Dashboard**: Streamlit-based UI for monitoring and manual trading

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Launch Dashboard

```bash
python launch_dashboard.py
```

Or run directly:
```bash
streamlit run main.py
```

### 4. Docker (Optional)

```bash
docker-compose up -d
```

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `TRADING_MODE` | `paper` for simulation, `live` for real trading |
| `ETH_RPC_URL` | Ethereum RPC endpoint (Infura, Alchemy, etc.) |
| `ETH_PRIVATE_KEY` | Wallet private key for DeFi trades |
| `KRAKEN_API_KEY` | Kraken API credentials |
| `GEMINI_API_KEY` | Gemini API credentials |
| `MAX_POSITION_SIZE` | Max position as % of portfolio (0.1 = 10%) |
| `MAX_DRAWDOWN` | Max drawdown before auto-stop (0.15 = 15%) |

## Architecture

```
BorgGodTrader/
├── main.py                 # Entry point
├── services/
│   ├── core.py            # Main orchestrator
│   ├── execution/         # Exchange executors
│   │   ├── kraken_executor.py
│   │   ├── gemini_executor.py
│   │   ├── defi_executor.py
│   │   └── smart_order_router.py
│   ├── strategies/        # Trading strategies
│   ├── ml/               # ML models and training
│   ├── risk/             # Risk management
│   ├── data/             # Data sources
│   └── monitoring/       # Anomaly detection, logging
├── dashboard/            # Streamlit UI
└── tests/               # Test suite
```

## Usage Examples

### Manual Trading (Dashboard)
1. Navigate to "Trade" tab
2. Select asset, amount, and exchange
3. Click "Execute Trade"

### Natural Language
```
buy 0.1 ETH
sell 100 USDC worth of BTC
set stop loss at 65000 for BTC
what's my portfolio balance
```

### Programmatic
```python
from services.core import BorgCore

core = BorgCore()

# Execute trade
result = core.execute_trade("BTC/USD", "buy", 0.01)

# Get portfolio
portfolio = core.get_portfolio_summary()

# Check prices
price = core.tokeninfo_service.get_token_price("ETH")
```

## Risk Warning

⚠️ **IMPORTANT**: Trading cryptocurrencies involves significant risk. This software is provided as-is with no guarantees. Always:

1. Start with paper trading mode
2. Use small position sizes
3. Set appropriate stop-losses
4. Never invest more than you can afford to lose
5. Review all trades before execution

## Development

### Running Tests
```bash
python -m pytest tests/ -v
```

### Adding a New Strategy
1. Create `services/strategies/strategy_mystrategy.py`
2. Implement `Strategy` class with `run()` and `analyze()` methods
3. Strategy auto-loads on restart

## License

MIT License - See LICENSE file

## Credits

Created by Chemothearpy/Eviscerate
