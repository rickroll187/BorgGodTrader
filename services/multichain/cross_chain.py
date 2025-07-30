class CrossChainManager:
    """
    Handles multi-chain balance and transaction operations.
    """
    def __init__(self, chain_clients):
        self.chain_clients = chain_clients  # Dict: chain_name -> client

    def get_balance(self, chain, address):
        return self.chain_clients[chain].get_balance(address)

    def send_tx(self, chain, tx):
        return self.chain_clients[chain].send_transaction(tx)