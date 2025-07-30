# BorgGodTrader Bot

## Structure

- `dashboard/app.py` — Main Streamlit dashboard
- `services/strategy/` — All strategies (MA, sniper, scalping, DeFi, ML)
- `services/news/news_scraper.py` — Simulated news data (replace with real)
- `services/ml/feature_engineering.py` — Adds technical indicator columns

## How To Run

```bash
streamlit run dashboard/app.py
```

## What To Edit

- Add your real data feeds in `fetch_combined_news` or `get_price_data`.
- Expand or tune strategy logic in `services/strategy/`.
- The ML strategy will learn from its own trades and retrain as needed.