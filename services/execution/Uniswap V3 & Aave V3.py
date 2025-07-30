from .order_executor import OrderExecutor
from web3 import Web3
import json
import os
from dotenv import load_dotenv

class DeFiExecutor(OrderExecutor):
    """
    DeFi Executor: Uniswap V3 swaps and Aave v3 lending/borrowing.
    """
    def __init__(self, rpc_url, private_key, wallet_address, logger=None):
        super().__init__(logger=logger)
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        assert self.web3.is_connected(), "Web3 provider connection failed!"
        self.private_key = private_key
        self.wallet_address = wallet_address
        # Uniswap V3 SwapRouter (mainnet)
        router_address = Web3.to_checksum_address("0xE592427A0AEce92De3Edee1F18E0157C05861564")
        with open(os.path.join(os.path.dirname(__file__), "uniswap_v3_router_abi.json")) as f:
            self.uniswap_router_abi = json.load(f)
        self.uniswap_router = self.web3.eth.contract(address=router_address, abi=self.uniswap_router_abi)
        # Aave v3 Pool (mainnet)
        pool_address = Web3.to_checksum_address("0x7BeA39867e4169dBe237d55C8242a8f2fcDcc387")
        with open(os.path.join(os.path.dirname(__file__), "aave_pool_abi.json")) as f:
            self.aave_pool_abi = json.load(f)
        self.aave_pool = self.web3.eth.contract(address=pool_address, abi=self.aave_pool_abi)
        # ERC20 ABI
        with open(os.path.join(os.path.dirname(__file__), "erc20_abi.json")) as f:
            self.erc20_abi = json.load(f)

    # -------- Uniswap V3 SWAP --------
    def swap_uniswap_v3(self, token_in, token_out, amount_in, fee=3000, amount_out_min=0, deadline_minutes=10):
        """
        Swap token_in -> token_out on Uniswap V3.
        All addresses must be checksum.
        - fee: 500, 3000, or 10000 (Uniswap V3 pool fee)
        - amount_in: in token_in's smallest units (use decimals)
        """
        token_in = self.web3.to_checksum_address(token_in)
        token_out = self.web3.to_checksum_address(token_out)
        deadline = int(self.web3.eth.get_block('latest')['timestamp']) + deadline_minutes * 60

        # Approve router if needed
        if token_in != self.web3.to_checksum_address("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"):  # Not ETH
            erc20 = self.web3.eth.contract(address=token_in, abi=self.erc20_abi)
            allowance = erc20.functions.allowance(self.wallet_address, self.uniswap_router.address).call()
            if allowance < amount_in:
                approve_txn = erc20.functions.approve(self.uniswap_router.address, int(2**256-1)).build_transaction({
                    'from': self.wallet_address,
                    'gas': 60000,
                    'gasPrice': self.web3.eth.gas_price,
                    'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
                })
                signed_approve = self.web3.eth.account.sign_transaction(approve_txn, self.private_key)
                approve_tx_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
                self.web3.eth.wait_for_transaction_receipt(approve_tx_hash)

        params = {
            "tokenIn": token_in,
            "tokenOut": token_out,
            "fee": fee,
            "recipient": self.wallet_address,
            "deadline": deadline,
            "amountIn": int(amount_in),
            "amountOutMinimum": int(amount_out_min),
            "sqrtPriceLimitX96": 0
        }
        txn = self.uniswap_router.functions.exactInputSingle(params).build_transaction({
            'from': self.wallet_address,
            'gas': 300000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
            'value': amount_in if token_in == self.web3.to_checksum_address("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE") else 0
        })
        signed_txn = self.web3.eth.account.sign_transaction(txn, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return {"tx_hash": tx_hash.hex()}

    # --------- AAVE LENDING ---------
    def supply_aave(self, asset, amount, referral_code=0):
        asset = self.web3.to_checksum_address(asset)
        erc20 = self.web3.eth.contract(address=asset, abi=self.erc20_abi)
        allowance = erc20.functions.allowance(self.wallet_address, self.aave_pool.address).call()
        if allowance < amount:
            approve_txn = erc20.functions.approve(self.aave_pool.address, int(2**256-1)).build_transaction({
                'from': self.wallet_address,
                'gas': 60000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
            })
            signed_approve = self.web3.eth.account.sign_transaction(approve_txn, self.private_key)
            approve_tx_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
            self.web3.eth.wait_for_transaction_receipt(approve_tx_hash)

        txn = self.aave_pool.functions.supply(
            asset,
            int(amount),
            self.wallet_address,
            referral_code
        ).build_transaction({
            'from': self.wallet_address,
            'gas': 300000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
        })
        signed_txn = self.web3.eth.account.sign_transaction(txn, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return {"tx_hash": tx_hash.hex()}

    def withdraw_aave(self, asset, amount):
        asset = self.web3.to_checksum_address(asset)
        txn = self.aave_pool.functions.withdraw(
            asset,
            int(amount),
            self.wallet_address
        ).build_transaction({
            'from': self.wallet_address,
            'gas': 300000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
        })
        signed_txn = self.web3.eth.account.sign_transaction(txn, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return {"tx_hash": tx_hash.hex()}

    def borrow_aave(self, asset, amount, interest_rate_mode=2, referral_code=0):
        """
        interest_rate_mode: 1 = Stable, 2 = Variable
        """
        asset = self.web3.to_checksum_address(asset)
        txn = self.aave_pool.functions.borrow(
            asset,
            int(amount),
            self.wallet_address,
            referral_code,
            interest_rate_mode
        ).build_transaction({
            'from': self.wallet_address,
            'gas': 400000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
        })
        signed_txn = self.web3.eth.account.sign_transaction(txn, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return {"tx_hash": tx_hash.hex()}

    def repay_aave(self, asset, amount, interest_rate_mode=2):
        asset = self.web3.to_checksum_address(asset)
        erc20 = self.web3.eth.contract(address=asset, abi=self.erc20_abi)
        allowance = erc20.functions.allowance(self.wallet_address, self.aave_pool.address).call()
        if allowance < amount:
            approve_txn = erc20.functions.approve(self.aave_pool.address, int(2**256-1)).build_transaction({
                'from': self.wallet_address,
                'gas': 60000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
            })
            signed_approve = self.web3.eth.account.sign_transaction(approve_txn, self.private_key)
            approve_tx_hash = self.web3.eth.send_raw_transaction(signed_approve.rawTransaction)
            self.web3.eth.wait_for_transaction_receipt(approve_tx_hash)
        txn = self.aave_pool.functions.repay(
            asset,
            int(amount),
            interest_rate_mode,
            self.wallet_address
        ).build_transaction({
            'from': self.wallet_address,
            'gas': 400000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
        })
        signed_txn = self.web3.eth.account.sign_transaction(txn, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return {"tx_hash": tx_hash.hex()}