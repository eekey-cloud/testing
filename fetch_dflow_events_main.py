#!/usr/bin/env python3
"""
DFlow Event Fetcher v3 - Properly decodes Anchor CPI events
Anchor events are emitted via anchor Self CPI and encoded in a specific format
"""

import json
import requests
import base64
import base58
import struct
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configuration
PROGRAM_ID = "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH"
HELIUS_API_KEY = "40cc947b-4381-47a9-b554-5b693c015ac6"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
HELIUS_BASE_URL = f"https://api.helius.xyz/v0"

# SwapEvent discriminator
SWAP_EVENT_DISCRIMINATOR = bytes([64, 198, 205, 232, 38, 8, 113, 226])


def decode_swap_event_from_anchor_cpi(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Decode SwapEvent from Anchor CPI event data.
    Anchor events in "Program data:" logs may have additional wrapper bytes.
    """
    # Try to find the discriminator in the data
    for start_offset in [0, 8, 16, 24]:  # Try common offsets
        if len(data) < start_offset + 8:
            continue

        if data[start_offset:start_offset+8] == SWAP_EVENT_DISCRIMINATOR:
            offset = start_offset + 8

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
                    "inputAmount": str(input_amount),
                    "outputMint": output_mint,
                    "outputAmount": str(output_amount),
                    "source": "anchor_event"
                }
            except Exception as e:
                continue

    return None


def fetch_transaction_with_logs(signature: str) -> Optional[Dict[str, Any]]:
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
        response = requests.post(HELIUS_RPC, json=payload)
        response.raise_for_status()
        return response.json().get("result")
    except Exception as e:
        return None


def extract_swap_events_from_logs(logs: List[str]) -> List[Dict[str, Any]]:
    """Extract SwapEvent data from transaction logs."""
    events = []

    for log in logs:
        if "Program data:" in log:
            try:
                # Extract base64 data
                data_str = log.split("Program data: ")[1].strip()
                event_data = base64.b64decode(data_str)

                # Try to decode as SwapEvent
                decoded_event = decode_swap_event_from_anchor_cpi(event_data)

                if decoded_event:
                    events.append(decoded_event)
            except Exception:
                continue

    return events


def fetch_parsed_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch parsed transactions using Helius Enhanced API."""
    url = f"{HELIUS_BASE_URL}/addresses/{PROGRAM_ID}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from Helius API: {e}")
        return []


def process_transaction(tx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process a single transaction and extract all swap events."""
    signature = tx.get("signature", "")
    slot = tx.get("slot", 0)
    timestamp = tx.get("timestamp", 0)

    all_events = []

    # Fetch full transaction with logs
    tx_with_logs = fetch_transaction_with_logs(signature)
    if tx_with_logs:
        logs = tx_with_logs.get("meta", {}).get("logMessages", [])
        log_events = extract_swap_events_from_logs(logs)

        for event_data in log_events:
            all_events.append({
                "tx_id": signature,
                "block_slot": slot,
                "block_time": timestamp,
                **event_data
            })

    return all_events


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to readable format."""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return "N/A"


def print_table_header():
    """Print table header."""
    print("\n" + "="*200)
    print(f"{'TX_ID':<88} {'SLOT':<12} {'TIME':<20}")
    print(f"{'AMM':<44} {'INPUT_MINT':<44}")
    print(f"{'INPUT_AMOUNT':<25} {'OUTPUT_MINT':<44} {'OUTPUT_AMOUNT':<25}")
    print("="*200)


def print_event_row(event: Dict[str, Any]):
    """Print a single event as a table row."""
    tx_id = event.get("tx_id", "N/A")
    slot = event.get("block_slot", "N/A")
    time = format_timestamp(event.get("block_time"))

    amm = event.get("amm", "N/A")
    input_mint = event.get("inputMint", "N/A")
    input_amount = event.get("inputAmount", "N/A")
    output_mint = event.get("outputMint", "N/A")
    output_amount = event.get("outputAmount", "N/A")

    print(f"{tx_id:<88} {slot:<12} {time:<20}")
    print(f"{amm:<44} {input_mint:<44}")
    print(f"{input_amount:<25} {output_mint:<44} {output_amount:<25}")
    print("-"*200)


def main():
    """Main execution function."""
    print(f"Fetching DFlow program swap events (Anchor CPI format)")
    print(f"Program: {PROGRAM_ID}\n")

    # Fetch transactions from Helius
    print("Fetching transactions from Helius...")
    transactions = fetch_parsed_transactions(limit=30)
    print(f"Found {len(transactions)} transactions\n")

    # Process each transaction
    all_events = []

    for i, tx in enumerate(transactions):
        signature = tx.get("signature", "unknown")
        print(f"[{i+1}/{len(transactions)}] Processing: {signature[:16]}...", end="")

        events = process_transaction(tx)
        all_events.extend(events)

        if events:
            print(f" → Found {len(events)} event(s)")
        else:
            print()

    # Display results
    print(f"\n{'='*80}")
    print(f"SUMMARY: Found {len(all_events)} SwapEvent(s) total (from Anchor CPI logs)")
    print(f"{'='*80}")

    if all_events:
        print_table_header()

        for event in all_events:
            print_event_row(event)

        # Export to JSON
        output_file = "dflow_swap_events_v3.json"
        with open(output_file, 'w') as f:
            json.dump(all_events, f, indent=2)
        print(f"\nAll events exported to: {output_file}")
    else:
        print("\nNo swap events found in Anchor CPI logs.")
        print("This might mean:")
        print("  - Events are encoded differently")
        print("  - Need to check instruction data or inner instructions")


if __name__ == "__main__":
    main()
