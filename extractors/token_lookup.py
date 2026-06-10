import json
from typing import Any

from web3 import Web3

from config import CHAINS
from contract_loader import get_contract

with open("abi/erc20.json") as f:
    ERC20_ABI = json.load(f)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def normalize_token_address(token_address: Any) -> str:
    if hasattr(token_address, "hex") and not isinstance(token_address, str):
        token_address = token_address.hex()
    return Web3.to_checksum_address(str(token_address))


def _call_token_field(token, field: str) -> Any:
    try:
        return getattr(token.functions, field)().call()
    except Exception:
        return None


def resolve_token(chain_name: str, token_address: str, w3: Web3 | None = None) -> dict[str, Any]:
    if chain_name not in CHAINS:
        raise ValueError(f"Unknown chain: {chain_name}")

    token_address = normalize_token_address(token_address)
    if w3 is None:
        w3, _ = get_contract(chain_name)

    token = w3.eth.contract(address=token_address, abi=ERC20_ABI)

    return {
        "chain": chain_name,
        "token_address": token_address,
        "symbol": _call_token_field(token, "symbol"),
        "name": _call_token_field(token, "name"),
        "decimals": _call_token_field(token, "decimals"),
    }


def extract_token_addresses(market_rows: list[dict[str, Any]]) -> list[str]:
    tokens: set[str] = set()
    for row in market_rows:
        for column in ("loan_token", "collateral_token"):
            value = row.get(column)
            if value is None:
                continue
            address = normalize_token_address(value)
            if address == ZERO_ADDRESS:
                continue
            tokens.add(address)
    return sorted(tokens)


def resolve_tokens(chain_name: str, token_addresses: list[str]) -> list[dict[str, Any]]:
    w3, _ = get_contract(chain_name)
    return [resolve_token(chain_name, address, w3=w3) for address in token_addresses]
