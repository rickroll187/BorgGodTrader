import datetime

class AutoTrader:
    def __init__(self, spot_executor, margin_executor, symbols, trading_logs):
        self.spot_executor = spot_executor
        self.margin_executor = margin_executor
        self.symbols = symbols
        self.trading_logs = trading_logs

    def log(self, message, type_="info"):
        self.trading_logs.append({
            "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "type": type_,
            "message": message
        })

    def run_spot_trading(self):
        for symbol in self.symbols:
            try:
                self.spot_executor.buy(symbol)
                self.log(f"Spot Long executed for {symbol}", "success")
            except Exception as e:
                self.log(f"Spot trading LONG error for {symbol}: {e}", "error")
            try:
                self.spot_executor.sell(symbol)
                self.log(f"Spot Sell executed for {symbol}", "success")
            except Exception as e:
                self.log(f"Spot trading SELL error for {symbol}: {e}", "error")

    def run_margin_trading(self):
        for symbol in self.symbols:
            try:
                self.margin_executor.open_long(symbol, amount=0.01)
                self.log(f"Margin LONG opened for {symbol}", "success")
            except Exception as e:
                self.log(f"Margin LONG error for {symbol}: {e}", "error")
            try:
                self.margin_executor.open_short(symbol, amount=0.01)
                self.log(f"Margin SHORT opened for {symbol}", "success")
            except Exception as e:
                self.log(f"Margin SHORT error for {symbol}: {e}", "error")