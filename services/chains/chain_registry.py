from web3 import Web3

class ChainRegistry:
    """
    Multi-chain support: EVM chains with real RPCs.
    """
    def __init__(self):
        import os
        self.chains = {
            "ethereum": {
                "rpc": os.getenv("ETH_RPC_URL"),
                "chain_id": 1,
                "native": "ETH"
            },
            "polygon": {
                "rpc": os.getenv("POLYGON_RPC_URL"),
                "chain_id": 137,
                "native": "MATIC"
            },
            "arbitrum": {
                "rpc": os.getenv("ARBITRUM_RPC_URL"),
                "chain_id": 42161,
                "native": "ETH"
            },
            # Add more as needed
        }
        self.web3 = {}

    def get_web3(self, chain):
        if chain not in self.web3:
            self.web3[chain] = Web3(Web3.HTTPProvider(self.chains[chain]["rpc"]))
        return self.web3[chain]

    def get_chain_ids(self):
        return {k: v["chain_id"] for k, v in self.chains.items()}

    def get_native_token(self, chain):
        return self.chains[chain]["native"]