import os
import json
import time
import logging
from typing import Dict, Optional, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("web3 not installed - DeFi executor will be limited")


class DeFiExecutor:
    """
    DeFi executor for on-chain trading via Uniswap V3 and other DEXes.
    Supports swaps, liquidity provision, and contract interactions.
    """

    # Uniswap V3 Router address (Ethereum mainnet)
    UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

    # Common token addresses
    TOKENS = {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "DAI": "0x6B175474E89094C44Da98b954EescdC5cCc07bdbef",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    }

    # Minimal ERC20 ABI
    ERC20_ABI = [
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
         "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "decimals",
         "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
         "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
         "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    ]

    # Uniswap V3 Router ABI (minimal for swaps)
    ROUTER_ABI = [
        {
            "inputs": [
                {"components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "recipient", "type": "address"},
                    {"name": "deadline", "type": "uint256"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMinimum", "type": "uint256"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"}
                ], "name": "params", "type": "tuple"}
            ],
            "name": "exactInputSingle",
            "outputs": [{"name": "amountOut", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function"
        }
    ]

    def __init__(self, chain_registry=None, private_key: Optional[str] = None,
                 wallet_address: Optional[str] = None, logger=None, rpc_url: Optional[str] = None):
        self.chain_registry = chain_registry
        self.private_key = private_key or os.getenv("ETH_PRIVATE_KEY")
        self.wallet_address = wallet_address or os.getenv("ETH_WALLET_ADDRESS")
        self.trade_logger = logger
        self.rpc_url = rpc_url or os.getenv("ETH_RPC_URL")

        self.w3 = None
        if WEB3_AVAILABLE and self.rpc_url:
            self._init_web3()

    def _init_web3(self):
        """Initialize Web3 connection."""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            # Add PoA middleware for networks like Polygon
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            if self.w3.is_connected():
                logger.info(f"Connected to chain ID: {self.w3.eth.chain_id}")
            else:
                logger.error("Failed to connect to RPC")
                self.w3 = None
        except Exception as e:
            logger.error(f"Web3 init failed: {e}")
            self.w3 = None

    def is_connected(self) -> bool:
        """Check if connected to blockchain."""
        return self.w3 is not None and self.w3.is_connected()

    def get_eth_balance(self, address: Optional[str] = None) -> float:
        """Get ETH balance for an address."""
        if not self.is_connected():
            return 0.0

        address = address or self.wallet_address
        if not address:
            return 0.0

        try:
            balance_wei = self.w3.eth.get_balance(address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"Failed to get ETH balance: {e}")
            return 0.0

    def get_token_balance(self, token_address: str, wallet: Optional[str] = None) -> float:
        """Get ERC20 token balance."""
        if not self.is_connected():
            return 0.0

        wallet = wallet or self.wallet_address
        if not wallet:
            return 0.0

        try:
            # Resolve symbol to address if needed
            if token_address.upper() in self.TOKENS:
                token_address = self.TOKENS[token_address.upper()]

            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.ERC20_ABI
            )
            balance = contract.functions.balanceOf(wallet).call()
            decimals = contract.functions.decimals().call()
            return float(balance) / (10 ** decimals)
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return 0.0

    def get_all_balances(self) -> Dict[str, float]:
        """Get balances for ETH and common tokens."""
        balances = {"ETH": self.get_eth_balance()}

        for symbol, address in self.TOKENS.items():
            balance = self.get_token_balance(address)
            if balance > 0:
                balances[symbol] = balance

        return balances

    def approve_token(self, token_address: str, spender: str, amount: int = None) -> Optional[str]:
        """Approve token spending."""
        if not self.is_connected() or not self.private_key:
            logger.error("Cannot approve - not connected or no private key")
            return None

        try:
            if token_address.upper() in self.TOKENS:
                token_address = self.TOKENS[token_address.upper()]

            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.ERC20_ABI
            )

            # Max approval if amount not specified
            if amount is None:
                amount = 2**256 - 1

            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            gas_price = self.w3.eth.gas_price

            txn = contract.functions.approve(
                self.w3.to_checksum_address(spender),
                amount
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': gas_price,
            })

            signed = self.w3.eth.account.sign_transaction(txn, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            logger.info(f"Approval tx sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Approval failed: {e}")
            return None

    def swap_exact_input(self, token_in: str, token_out: str, amount_in: float,
                         slippage: float = 0.005, fee_tier: int = 3000) -> Dict[str, Any]:
        """
        Execute a swap on Uniswap V3.

        Args:
            token_in: Input token symbol or address
            token_out: Output token symbol or address
            amount_in: Amount of input token
            slippage: Max slippage (0.005 = 0.5%)
            fee_tier: Pool fee tier (500, 3000, or 10000)
        """
        if not self.is_connected() or not self.private_key:
            return {"status": "failed", "error": "Not connected or no private key"}

        try:
            # Resolve symbols to addresses
            if token_in.upper() in self.TOKENS:
                token_in = self.TOKENS[token_in.upper()]
            if token_out.upper() in self.TOKENS:
                token_out = self.TOKENS[token_out.upper()]

            token_in = self.w3.to_checksum_address(token_in)
            token_out = self.w3.to_checksum_address(token_out)

            # Get decimals
            token_contract = self.w3.eth.contract(address=token_in, abi=self.ERC20_ABI)
            decimals = token_contract.functions.decimals().call()
            amount_in_wei = int(amount_in * (10 ** decimals))

            # Check allowance and approve if needed
            allowance = token_contract.functions.allowance(
                self.wallet_address, self.UNISWAP_V3_ROUTER
            ).call()

            if allowance < amount_in_wei:
                logger.info("Approving token for router...")
                approval_tx = self.approve_token(token_in, self.UNISWAP_V3_ROUTER)
                if approval_tx:
                    # Wait for approval
                    self.w3.eth.wait_for_transaction_receipt(approval_tx, timeout=120)

            # Build swap transaction
            router = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.UNISWAP_V3_ROUTER),
                abi=self.ROUTER_ABI
            )

            deadline = int(time.time()) + 1800  # 30 min deadline
            min_out = 0  # TODO: Get quote and calculate min with slippage

            params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee_tier,
                'recipient': self.wallet_address,
                'deadline': deadline,
                'amountIn': amount_in_wei,
                'amountOutMinimum': min_out,
                'sqrtPriceLimitX96': 0,
            }

            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            gas_price = self.w3.eth.gas_price

            txn = router.functions.exactInputSingle(params).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': gas_price,
            })

            signed = self.w3.eth.account.sign_transaction(txn, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            result = {
                "status": "submitted",
                "tx_hash": tx_hash.hex(),
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "timestamp": time.time(),
            }

            if self.trade_logger:
                self.trade_logger.log_trade(result)

            logger.info(f"Swap tx sent: {tx_hash.hex()}")
            return result

        except Exception as e:
            logger.error(f"Swap failed: {e}")
            return {"status": "failed", "error": str(e)}

    def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> Dict[str, Any]:
        """Wait for transaction confirmation."""
        if not self.is_connected():
            return {"confirmed": False, "error": "Not connected"}

        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return {
                "confirmed": True,
                "status": "success" if receipt['status'] == 1 else "reverted",
                "block_number": receipt['blockNumber'],
                "gas_used": receipt['gasUsed'],
            }
        except Exception as e:
            return {"confirmed": False, "error": str(e)}

    def get_gas_price(self) -> Dict[str, float]:
        """Get current gas prices in gwei."""
        if not self.is_connected():
            return {}

        try:
            gas_price = self.w3.eth.gas_price
            base_fee = self.w3.eth.get_block('latest').get('baseFeePerGas', 0)

            return {
                "gas_price_gwei": float(self.w3.from_wei(gas_price, 'gwei')),
                "base_fee_gwei": float(self.w3.from_wei(base_fee, 'gwei')) if base_fee else 0,
            }
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            return {}

    def estimate_swap_gas(self, token_in: str, token_out: str, amount: float) -> int:
        """Estimate gas for a swap."""
        # Rough estimates based on Uniswap V3
        return 200000  # Conservative estimate

    def send_eth(self, to_address: str, amount: float) -> Dict[str, Any]:
        """Send ETH to an address."""
        if not self.is_connected() or not self.private_key:
            return {"status": "failed", "error": "Not connected or no private key"}

        try:
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            gas_price = self.w3.eth.gas_price

            txn = {
                'nonce': nonce,
                'to': self.w3.to_checksum_address(to_address),
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': gas_price,
            }

            signed = self.w3.eth.account.sign_transaction(txn, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            return {
                "status": "submitted",
                "tx_hash": tx_hash.hex(),
                "to": to_address,
                "amount": amount,
            }

        except Exception as e:
            logger.error(f"ETH send failed: {e}")
            return {"status": "failed", "error": str(e)}
