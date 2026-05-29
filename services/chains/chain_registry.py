import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("web3 not installed - chain registry limited")


class ChainConfig:
    def __init__(self, chain_id: int, name: str, rpc_env_var: str,
                 native_token: str, block_time: float,
                 explorer: str, uniswap_router: str = None,
                 requires_poa: bool = False):
        self.chain_id = chain_id
        self.name = name
        self.rpc_env_var = rpc_env_var
        self.native_token = native_token
        self.block_time = block_time  # seconds
        self.explorer = explorer
        self.uniswap_router = uniswap_router
        self.requires_poa = requires_poa

    @property
    def rpc_url(self) -> Optional[str]:
        return os.getenv(self.rpc_env_var)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "native_token": self.native_token,
            "block_time": self.block_time,
            "explorer": self.explorer,
            "rpc_configured": bool(self.rpc_url),
        }


class ChainRegistry:
    """
    Multi-chain registry supporting EVM-compatible networks.
    Manages Web3 connections and chain-specific contract addresses.
    """

    # All supported chains
    CHAIN_CONFIGS = {
        "ethereum": ChainConfig(
            chain_id=1,
            name="Ethereum Mainnet",
            rpc_env_var="ETH_RPC_URL",
            native_token="ETH",
            block_time=12.0,
            explorer="https://etherscan.io",
            uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        ),
        "polygon": ChainConfig(
            chain_id=137,
            name="Polygon",
            rpc_env_var="POLYGON_RPC_URL",
            native_token="MATIC",
            block_time=2.0,
            explorer="https://polygonscan.com",
            uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
            requires_poa=True,
        ),
        "arbitrum": ChainConfig(
            chain_id=42161,
            name="Arbitrum One",
            rpc_env_var="ARBITRUM_RPC_URL",
            native_token="ETH",
            block_time=0.25,
            explorer="https://arbiscan.io",
            uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        ),
        "optimism": ChainConfig(
            chain_id=10,
            name="Optimism",
            rpc_env_var="OPTIMISM_RPC_URL",
            native_token="ETH",
            block_time=2.0,
            explorer="https://optimistic.etherscan.io",
            uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        ),
        "bsc": ChainConfig(
            chain_id=56,
            name="BNB Smart Chain",
            rpc_env_var="BSC_RPC_URL",
            native_token="BNB",
            block_time=3.0,
            explorer="https://bscscan.com",
            uniswap_router="0x10ED43C718714eb63d5aA57B78B54704E256024E",  # PancakeSwap
            requires_poa=True,
        ),
        "avalanche": ChainConfig(
            chain_id=43114,
            name="Avalanche C-Chain",
            rpc_env_var="AVAX_RPC_URL",
            native_token="AVAX",
            block_time=2.0,
            explorer="https://snowtrace.io",
            uniswap_router="0x60aE616a2155Ee3d9A68541Ba4544862310933d4",  # TraderJoe
            requires_poa=True,
        ),
        "base": ChainConfig(
            chain_id=8453,
            name="Base",
            rpc_env_var="BASE_RPC_URL",
            native_token="ETH",
            block_time=2.0,
            explorer="https://basescan.org",
            uniswap_router="0x2626664c2603336E57B271c5C0b26F421741e481",  # Uniswap V3 on Base
        ),
        "fantom": ChainConfig(
            chain_id=250,
            name="Fantom Opera",
            rpc_env_var="FTM_RPC_URL",
            native_token="FTM",
            block_time=1.0,
            explorer="https://ftmscan.com",
            requires_poa=True,
        ),
    }

    # Free public RPC fallbacks (rate-limited, don't rely on these)
    PUBLIC_RPCS = {
        "ethereum": "https://cloudflare-eth.com",
        "polygon": "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "optimism": "https://mainnet.optimism.io",
        "bsc": "https://bsc-dataseed.binance.org",
        "avalanche": "https://api.avax.network/ext/bc/C/rpc",
        "base": "https://mainnet.base.org",
        "fantom": "https://rpc.ftm.tools",
    }

    def __init__(self):
        self.chains = self.CHAIN_CONFIGS
        self._web3_connections: Dict[str, Web3] = {}
        self._connection_status: Dict[str, bool] = {}

    def get_web3(self, chain: str) -> Optional[Any]:
        """Get Web3 connection for a chain, with fallback to public RPC."""
        if not WEB3_AVAILABLE:
            return None

        if chain in self._web3_connections and self._web3_connections[chain].is_connected():
            return self._web3_connections[chain]

        config = self.chains.get(chain)
        if not config:
            logger.error(f"Unknown chain: {chain}")
            return None

        # Try configured RPC first, then public fallback
        rpc_url = config.rpc_url or self.PUBLIC_RPCS.get(chain)

        if not rpc_url:
            logger.warning(f"No RPC URL for {chain}")
            return None

        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))

            if config.requires_poa:
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)

            if w3.is_connected():
                self._web3_connections[chain] = w3
                self._connection_status[chain] = True
                logger.info(f"Connected to {chain} (chain_id={w3.eth.chain_id})")
                return w3
            else:
                logger.warning(f"Could not connect to {chain}")
                self._connection_status[chain] = False

        except Exception as e:
            logger.error(f"Web3 connection failed for {chain}: {e}")
            self._connection_status[chain] = False

        return None

    def get_balance(self, chain: str, address: str) -> float:
        """Get native token balance on a chain."""
        w3 = self.get_web3(chain)
        if not w3:
            return 0.0

        try:
            balance_wei = w3.eth.get_balance(w3.to_checksum_address(address))
            return float(w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"Balance fetch failed on {chain}: {e}")
            return 0.0

    def get_all_balances(self, address: str) -> Dict[str, float]:
        """Get native token balance across all configured chains."""
        if not address:
            return {}

        balances = {}
        for chain_name in self.chains:
            balance = self.get_balance(chain_name, address)
            if balance > 0:
                balances[chain_name] = balance

        return balances

    def get_gas_price(self, chain: str) -> Dict[str, float]:
        """Get current gas price on a chain."""
        w3 = self.get_web3(chain)
        if not w3:
            return {}

        try:
            gas_price = w3.eth.gas_price
            gwei = float(w3.from_wei(gas_price, 'gwei'))

            # Get base fee if EIP-1559 chain
            try:
                block = w3.eth.get_block('latest')
                base_fee = float(w3.from_wei(block.get('baseFeePerGas', 0), 'gwei'))
            except:
                base_fee = 0

            return {
                "gas_price_gwei": gwei,
                "base_fee_gwei": base_fee,
                "priority_fee_gwei": max(0, gwei - base_fee),
            }
        except Exception as e:
            logger.error(f"Gas price fetch failed on {chain}: {e}")
            return {}

    def send_transaction(self, chain: str, tx: Dict[str, Any]) -> Optional[str]:
        """Send a transaction on a specific chain."""
        w3 = self.get_web3(chain)
        if not w3:
            return None

        private_key = os.getenv("ETH_PRIVATE_KEY")
        if not private_key:
            logger.error("No private key configured")
            return None

        try:
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Transaction failed on {chain}: {e}")
            return None

    def get_chain_status(self) -> Dict[str, Dict[str, Any]]:
        """Get connectivity and status for all chains."""
        status = {}
        for chain_name, config in self.chains.items():
            w3 = self._web3_connections.get(chain_name)
            is_connected = w3.is_connected() if w3 else False

            block_number = None
            if is_connected:
                try:
                    block_number = w3.eth.block_number
                except:
                    pass

            status[chain_name] = {
                **config.to_dict(),
                "connected": is_connected,
                "block_number": block_number,
                "using_public_rpc": not bool(config.rpc_url),
            }

        return status

    def get_chain_ids(self) -> Dict[str, int]:
        return {k: v.chain_id for k, v in self.chains.items()}

    def get_native_token(self, chain: str) -> str:
        config = self.chains.get(chain)
        return config.native_token if config else "ETH"

    def get_uniswap_router(self, chain: str) -> Optional[str]:
        config = self.chains.get(chain)
        return config.uniswap_router if config else None

    def add_chain(self, name: str, config: ChainConfig):
        """Add a custom chain."""
        self.chains[name] = config
        logger.info(f"Added custom chain: {name}")

    def list_chains(self) -> List[str]:
        return list(self.chains.keys())
