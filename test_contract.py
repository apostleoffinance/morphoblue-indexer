import json
import os

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

MM_INFURA_URL = os.getenv("MM_INFURA_URL")

web3 = Web3(
    Web3.HTTPProvider(MM_INFURA_URL)
)

MORPHO = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"

with open("abi/morpho_blue.json") as f:
    abi = json.load(f)

contract = web3.eth.contract(
    address=Web3.to_checksum_address(MORPHO),
    abi=abi
)

print(contract.events.Supply)