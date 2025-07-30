import requests
import time
import random
from web3 import Web3

class RealTimeFetchers:
    """
    Real-time data fetchers for DeFi protocols and on-chain analytics, using free-tier APIs where possible.
    Covers TheGraph, Dune Analytics, Aave, Uniswap, and generic on-chain endpoints.
    """

    # --- TheGraph Example: Uniswap V3 Pools ---
    @staticmethod
    def fetch_uniswapv3_pool_stats(token0, token1, pool_fee=3000):
        """Fetch Uniswap V3 pool stats using TheGraph public endpoint."""
        url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        query = """
        query ($token0: String!, $token1: String!, $feeTier: Int!) {
          pools(where: {token0: $token0, token1: $token1, feeTier: $feeTier}) {
            id
            token0 { symbol }
            token1 { symbol }
            liquidity
            sqrtPrice
            volumeUSD
            feesUSD
            tick
            totalValueLockedUSD
          }
        }
        """
        variables = {
            "token0": token0,
            "token1": token1,
            "feeTier": pool_fee
        }
        try:
            resp = requests.post(url, json={"query": query, "variables": variables}, timeout=10)
            pools = resp.json().get("data", {}).get("pools", [])
            return pools[0] if pools else {}
        except Exception as e:
            print(f"UniswapV3 fetch error: {e}")
            return {}

    # --- TheGraph: Aave V3 Stats ---
    @staticmethod
    def fetch_aavev3_stats():
        url = "https://api.thegraph.com/subgraphs/name/aave/protocol-v3"
        query = """
        {
          reserves(first: 5) {
            symbol
            name
            liquidityRate
            variableBorrowRate
            totalATokenSupply
            totalCurrentVariableDebt
            totalCurrentStableDebt
            utilizationRate
          }
        }
        """
        try:
            resp = requests.post(url, json={"query": query}, timeout=10)
            reserves = resp.json().get("data", {}).get("reserves", [])
            return reserves
        except Exception as e:
            print(f"AaveV3 fetch error: {e}")
            return []

    # --- Uniswap V2: Token Pairs and Reserves (TheGraph) ---
    @staticmethod
    def fetch_uniswapv2_pair_reserves(token0, token1):
        url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
        query = """
        query($token0: String!, $token1: String!) {
          pairs(where: {token0: $token0, token1: $token1}) {
            id
            reserve0
            reserve1
            token0 {symbol}
            token1 {symbol}
            volumeUSD
            reserveUSD
          }
        }
        """
        variables = {"token0": token0, "token1": token1}
        try:
            resp = requests.post(url, json={"query": query, "variables": variables}, timeout=10)
            pairs = resp.json().get("data", {}).get("pairs", [])
            return pairs[0] if pairs else {}
        except Exception as e:
            print(f"UniswapV2 fetch error: {e}")
            return {}

    # --- Dune Analytics API (requires API key; free tier available) ---
    @staticmethod
    def fetch_dune_query_result(query_id, api_key, parameters={}):
        """
        Fetch Dune Analytics query results (JSON).
        Parameters:
            query_id: Dune query ID (integer)
            api_key: Dune API key (get yours at https://dune.com/docs/api/)
            parameters: dict, query parameters if needed
        """
        url = f"https://api.dune.com/api/v1/query/{query_id}/results"
        headers = {"x-dune-api-key": api_key}
        try:
            resp = requests.get(url, headers=headers, params=parameters, timeout=20)
            data = resp.json()
            return data.get("result", {}).get("rows", [])
        except Exception as e:
            print(f"Dune fetch error: {e}")
            return []

    # --- On-chain: ETH Balance, ERC20 Balance, Contract Read (via Infura/Alchemy, free tier) ---
    @staticmethod
    def get_eth_balance(address, rpc_url):
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            balance = w3.eth.get_balance(Web3.to_checksum_address(address))
            return balance / 1e18
        except Exception as e:
            print(f"ETH balance fetch error: {e}")
            return 0

    @staticmethod
    def get_erc20_balance(address, token_address, rpc_url, erc20_abi):
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=erc20_abi)
            bal = contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
            decimals = contract.functions.decimals().call()
            return bal / (10 ** decimals)
        except Exception as e:
            print(f"ERC20 balance fetch error: {e}")
            return 0

    # --- Generic Contract Call ---
    @staticmethod
    def call_contract_function(contract_address, abi, function_name, args, rpc_url):
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            func = getattr(contract.functions, function_name)
            return func(*args).call()
        except Exception as e:
            print(f"Contract call error: {e}")
            return None

    # --- Example: aggregate live DeFi stats for a token pair ---
    @staticmethod
    def fetch_all_defi_stats(
        token0_address,
        token1_address,
        rpc_url,
        erc20_abi,
        dune_query_id=None,
        dune_api_key=None
    ):
        stats = {}
        stats["univ3_pool"] = RealTimeFetchers.fetch_uniswapv3_pool_stats(token0_address, token1_address)
        stats["univ2_pair"] = RealTimeFetchers.fetch_uniswapv2_pair_reserves(token0_address, token1_address)
        stats["aave_reserves"] = RealTimeFetchers.fetch_aavev3_stats()
        if dune_query_id and dune_api_key:
            stats["dune"] = RealTimeFetchers.fetch_dune_query_result(dune_query_id, dune_api_key)
        # Optionally add on-chain balances or contract calls as needed
        return stats