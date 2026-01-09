#!/usr/bin/env python3
"""
Multi-Protocol Arbitrage Detector
Fetches swap events in real-time from DFlow and Jupiter and identifies atomic arbitrage opportunities.

An atomic arbitrage is a sequence of swaps within a single transaction where:
- The final output token is the same as the initial input token
- The net amount is positive (profit)
"""

import json
import requests
import base64
import base58
import struct
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

# Protocol Configurations
PROTOCOLS = {
    "dflow": {
        "program_id": "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH",
        "api_key": "40cc947b-4381-47a9-b554-5b693c015ac6",
        "discriminator": bytes([0xe4, 0x45, 0xa5, 0x2e, 0x51, 0xcb, 0x9a, 0x1d])
    },
    "jupiter": {
        "program_id": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
        "api_key": "b84cd4c8-22cd-439b-a9d4-064dae398e5c",
        "discriminator": bytes([0xe4, 0x45, 0xa5, 0x2e, 0x51, 0xcb, 0x9a, 0x1d])  # Using same discriminator
    }
}

# Tracking per protocol
protocol_data = {
    "dflow": {
        "processed_signatures": set(),
        "all_swaps": [],
        "arbitrage_opportunities": []
    },
    "jupiter": {
        "processed_signatures": set(),
        "all_swaps": [],
        "arbitrage_opportunities": []
    }
}


def decode_swap_event_from_data(data: bytes, start_offset: int = 0) -> Optional[Dict[str, Any]]:
    """Decode SwapEvent using the correct discriminator."""
    offset = start_offset + 16  # Skip discriminator (8) + unknown field (8)

    try:
        # Parse amm (32 bytes)
        amm = base58.b58encode(data[offset:offset+32]).decode('utf-8')
        offset += 32

        # Parse inputMint (32 bytes)
        input_mint = base58.b58encode(data[offset:offset+32]).decode('utf-8')
        offset += 32

        # Parse inputAmount (8 bytes, little-endian u64)
        input_amount = struct.unpack('<Q', data[offset:offset+8])[0]
        offset += 8

        # Parse outputMint (32 bytes)
        output_mint = base58.b58encode(data[offset:offset+32]).decode('utf-8')
        offset += 32

        # Parse outputAmount (8 bytes, little-endian u64)
        output_amount = struct.unpack('<Q', data[offset:offset+8])[0]

        return {
            "amm": amm,
            "inputMint": input_mint,
            "inputAmount": int(input_amount),
            "outputMint": output_mint,
            "outputAmount": int(output_amount)
        }
    except Exception:
        return None


def extract_events_from_inner_instructions(tx_data: Dict[str, Any], discriminator: bytes) -> List[Dict[str, Any]]:
    """Extract SwapEvent data from inner instructions (Anchor Self CPI)."""
    events = []
    inner_instructions = tx_data.get("meta", {}).get("innerInstructions", [])

    for inner_set in inner_instructions:
        instruction_index = inner_set.get("index", 0)
        for instruction in inner_set.get("instructions", []):
            if "data" in instruction:
                try:
                    inst_data = base58.b58decode(instruction["data"])
                    if len(inst_data) >= 128 and inst_data[:8] == discriminator:
                        decoded_event = decode_swap_event_from_data(inst_data, 0)
                        if decoded_event:
                            decoded_event["instruction_index"] = instruction_index
                            events.append(decoded_event)
                except Exception:
                    continue

    # Sort by instruction index to maintain order
    events.sort(key=lambda x: x.get("instruction_index", 0))
    return events


def fetch_transaction_with_logs(signature: str, rpc_url: str) -> Optional[Dict[str, Any]]:
    """Fetch transaction details including logs."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "json",
                "commitment": "confirmed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }

    try:
        response = requests.post(rpc_url, json=payload)
        response.raise_for_status()
        return response.json().get("result")
    except Exception:
        return None


def fetch_recent_transactions(program_id: str, api_key: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch recent transactions using Helius Enhanced API."""
    url = f"https://api.helius.xyz/v0/addresses/{program_id}/transactions"
    params = {
        "api-key": api_key,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []


def detect_arbitrage(swaps: List[Dict[str, Any]], tx_id: str, slot: int, timestamp: int) -> Optional[Dict[str, Any]]:
    """
    Detect atomic arbitrage in a transaction's swaps.

    Logic:
    1. Order swaps by instruction index
    2. Track token flow: input (negative) -> output (positive)
    3. Check if final token equals initial token with net positive amount
    """
    if len(swaps) < 2:
        return None

    # Create ordered token flow
    token_balances = defaultdict(int)
    amms_involved = []
    token_path = []

    for swap in swaps:
        # Record AMM
        if swap["amm"] not in amms_involved:
            amms_involved.append(swap["amm"])

        # Input: decrease balance (negative)
        token_balances[swap["inputMint"]] -= swap["inputAmount"]
        if swap["inputMint"] not in token_path:
            token_path.append(swap["inputMint"])

        # Output: increase balance (positive)
        token_balances[swap["outputMint"]] += swap["outputAmount"]
        if swap["outputMint"] not in token_path:
            token_path.append(swap["outputMint"])

    # Check for arbitrage: any token with positive net balance
    arbitrage_found = False
    arbitrage_tokens = []

    for token, balance in token_balances.items():
        if balance > 0:
            arbitrage_found = True
            arbitrage_tokens.append({
                "mint": token,
                "profit": balance
            })

    # Check if it's a closed loop (start and end with same token)
    first_input = swaps[0]["inputMint"]
    last_output = swaps[-1]["outputMint"]
    is_closed_loop = (first_input == last_output)

    # ONLY return if it's a closed loop arbitrage with profit
    if is_closed_loop and arbitrage_found and len(swaps) >= 2:
        # Verify the closed loop token has positive balance
        if token_balances[first_input] > 0:
            return {
                "tx_id": tx_id,
                "block_slot": slot,
                "block_time": timestamp,
                "timestamp": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                "num_swaps": len(swaps),
                "amms": amms_involved,
                "token_path": token_path,
                "profit_token": first_input,
                "profit_amount": token_balances[first_input],
                "swaps": swaps
            }

    return None


def process_transaction(tx: Dict[str, Any], protocol: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single transaction and detect arbitrage."""
    signature = tx.get("signature", "")

    data = protocol_data[protocol]

    # Skip if already processed
    if signature in data["processed_signatures"]:
        return None

    data["processed_signatures"].add(signature)

    slot = tx.get("slot", 0)
    timestamp = tx.get("timestamp", 0)

    # Fetch full transaction with inner instructions
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={config['api_key']}"
    tx_with_logs = fetch_transaction_with_logs(signature, rpc_url)
    if not tx_with_logs:
        return None

    # Extract swap events (ordered)
    swaps = extract_events_from_inner_instructions(tx_with_logs, config["discriminator"])

    if not swaps:
        return None

    # Store all swaps
    for swap in swaps:
        data["all_swaps"].append({
            "tx_id": signature,
            "block_slot": slot,
            "block_time": timestamp,
            **swap
        })

    # Detect arbitrage
    return detect_arbitrage(swaps, signature, slot, timestamp)


def run_for_duration(duration_seconds: int = 180):
    """Run the arbitrage detector for a specified duration."""
    print(f"Starting multi-protocol arbitrage detection for {duration_seconds} seconds...")
    print(f"Protocols: DFlow & Jupiter\n")

    start_time = time.time()
    iteration = 0

    while (time.time() - start_time) < duration_seconds:
        iteration += 1
        elapsed = int(time.time() - start_time)
        remaining = duration_seconds - elapsed

        print(f"\n[Iteration {iteration}] Elapsed: {elapsed}s | Remaining: {remaining}s")

        # Process both protocols
        for protocol_name, config in PROTOCOLS.items():
            # Fetch recent transactions
            transactions = fetch_recent_transactions(config["program_id"], config["api_key"], limit=50)
            print(f"  [{protocol_name.upper()}] Fetched {len(transactions)} transactions")

            data = protocol_data[protocol_name]

            # Process each transaction
            new_arbitrages = 0
            for tx in transactions:
                arbitrage = process_transaction(tx, protocol_name, config)
                if arbitrage:
                    data["arbitrage_opportunities"].append(arbitrage)
                    new_arbitrages += 1

            if new_arbitrages > 0:
                print(f"  [{protocol_name.upper()}] ✓ Found {new_arbitrages} new arbitrage(s)!")

            print(f"  [{protocol_name.upper()}] Total: {len(data['all_swaps'])} swaps, {len(data['arbitrage_opportunities'])} arbitrages")

        # Wait before next iteration (avoid rate limits)
        if remaining > 0:
            time.sleep(min(5, remaining))

    print(f"\n{'='*80}")
    print(f"COMPLETED: Ran for {duration_seconds} seconds")
    print(f"{'='*80}")


def print_summary():
    """Print summary of findings."""
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")

    for protocol_name in PROTOCOLS.keys():
        data = protocol_data[protocol_name]
        print(f"\n[{protocol_name.upper()}]")
        print(f"  Total Swaps Collected: {len(data['all_swaps'])}")
        print(f"  Total Arbitrage Opportunities: {len(data['arbitrage_opportunities'])}")
        print(f"  Unique Transactions: {len(data['processed_signatures'])}")


def print_sample_swaps(limit: int = 10):
    """Print sample swap events."""
    print(f"\n{'='*80}")
    print(f"SAMPLE SWAP EVENTS (First {limit} per protocol)")
    print(f"{'='*80}")

    for protocol_name in PROTOCOLS.keys():
        data = protocol_data[protocol_name]
        print(f"\n[{protocol_name.upper()}]")

        for i, swap in enumerate(data['all_swaps'][:limit]):
            print(f"  [{i+1}] TX: {swap['tx_id'][:16]}...")
            print(f"      AMM: {swap['amm']}")
            print(f"      {swap['inputMint'][:20]}... ({swap['inputAmount']}) -> {swap['outputMint'][:20]}... ({swap['outputAmount']})")


def save_results():
    """Save results to JSON files (4 files total: 2 arbitrages + 2 swaps)."""
    print(f"\n{'='*80}")
    print(f"RESULTS SAVED")
    print(f"{'='*80}")

    for protocol_name in PROTOCOLS.keys():
        data = protocol_data[protocol_name]

        # Extract only transaction IDs from arbitrage opportunities
        arbitrage_tx_ids = [arb["tx_id"] for arb in data["arbitrage_opportunities"]]

        # Save arbitrages_{protocol}.json (only transaction IDs, overwrites existing)
        arb_file = f"{protocol_name}_arbitrages.json"
        with open(arb_file, 'w') as f:
            json.dump(arbitrage_tx_ids, f, indent=2)

        # Save swaps_{protocol}.json (limit to 100 transactions, overwrites existing)
        # Group swaps by transaction and limit to 100 txns
        swaps_by_txn = {}
        for swap in data["all_swaps"]:
            tx_id = swap["tx_id"]
            if tx_id not in swaps_by_txn:
                if len(swaps_by_txn) >= 100:
                    break
                swaps_by_txn[tx_id] = []
            swaps_by_txn[tx_id].append(swap)

        # Flatten back to list
        swaps_limited = []
        for swaps in swaps_by_txn.values():
            swaps_limited.extend(swaps)

        swaps_file = f"{protocol_name}_swaps.json"
        with open(swaps_file, 'w') as f:
            json.dump(swaps_limited, f, indent=2)

        print(f"\n[{protocol_name.upper()}]")
        print(f"  ✅ Arbitrages (txn IDs only): {arb_file}")
        print(f"  ✅ Swaps (max 100 txns): {swaps_file}")


def print_arbitrage_details():
    """Print detailed arbitrage information."""
    print(f"\n{'='*80}")
    print(f"ARBITRAGE OPPORTUNITIES FOUND")
    print(f"{'='*80}")

    for protocol_name in PROTOCOLS.keys():
        data = protocol_data[protocol_name]
        arbitrage_opportunities = data["arbitrage_opportunities"]

        print(f"\n[{protocol_name.upper()}] {len(arbitrage_opportunities)} arbitrages")

        if not arbitrage_opportunities:
            print("  No arbitrage opportunities found.")
            continue

        for i, arb in enumerate(arbitrage_opportunities[:5]):  # Show first 5 only
            print(f"\n  [{i+1}] TX: {arb['tx_id']}")
            print(f"      Time: {arb['timestamp']}")
            print(f"      Swaps: {arb['num_swaps']}")
            print(f"      AMMs: {', '.join([amm[:16] + '...' for amm in arb['amms']])}")
            print(f"      Token Path: {len(arb['token_path'])} tokens")
            print(f"      Profit Token: {arb['profit_token'][:20]}...")
            print(f"      Profit Amount: +{arb['profit_amount']}")


def main():
    """Main execution function."""
    # Step 1: Run for 3 minutes
    run_for_duration(duration_seconds=180)

    # Step 2: Print all outputs
    print_summary()

    # Step 3 & 4: Extract and identify arbitrages (done during processing)
    print_arbitrage_details()

    # Step 10: Print sample swaps (max 10)
    print_sample_swaps(limit=10)

    # Step 5: Store arbitrages
    save_results()


if __name__ == "__main__":
    main()
