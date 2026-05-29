import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False


class AllowanceAuditor:
    """
    Audits ERC20 token allowances to detect potential security risks.
    Helps identify unlimited approvals and suspicious contracts.
    """

    # Known DEX routers and protocols (considered safe)
    KNOWN_SAFE_CONTRACTS = {
        "0xE592427A0AEce92De3Edee1F18E0157C05861564": "Uniswap V3 Router",
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D": "Uniswap V2 Router",
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F": "SushiSwap Router",
        "0x1111111254EEB25477B68fb85Ed929f73A960582": "1inch Router",
        "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": "Uniswap Universal Router",
    }

    # Standard ERC20 ABI for allowance checks
    ERC20_ABI = [
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
         "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "symbol",
         "outputs": [{"name": "", "type": "string"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "decimals",
         "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    ]

    def __init__(self, rpc_url: str = None, wallet_address: str = None, erc20_abi: list = None):
        self.rpc_url = rpc_url or os.getenv("ETH_RPC_URL")
        self.wallet_address = wallet_address or os.getenv("ETH_WALLET_ADDRESS")
        self.erc20_abi = erc20_abi or self.ERC20_ABI

        self.w3 = None
        if WEB3_AVAILABLE and self.rpc_url:
            try:
                self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            except Exception as e:
                logger.error(f"Web3 init failed: {e}")

    def check_allowance(self, token_address: str, spender_address: str) -> Dict[str, Any]:
        """Check allowance for a specific token and spender."""
        if not self.w3 or not self.wallet_address:
            return {"error": "Web3 not configured"}

        try:
            token = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )

            allowance = token.functions.allowance(
                self.wallet_address,
                self.w3.to_checksum_address(spender_address)
            ).call()

            try:
                symbol = token.functions.symbol().call()
                decimals = token.functions.decimals().call()
            except:
                symbol = "UNKNOWN"
                decimals = 18

            # Check if unlimited (max uint256)
            is_unlimited = allowance >= (2**256 - 1) // 2

            # Check if spender is known
            spender_name = self.KNOWN_SAFE_CONTRACTS.get(
                self.w3.to_checksum_address(spender_address), "Unknown"
            )

            return {
                "token": token_address,
                "symbol": symbol,
                "spender": spender_address,
                "spender_name": spender_name,
                "allowance": allowance,
                "allowance_readable": allowance / (10 ** decimals),
                "is_unlimited": is_unlimited,
                "risk_level": self._assess_risk(allowance, spender_address),
            }

        except Exception as e:
            return {"error": str(e)}

    def _assess_risk(self, allowance: int, spender: str) -> str:
        """Assess risk level of an allowance."""
        if allowance == 0:
            return "none"

        is_unlimited = allowance >= (2**256 - 1) // 2
        is_known = self.w3.to_checksum_address(spender) in self.KNOWN_SAFE_CONTRACTS if self.w3 else False

        if is_unlimited and not is_known:
            return "high"
        elif is_unlimited and is_known:
            return "medium"
        elif not is_known:
            return "medium"
        else:
            return "low"

    def audit_common_tokens(self, spenders: List[str] = None) -> List[Dict]:
        """Audit allowances for common tokens."""
        # Common token addresses
        tokens = {
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "DAI": "0x6B175474E89094C44Da98b954EescdC5c4cbb07bdbef",
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }

        if spenders is None:
            spenders = list(self.KNOWN_SAFE_CONTRACTS.keys())

        results = []
        for token_name, token_addr in tokens.items():
            for spender in spenders:
                result = self.check_allowance(token_addr, spender)
                if result.get("allowance", 0) > 0:
                    result["token_name"] = token_name
                    results.append(result)

        return results

    def get_risky_allowances(self) -> List[Dict]:
        """Get all allowances with medium or high risk."""
        all_allowances = self.audit_common_tokens()
        return [a for a in all_allowances if a.get("risk_level") in ("medium", "high")]

    def revoke_allowance(self, token_address: str, spender_address: str) -> Optional[str]:
        """Revoke an allowance (set to 0). Requires private key."""
        private_key = os.getenv("ETH_PRIVATE_KEY")
        if not self.w3 or not private_key:
            logger.error("Cannot revoke - Web3 or private key not configured")
            return None

        try:
            token = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=[{
                    "constant": False,
                    "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }]
            )

            nonce = self.w3.eth.get_transaction_count(self.wallet_address)

            txn = token.functions.approve(
                self.w3.to_checksum_address(spender_address),
                0
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gas': 60000,
                'gasPrice': self.w3.eth.gas_price,
            })

            signed = self.w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            logger.info(f"Revoked allowance: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Failed to revoke allowance: {e}")
            return None
