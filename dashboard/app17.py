import os
from dotenv import load_dotenv
from dashboard.advanced_dashboard import show_advanced_dashboard
from services.core import BorgCore
from services.data.data_pipeline import DataPipeline
from services.tokeninfo import TokenInfoService

def main():
    load_dotenv()
    config = {
        "ETH_RPC_URL": os.getenv("ETH_RPC_URL"),
        "DUNE_QUERY_ID": os.getenv("DUNE_QUERY_ID"),
        "DUNE_API_KEY": os.getenv("DUNE_API_KEY"),
        "GITHUB_REPO": "ethereum/ethereum-org-website"
    }
    tokeninfo = TokenInfoService(config["ETH_RPC_URL"])
    data_pipeline = DataPipeline(config, tokeninfo.erc20_abi)
    core = BorgCore()
    core.data_pipeline = data_pipeline  # Attach for GUI & strategies
    show_advanced_dashboard(core)

if __name__ == "__main__":
    main()