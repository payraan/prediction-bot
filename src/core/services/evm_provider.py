"""
EVM Provider (ERC20 / BEP20)
- Fetch incoming USDT transfers via eth_getLogs RPC
- Works for both Ethereum (ERC20) and BSC (BEP20)
"""

import httpx
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.core.config import EVM_RPC_URLS, EVM_TOKEN_CONTRACTS, EVM_CONFIRMATIONS

# ERC20 Transfer event signature: Transfer(address,address,uint256)
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _chunks(lst, n: int):
    for k in range(0, len(lst), n):
        yield lst[k:k+n]


def _address_to_topic(addr: str) -> str:
    """Convert 0x address to 32-byte topic (zero-padded)"""
    return "0x" + addr.lower().replace("0x", "").zfill(64)


async def _rpc_call(rpc_url: str, method: str, params: list) -> Any:
    """Generic JSON-RPC call"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data.get("result")


async def fetch_incoming_evm_transfers(
    addresses: List[str],
    network: str,
    asset: str = "USDT",
    from_block: Optional[int] = None,
    block_range: int = 5000,
) -> List[Dict[str, Any]]:
    """
    Fetch confirmed ERC20/BEP20 Transfer events to given addresses.
    
    Returns list of:
      - hash: str (tx hash)
      - amount: Decimal (human units, 6 decimals for USDT)
      - to_address: str
      - from_address: str
      - timestamp: int (block number as proxy, 0 if unknown)
      - log_index: int
    """
    rpc_url = EVM_RPC_URLS.get(network)
    if not rpc_url:
        print(f"⚠️ No RPC URL for network {network}")
        return []

    token_contract = EVM_TOKEN_CONTRACTS.get((asset, network))
    if not token_contract:
        print(f"⚠️ No token contract for {asset}/{network}")
        return []

    min_confirmations = EVM_CONFIRMATIONS.get(network, 12)

    if not addresses:
        return []

    try:
        # Get latest block
        latest_hex = await _rpc_call(rpc_url, "eth_blockNumber", [])
        latest_block = int(latest_hex, 16)
        safe_block = latest_block - min_confirmations

        if safe_block <= 0:
            return []

        # Determine from_block
        if from_block is None:
            from_block = max(safe_block - block_range, 0)

        if from_block > safe_block:
            return []

        # Build address topics (batch addresses into one query)
        addr_topics = [_address_to_topic(a) for a in addresses]

        # eth_getLogs: filter Transfer events TO our addresses        # eth_getLogs: filter Transfer events TO our addresses
        # IMPORTANT: batch address topics to avoid RPC limits/timeouts
        all_logs = []
        for addr_topics_chunk in _chunks(addr_topics, 50):
            log_filter = {
                "fromBlock": hex(from_block),
                "toBlock": hex(safe_block),
                "address": token_contract,
                "topics": [
                    TRANSFER_TOPIC,    # topic[0] = Transfer event
                    None,              # topic[1] = from (any)
                    addr_topics_chunk, # topic[2] = to (batched)
                ],
            }
            chunk_logs = await _rpc_call(rpc_url, "eth_getLogs", [log_filter])
            if chunk_logs:
                all_logs.extend(chunk_logs)

        logs = all_logs
        if not logs:
            return []

        out: List[Dict[str, Any]] = []

        # Build lookup set for fast matching
        addr_set = {a.lower() for a in addresses}

        for log in logs:
            tx_hash = log.get("transactionHash", "")
            if not tx_hash:
                continue

            # Parse topics
            topics = log.get("topics", [])
            if len(topics) < 3:
                continue

            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]

            if to_addr.lower() not in addr_set:
                continue

            # Parse amount from data (uint256, USDT = 6 decimals)
            raw_data = log.get("data", "0x0")
            try:
                raw_amount = int(raw_data, 16)
                amount = Decimal(raw_amount) / Decimal(10 ** 6)
            except Exception:
                continue

            if amount <= 0:
                continue

            log_index = int(log.get("logIndex", "0x0"), 16)
            block_num = int(log.get("blockNumber", "0x0"), 16)

            out.append({
                "hash": tx_hash,
                "amount": amount,
                "to_address": to_addr,
                "from_address": from_addr,
                "timestamp": block_num,
                "log_index": log_index,
                "memo": None,
            })

        return out

    except Exception as e:
        print(f"❌ Error fetching EVM transfers ({network}): {e}")
        return []
