import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class BorgCore:
    """
    Core orchestrator for BorgGodTrader.
    Initializes and manages all trading services, executors, and strategies.
    """

    def __init__(self, config: Dict[str, Any] = None):
        load_dotenv()

        self.config = config or {}
        self._load_config_from_env()
        self._init_logging()

        # Initialize services in correct order
        self._init_data_services()
        self._init_executors()
        self._init_portfolio_services()
        self._init_strategy_services()
        self._init_risk_services()
        self._init_monitoring_services()
        self._init_notification_services()

        self.liquidation_events = []
        logger.info("BorgCore initialized successfully")

    def _load_config_from_env(self):
        """Load configuration from environment."""
        self.rpc_url = os.getenv("ETH_RPC_URL")
        self.private_key = os.getenv("ETH_PRIVATE_KEY")
        self.wallet_address = os.getenv("ETH_WALLET_ADDRESS")
        self.trading_mode = os.getenv("TRADING_MODE", "paper")

        # Risk settings
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
        self.max_drawdown = float(os.getenv("MAX_DRAWDOWN", "0.15"))
        self.default_slippage = float(os.getenv("DEFAULT_SLIPPAGE", "0.005"))

    def _init_logging(self):
        """Initialize logging."""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("BorgCore")

    def _init_data_services(self):
        """Initialize data services."""
        from services.tokeninfo import TokenInfoService
        from services.news.news_scraper import NewsScraper
        from services.data.data_sources import DataSources
        from services.chains.chain_registry import ChainRegistry

        self.tokeninfo_service = TokenInfoService(self.rpc_url)
        self.news_scraper = NewsScraper()
        self.data_sources = DataSources()
        self.chain_registry = ChainRegistry()

        # Data pipeline (optional, for advanced features)
        try:
            from services.data.data_pipeline import DataPipeline
            self.data_pipeline = DataPipeline(self.config, self.tokeninfo_service.erc20_abi)
        except Exception as e:
            logger.warning(f"DataPipeline init failed: {e}")
            self.data_pipeline = None

    def _init_executors(self):
        """Initialize exchange executors."""
        from services.execution.trade_logger import TradeLogger
        from services.execution.kraken_executor import KrakenExecutor
        from services.execution.gemini_executor import GeminiExecutor
        from services.execution.cex_executor import CEXExecutor
        from services.execution.defi_executor import DeFiExecutor
        from services.execution.smart_order_router import SmartOrderRouter

        self.trade_logger = TradeLogger()

        # Paper trading mode check
        is_paper = self.trading_mode == "paper"
        if is_paper:
            logger.info("Running in PAPER TRADING mode")

        # Initialize executors
        self.kraken_executor = KrakenExecutor(logger_service=self.trade_logger)
        self.gemini_executor = GeminiExecutor(logger_service=self.trade_logger)
        self.cex_executor = CEXExecutor(trade_logger=self.trade_logger, paper_mode=is_paper)
        self.defi_executor = DeFiExecutor(
            private_key=self.private_key,
            wallet_address=self.wallet_address,
            logger=self.trade_logger,
            rpc_url=self.rpc_url
        )

        # Smart order router
        self.smart_order_router = SmartOrderRouter({
            "kraken": self.kraken_executor,
            "gemini": self.gemini_executor,
            "cex": self.cex_executor,
            "defi": self.defi_executor,
        })

    def _init_portfolio_services(self):
        """Initialize portfolio services."""
        from services.portfolio import PortfolioService

        self.portfolio_service = PortfolioService(
            self.wallet_address or "",
            self.rpc_url
        )

    def _init_strategy_services(self):
        """Initialize strategy and ML services."""
        from services.strategies.strategy_manager import StrategyManager
        from services.strategies.auto_strategy_generator import AutoStrategyGenerator
        from services.ml.advanced_ml_manager import AdvancedMLManager

        self.strategy_manager = StrategyManager(self)

        # Auto strategy generator
        try:
            self.auto_strategy_gen = AutoStrategyGenerator(
                backtester=getattr(self.strategy_manager, 'backtester', None),
                strategy_templates=getattr(self.strategy_manager, 'strategy_templates', {})
            )
        except Exception as e:
            logger.warning(f"AutoStrategyGenerator init failed: {e}")
            self.auto_strategy_gen = None

        # ML manager
        try:
            self.ml_manager = AdvancedMLManager()
        except Exception as e:
            logger.warning(f"MLManager init failed: {e}")
            self.ml_manager = None

    def _init_risk_services(self):
        """Initialize risk management services."""
        from services.risk.position_manager import PositionManager
        from services.risk.risk_engine import RiskEngine

        self.position_manager = PositionManager(
            self.portfolio_service,
            {
                "max_drawdown": self.max_drawdown,
                "max_pos_size": self.max_position_size
            }
        )
        self.risk_engine = RiskEngine()

        # Margin services
        try:
            from services.margin.margin_manager import MarginManager
            from services.margin.interest_tracker import InterestTracker
            from services.margin.liquidation_monitor import LiquidationMonitor

            self.interest_tracker = InterestTracker()
            self.margin_manager = MarginManager(
                self.cex_executor,
                self.portfolio_service,
                self.interest_tracker
            )
            self.liquidation_monitor = LiquidationMonitor(
                self.margin_manager,
                self.portfolio_service,
                threshold=1.15,
                poll_interval=30,
                on_liquidation_risk=self._handle_liquidation_risk,
                dashboard_callback=self._dashboard_liquidation_callback
            )
        except Exception as e:
            logger.warning(f"Margin services init failed: {e}")
            self.margin_manager = None
            self.liquidation_monitor = None

    def _init_monitoring_services(self):
        """Initialize monitoring services."""
        from services.monitoring.anomaly_detection import AnomalyDetector
        from services.monitoring.log_audit import AuditLogger
        from services.automation.strategy_scheduler import StrategyScheduler

        self.anomaly_detector = AnomalyDetector()
        self.audit_logger = AuditLogger()

        # Strategy scheduler
        strategies = getattr(self.strategy_manager, 'strategies', {})
        self.strategy_scheduler = StrategyScheduler(strategies)

        # Plugin loader
        try:
            from services.plugins.plugin_loader import PluginLoader
            self.plugin_loader = PluginLoader()
            self.plugin_loader.load_plugins()
        except Exception as e:
            logger.warning(f"Plugin loader init failed: {e}")
            self.plugin_loader = None

        # Security services
        try:
            from services.security.allowance_audit import AllowanceAuditor
            self.allowance_auditor = AllowanceAuditor(
                self.rpc_url,
                self.wallet_address,
                self.tokeninfo_service.erc20_abi
            )
        except Exception as e:
            logger.warning(f"AllowanceAuditor init failed: {e}")
            self.allowance_auditor = None

    def _init_notification_services(self):
        """Initialize notification services."""
        try:
            from services.notification.alert_manager import AlertManager
            self.alert_manager = AlertManager()
        except Exception as e:
            logger.warning(f"AlertManager init failed: {e}")
            self.alert_manager = None

    def _handle_liquidation_risk(self, symbol: str, margin_ratio: float):
        """Handle liquidation risk callback."""
        msg = f"LIQUIDATION RISK: {symbol} margin ratio at {margin_ratio:.2%}"
        self.liquidation_events.append({
            "symbol": symbol,
            "margin_ratio": margin_ratio,
            "message": msg,
            "timestamp": __import__('time').time()
        })

        if self.alert_manager:
            self.alert_manager.send_telegram(msg)
            self.alert_manager.send_discord(msg)

        if self.margin_manager:
            self.margin_manager.auto_liquidate(symbol)

    def _dashboard_liquidation_callback(self, symbol: str, margin_ratio: float, msg: str):
        """Dashboard liquidation callback."""
        self.liquidation_events.append({
            "symbol": symbol,
            "margin_ratio": margin_ratio,
            "message": msg,
            "timestamp": __import__('time').time()
        })

    def get_executors(self) -> Dict[str, Any]:
        """Get all available executors."""
        return {
            "kraken": self.kraken_executor,
            "gemini": self.gemini_executor,
            "cex": self.cex_executor,
            "defi": self.defi_executor,
        }

    def get_services(self) -> Dict[str, Any]:
        """Get all available services."""
        return {
            "portfolio": self.portfolio_service,
            "tokeninfo": self.tokeninfo_service,
            "strategy": self.strategy_manager,
            "ml_manager": self.ml_manager,
            "auto_strategy_gen": self.auto_strategy_gen,
            "order_router": self.smart_order_router,
            "risk": self.position_manager,
            "anomaly": self.anomaly_detector,
            "scheduler": self.strategy_scheduler,
            "plugin": self.plugin_loader,
            "audit": self.audit_logger,
            "news": self.news_scraper,
            "margin_manager": self.margin_manager,
            "data_sources": self.data_sources,
            "alert_manager": self.alert_manager,
        }

    def news(self, symbols: list = None) -> list:
        """Get latest news."""
        return self.news_scraper.fetch_latest(symbols)

    def execute_trade(self, symbol: str, side: str, amount: float,
                      exchange: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a trade via smart order routing.

        Args:
            symbol: Trading pair (e.g., "BTC/USD")
            side: "buy" or "sell"
            amount: Order amount
            exchange: Specific exchange (optional, auto-routes if not specified)
        """
        return self.smart_order_router.route_order(
            symbol=symbol,
            side=side,
            amount=amount,
            preferred_exchange=exchange,
            **kwargs
        )

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        return self.portfolio_service.get_portfolio_overview(self.tokeninfo_service)

    def health_check(self) -> Dict[str, Any]:
        """Check health of all services."""
        return {
            "exchanges": self.smart_order_router.health_check(),
            "defi_connected": self.defi_executor.is_connected(),
            "trading_mode": self.trading_mode,
        }


# Alias for backwards compatibility
BorgGodCore = BorgCore
