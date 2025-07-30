import os
from dotenv import load_dotenv
from services.execution.defi_executor import DeFiExecutor

def main():
    load_dotenv()
    rpc_url = os.getenv("ETH_RPC_URL")
    private_key = os.getenv("ETH_PRIVATE_KEY")
    wallet_address = os.getenv("ETH_WALLET_ADDRESS")
    executor = DeFiExecutor(rpc_url, private_key, wallet_address)

    # Example swap: USDC <-> WETH (Uniswap V3, 0.3% fee)
    usdc = "0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    weth = "0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    print("Swapping 10 USDC for WETH...")
    tx_hash = executor.swap_uniswap_v3(usdc, weth, 10_000_000, fee=3000)
    print("Swap tx:", tx_hash)

    # Example: Supply USDC to Aave
    print("Supplying 10 USDC to Aave...")
    tx_hash = executor.supply_aave(usdc, 10_000_000)
    print("Supply tx:", tx_hash)

    # Example: Withdraw USDC from Aave
    print("Withdrawing 1 USDC from Aave...")
    tx_hash = executor.withdraw_aave(usdc, 1_000_000)
    print("Withdraw tx:", tx_hash)

    # Example: Borrow USDC from Aave
    print("Borrowing 1 USDC (variable rate) from Aave...")
    tx_hash = executor.borrow_aave(usdc, 1_000_000)
    print("Borrow tx:", tx_hash)

    # Example: Repay USDC to Aave
    print("Repaying 1 USDC to Aave...")
    tx_hash = executor.repay_aave(usdc, 1_000_000)
    print("Repay tx:", tx_hash)

if __name__ == "__main__":
    main()