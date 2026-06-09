import json
from typing import Any, Optional, List
from web3 import Web3

from config import CHAINS

with open("abi/morpho_blue.json") as f:
    ABI = json.load(f)


def normalize_block_identifier(block_number: Any) -> Any:
    if isinstance(block_number, (bytes, bytearray)):
        return int.from_bytes(block_number, "big")
    if hasattr(block_number, "hex") and not isinstance(block_number, str):
        return int(block_number.hex(), 16)
    if isinstance(block_number, str) and block_number.isdigit():
        return int(block_number)
    return block_number


def _collect_candidate_rpcs(current_uri: Optional[str]) -> List[str]:
    candidates: List[str] = []
    for cfg in CHAINS.values():
        rpcs = cfg.get("rpcs") or ([cfg.get("rpc")] if cfg.get("rpc") else [])
        for u in rpcs:
            if u and u != current_uri and u not in candidates:
                candidates.append(u)
    return candidates


def _rpc_works(w3: Web3) -> bool:
    try:
        _ = w3.eth.block_number
        return True
    except Exception:
        return False


def get_block_timestamp(w3: Web3, block_number: Any) -> Optional[int]:
    """
    Try to get timestamp using the provided Web3 instance.
    On failure, attempt remaining RPCs configured in CHAINS.
    Returns None if no provider can return the block.
    """
    block_number = normalize_block_identifier(block_number)
    try:
        block = w3.eth.get_block(block_number)
        return block["timestamp"]
    except Exception:
        current_uri = getattr(w3.provider, "endpoint_uri", None)
        for rpc in _collect_candidate_rpcs(current_uri):
            try:
                tmp = Web3(Web3.HTTPProvider(rpc))
                block = tmp.eth.get_block(block_number)
                return block["timestamp"]
            except Exception:
                continue
    return None


def get_contract(chain_name: str):
    """
    Return a (Web3, contract) tuple using the first working RPC for the chain.
    Raises RuntimeError if no RPC connects.
    """
    chain_config = CHAINS[chain_name]
    rpcs = chain_config.get("rpcs") or ([chain_config.get("rpc")] if chain_config.get("rpc") else [])

    last_err = None
    for rpc in rpcs:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc))
            if not _rpc_works(w3):
                continue
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(chain_config["morpho"]),
                abi=ABI,
            )
            return w3, contract
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Could not connect to any RPC for chain '{chain_name}': {last_err}")
