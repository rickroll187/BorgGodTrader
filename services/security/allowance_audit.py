from web3 import Web3

class AllowanceAuditor:
    def __init__(self, rpc_url, wallet_address, erc20_abi):
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.wallet_address = Web3.to_checksum_address(wallet_address) if wallet_address else None
        self.erc20_abi = erc20_abi

    def get_allowances(self, tokens, contracts):
        allowances = []
        if not self.wallet_address:
            return allowances
        for token in tokens:
            contract = self.web3.eth.contract(address=Web3.to_checksum_address(token), abi=self.erc20_abi)
            for spender in contracts:
                allowed = contract.functions.allowance(self.wallet_address, spender).call()
                allowances.append({
                    "token": token,
                    "spender": spender,
                    "allowance": allowed,
                })
        return allowances

    def revoke_allowance(self, token, spender):
        if not self.wallet_address:
            return None
        contract = self.web3.eth.contract(address=Web3.to_checksum_address(token), abi=self.erc20_abi)
        tx = contract.functions.approve(spender, 0).build_transaction({
            'from': self.wallet_address,
            'gas': 60000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
        })
        return tx
