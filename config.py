
import os
from dotenv import load_dotenv

load_dotenv()

# RPC URLs from environment variables
ETH_RPC = os.getenv("MM_INFURA_URL")  # Use existing MM_INFURA_URL for Ethereum
BASE_RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")  # Fallback to public Base RPC
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc")  # Fallback to public Arbitrum RPC


CHAINS = {
    "ethereum": {
        "rpc": ETH_RPC,
        "morpho": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
    },
    "base": {
        "rpc": BASE_RPC,
        "morpho": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
    },
    "arbitrum": {
        "rpc": ARBITRUM_RPC,
        "morpho": "0x6c247b1F6182318877311737BaC0844bAa518F5e"
    }
}
