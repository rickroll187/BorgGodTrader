import json
import os
from datetime import datetime
import pandas as pd

class TradeLogger:
    def __init__(self, log_file="trade_log.txt"):
        self.log_file = log_file

    def log_trade(self, trade_dict):
        entry = dict(trade_dict)
        entry["timestamp"] = datetime.utcnow().isoformat()
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_log_dataframe(self):
        if not os.path.exists(self.log_file):
            return pd.DataFrame()
        with open(self.log_file, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        return pd.DataFrame(lines)
