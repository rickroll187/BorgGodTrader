from services.margin.margin_manager import MarginManager
from services.margin.interest_tracker import InterestTracker
from services.margin.liquidation_monitor import LiquidationMonitor
from dashboard.margin_dashboard import margin_dashboard

# Assume you have broker and portfolio_service objects already
broker = ...  # Must have .borrow() and .repay() methods
portfolio_service = ...  # Must have .get_margin_ratio(symbol) method

interest_tracker = InterestTracker()
margin_manager = MarginManager(broker, portfolio_service, interest_tracker)

liquidation_events = []

def on_liq(symbol, margin_ratio):
    msg = f"Auto-liquidation triggered for {symbol}! Margin ratio: {margin_ratio}"
    liquidation_events.append(msg)
    margin_manager.auto_liquidate(symbol)

def dashboard_callback(symbol, margin_ratio, msg):
    liquidation_events.append(msg)

liquidation_monitor = LiquidationMonitor(
    margin_manager,
    portfolio_service,
    threshold=1.15,
    poll_interval=30,
    on_liquidation_risk=on_liq,
    dashboard_callback=dashboard_callback
)
liquidation_monitor.daemon = True
liquidation_monitor.start()

# For Streamlit dashboard (margin_dashboard), call in your main app:
# margin_dashboard(margin_manager, interest_tracker, liquidation_events)