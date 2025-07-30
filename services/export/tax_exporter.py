import pandas as pd

class TaxExporter:
    """
    Exports trade logs for tax/compliance.
    """
    def __init__(self, log_df):
        self.log_df = log_df

    def export_csv(self, filename):
        self.log_df.to_csv(filename, index=False)

    def export_koinly(self, filename):
        koinly_df = self.log_df.rename(columns={
            "timestamp": "Date",
            "type": "Type",
            "amount": "Amount",
            "asset": "Currency",
            "price": "Rate",
            "fee": "Fee Amount"
        })
        koinly_df.to_csv(filename, index=False)