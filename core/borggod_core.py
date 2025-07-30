import logging
from services.execution.cex_executor import CEXExecutor
from services.execution.defi_executor import DeFiExecutor
from services.execution.kraken_executor import KrakenExecutor
from services.execution.gemini_executor import GeminiExecutor
from services.execution.trade_logger import TradeLogger
from services.portfolio import PortfolioService
from services.tokeninfo import TokenInfoService
from services.strategies.strategy_manager import StrategyManager
from services.strategies.auto_strategy_generator import AutoStrategyGenerator
from services.news.news_scraper import NewsScraper
from services.ml.advanced_feature_engineering import AdvancedFeatureEngineer
from services.ml.model_ensemble import ModelEnsembler
from services.ml.advanced_ml_manager import AdvancedMLManager
from services.execution.smart_order_router import SmartOrderRouter
from services.risk.position_manager import PositionManager
from services.monitoring.anomaly_detection import AnomalyDetector
from services.automation.strategy_scheduler import StrategyScheduler
from services.plugins.plugin_loader import PluginLoader
from services.monitoring.log_audit import AuditLogger
from services.security.allowance_audit import AllowanceAuditor
from services.extensibility.natural_language_strategy import parse_natural_language_command
from services.margin.margin_manager import MarginManager
from services.margin.interest_tracker import InterestTracker
from services.margin.liquidation_monitor import LiquidationMonitor
from services.chains.chain_registry import ChainRegistry

class BorgGodCore:
    def __init__(self, config):
        import os
        import dotenv
        dotenv.load_dotenv()
        self.config = config

        # Core credentials and services
        self.rpc_url = os.getenv("ETH_RPC_URL")
        self.private_key = os.getenv("ETH_PRIVATE_KEY")
        self.wallet_address = os.getenv("ETH_WALLET_ADDRESS")
        self.cex_api_key = os.getenv("CEX_API_KEY")
        self.cex_api_secret = os.getenv("CEX_API_SECRET")
        self.kraken_api_key = os.getenv("KRAKEN_API_KEY")
        self.kraken_api_secret = os.getenv("KRAKEN_API_SECRET")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_api_secret = os.getenv("GEMINI_API_SECRET")

        # Data connectors
        self.news_scraper = NewsScraper()
        self.tokeninfo_service = TokenInfoService(self.rpc_url)
        self.chain_registry = ChainRegistry()

        # Trading executors
        self.trade_logger = TradeLogger(log_file="trade_log.txt")
        self.defi_executor = DeFiExecutor(
            self.chain_registry, self.private_key, self.wallet_address, logger=self.trade_logger
        )
        self.cex_executor = CEXExecutor(self.cex_api_key, self.cex_api_secret, logger=self.trade_logger)
        self.kraken_executor = KrakenExecutor(self.kraken_api_key, self.kraken_api_secret, logger=self.trade_logger)
        self.gemini_executor = GeminiExecutor(self.gemini_api_key, self.gemini_api_secret, logger=self.trade_logger)

        # Core portfolio/risk
        self.portfolio_service = PortfolioService(self.wallet_address, self.rpc_url)
        self.position_manager = PositionManager(self.portfolio_service, {"max_drawdown": 0.15, "max_pos_size": 0.2})

        # Strategy/ML/Auto
        self.strategy_manager = StrategyManager(self)
        self.feature_engineer = AdvancedFeatureEngineer()
        self.model_ensembler = ModelEnsembler({})
        self.ml_manager = AdvancedMLManager()
        self.auto_strategy_gen = AutoStrategyGenerator(
            backtester=self.strategy_manager.backtester,
            strategy_templates=self.strategy_manager.strategy_templates
        )
        self.smart_order_router = SmartOrderRouter({
            "cex": self.cex_executor,
            "kraken": self.kraken_executor,
            "gemini": self.gemini_executor,
            "defi": self.defi_executor,
        })
        self.anomaly_detector = AnomalyDetector()
        self.strategy_scheduler = StrategyScheduler(self.strategy_manager.strategies)
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_plugins()
        self.audit_logger = AuditLogger()
        self.allowance_auditor = AllowanceAuditor(self.rpc_url, self.wallet_address, self.tokeninfo_service.erc20_abi)

        # Margin and risk
        self.interest_tracker = InterestTracker()
        self.margin_manager = MarginManager(self.cex_executor, self.portfolio_service, self.interest_tracker)
        self.liquidation_monitor = LiquidationMonitor(
            self.margin_manager,
            self.portfolio_service,
            threshold=1.15,
            poll_interval=30,
            on_liquidation_risk=self._auto_liq_callback,
            dashboard_callback=self._dashboard_liq_callback
        )
        self.liquidation_monitor.daemon = True
        self.liquidation_monitor.start()
        self.liquidation_events = []

        # Natural language
        self.parse_nl = parse_natural_language_command

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("BorgGodCore")
        self.logger.info("BorgGodCore initialized.")

    def _auto_liq_callback(self, symbol, margin_ratio):
        msg = f"Auto-liquidation triggered for {symbol}! Margin ratio: {margin_ratio}"
        self.liquidation_events.append(msg)
        self.margin_manager.auto_liquidate(symbol)

    def _dashboard_liq_callback(self, symbol, margin_ratio, msg):
        self.liquidation_events.append(msg)

    def get_executors(self):
        return {
            "cex": self.cex_executor,
            "kraken": self.kraken_executor,
            "gemini": self.gemini_executor,
            "defi": self.defi_executor,
        }

    def get_services(self):
        return {
            "portfolio": self.portfolio_service,
            "tokeninfo": self.tokeninfo_service,
            "strategy": self.strategy_manager,
            "feature_engineer": self.feature_engineer,
            "ensembler": self.model_ensembler,
            "ml_manager": self.ml_manager,
            "auto_strategy_gen": self.auto_strategy_gen,
            "order_router": self.smart_order_router,
            "risk": self.position_manager,
            "anomaly": self.anomaly_detector,
            "scheduler": self.strategy_scheduler,
            "plugin": self.plugin_loader,
            "audit": self.audit_logger,
            "allowance": self.allowance_auditor,
            "news": self.news_scraper,
            "margin_manager": self.margin_manager,
            "interest_tracker": self.interest_tracker,
            "liquidation_monitor": self.liquidation_monitor,
            "chain_registry": self.chain_registry,
            "nl_parse": self.parse_nl
        }