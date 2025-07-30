import logging
import re
import os

class SecurityMonitor:
    """
    Scans for key leaks and abnormal trades.
    """
    def __init__(self):
        self.logger = logging.getLogger("SecurityMonitor")

    def check_for_key_leak(self, codebase_path):
        # Scan files for 'secret', 'key', or 'token'
        for dirpath, _, filenames in os.walk(codebase_path):
            for fname in filenames:
                if fname.endswith(('.py', '.env', '.json')):
                    try:
                        with open(os.path.join(dirpath, fname), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if re.search(r'(secret|key|token)[=: ]', content, re.IGNORECASE):
                                self.logger.warning(f"Key leak risk in {fname}")
                    except Exception:
                        continue

    def detect_anomalous_activity(self, trade_log):
        # Flag trades > $10k or at odd hours (simple example)
        flagged = []
        for trade in trade_log:
            if trade.get('amount', 0) > 10000 or str(trade.get('timestamp', '')).endswith('03'):  # e.g., 03:00
                flagged.append(trade)
        return flagged

    def alert(self, message):
        self.logger.warning(f"SECURITY ALERT: {message}")