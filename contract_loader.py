import json
from typing import Any
from web3 import Web3

from config import CHAINS

with open("abi/morpho_blue.json") as f:
    ABI = json.load(f)


def get_contract(chain_name: str):
    """Return a Web3 instance and contract object for the named chain."""
    chain_config = CHAINS[chain_name]

    w3 = Web3(
        Web3.HTTPProvider(
            chain_config["rpc"]
        )
    )

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(
            chain_config["morpho"]
        ),
        abi=ABI
    )

    return w3, contract
