"""
Basic tests for BorgGodTrader core functionality.
Run with: python -m pytest tests/ -v
"""
import os
import sys
import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImports:
    """Test that all modules can be imported."""

    def test_import_core(self):
        from services.core import BorgCore
        assert BorgCore is not None

    def test_import_portfolio(self):
        from services.portfolio import PortfolioService
        assert PortfolioService is not None

    def test_import_tokeninfo(self):
        from services.tokeninfo import TokenInfoService
        assert TokenInfoService is not None

    def test_import_executors(self):
        from services.execution import KrakenExecutor, GeminiExecutor, CEXExecutor
        assert KrakenExecutor is not None
        assert GeminiExecutor is not None
        assert CEXExecutor is not None

    def test_import_strategies(self):
        from services.strategies import StrategyManager
        assert StrategyManager is not None

    def test_import_data_sources(self):
        from services.data import DataSources
        assert DataSources is not None

    def test_import_risk(self):
        from services.risk import PositionManager, RiskEngine
        assert PositionManager is not None
        assert RiskEngine is not None

    def test_import_monitoring(self):
        from services.monitoring import AnomalyDetector, AuditLogger
        assert AnomalyDetector is not None
        assert AuditLogger is not None


class TestPaperTrading:
    """Test paper trading functionality."""

    def test_cex_executor_paper_mode(self):
        from services.execution import CEXExecutor
        from services.execution import TradeLogger

        logger = TradeLogger(log_dir="/tmp/test_logs")
        executor = CEXExecutor(logger=logger, paper_mode=True)

        # Test buy
        result = executor.buy("BTC/USD", 0.1)
        assert result["status"] == "filled"
        assert result["paper_mode"] is True

        # Test sell
        result = executor.sell("BTC/USD", 0.05)
        assert result["status"] == "filled"

        # Check balances updated
        balances = executor.get_balance()
        assert balances.get("BTC", 0) > 0

    def test_paper_balance_tracking(self):
        from services.execution import CEXExecutor

        executor = CEXExecutor(paper_mode=True)
        initial_usd = executor.paper_balances["USD"]

        # Buy some BTC
        executor.buy("BTC/USD", 0.01)

        # USD should decrease
        assert executor.paper_balances["USD"] < initial_usd
        # BTC should increase
        assert executor.paper_balances["BTC"] > 0


class TestDataSources:
    """Test data source functionality."""

    def test_fear_greed_index(self):
        from services.data import DataSources

        ds = DataSources()
        result = ds.get_fear_greed_index()

        assert "value" in result
        assert "classification" in result
        assert 0 <= result["value"] <= 100

    def test_gas_prices(self):
        from services.data import DataSources

        ds = DataSources()
        result = ds.get_gas_prices()

        # May be empty if API fails, but shouldn't error
        assert isinstance(result, dict)


class TestNaturalLanguage:
    """Test NL parsing."""

    def test_parse_buy_command(self):
        from services.extensibility.natural_language_strategy import parse_natural_language_command

        result = parse_natural_language_command("buy 0.1 ETH")

        assert result["action"] == "buy"
        assert result["asset"] == "ETH"
        assert result["amount"] == 0.1
        assert result["parsed"] is True

    def test_parse_sell_command(self):
        from services.extensibility.natural_language_strategy import parse_natural_language_command

        result = parse_natural_language_command("sell 100 USDC")

        assert result["action"] == "sell"
        assert result["asset"] == "USDC"
        assert result["amount"] == 100

    def test_parse_with_conditions(self):
        from services.extensibility.natural_language_strategy import parse_natural_language_command

        result = parse_natural_language_command("buy 0.1 ETH when BTC drops 5%")

        assert result["action"] == "buy"
        conditions = result.get("conditions", {})
        assert conditions.get("reference_asset") == "BTC"
        assert conditions.get("change_pct") == -5

    def test_parse_query(self):
        from services.extensibility.natural_language_strategy import parse_natural_language_command

        result = parse_natural_language_command("what's my portfolio balance")

        assert result["action"] == "get_portfolio"
        assert result["parsed"] is True


class TestRiskManagement:
    """Test risk management."""

    def test_position_manager(self):
        from services.risk import PositionManager
        from unittest.mock import Mock

        portfolio = Mock()
        pm = PositionManager(portfolio, {"max_drawdown": 0.15, "max_pos_size": 0.2})

        # Open position
        result = pm.open_position("BTC/USD", "long", 0.1, 67000, stop_loss=65000)
        assert result["status"] == "opened"

        # Check positions
        positions = pm.get_positions()
        assert len(positions) == 1

    def test_anomaly_detector(self):
        from services.monitoring import AnomalyDetector

        detector = AnomalyDetector(window_size=20, z_threshold=2.0)

        # Feed normal data
        for i in range(30):
            detector.update("BTC", 67000 + i * 10)

        # Feed anomalous data
        anomaly = detector.update("BTC", 90000)

        # Should detect this as anomaly
        assert anomaly is not None or len(detector.get_recent_anomalies()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
