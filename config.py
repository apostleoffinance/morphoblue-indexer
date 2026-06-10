
import os
from dotenv import load_dotenv

load_dotenv()

# Read configured RPC endpoints (accept common env var spellings)
INFURA_RPC = os.getenv("MM_INFURA_URL")
ALCHEMY_RPC = os.getenv("MM_ALCHEMY_URL") or os.getenv("MM_AlCHEMY_URL")
BASE_RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC") or os.getenv("ARBITRUM_RPC")


def _compact(*urls):
    return [u for u in urls if u]


CHAINS = {
    "ethereum": {
        "rpcs": _compact(INFURA_RPC, ALCHEMY_RPC),
        "morpho": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    },
    "base": {
        "rpcs": _compact(BASE_RPC),
        "morpho": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    },
    "arbitrum": {
        "rpcs": _compact(ARBITRUM_RPC),
        "morpho": "0x6c247b1F6182318877311737BaC0844bAa518F5e",
    },
}
