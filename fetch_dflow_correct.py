#!/usr/bin/env python3
"""
DFlow Event Fetcher - Using CORRECT discriminator
Discriminator: e445a52e51cb9a1d (first 8 bytes from actual event data)
"""

import json
import requests
import base64
import base58
import struct
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configuration
PROGRAM_ID = "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH"
HELIUS_API_KEY = "40cc947b-4381-47a9-b554-5b693c015ac6"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
HELIUS_BASE_URL = f"https://api.helius.xyz/v0"

# CORRECT SwapEvent discriminator from your data
SWAP_EVENT_DISCRIMINATOR = bytes([0xe4, 0x45, 0xa5, 0x2e, 0x51, 0xcb, 0x9a, 0x1d])
# This is: [228, 69, 165, 46, 81, 203, 154, 29]


def decode_swap_event_from_data(data: bytes, start_offset: int = 0) -> Optional[Dict[str, Any]]:
    """
    Decode SwapEvent using the correct discriminator.
    Structure:
    - Bytes 0-7: Discriminator (e445a52e51cb9a1d)
    - Bytes 8-15: Unknown/padding field (skip)
    - Bytes 16-47: AMM (32 bytes)
    - Bytes 48-79: Input Mint (32 bytes)
    - Bytes 80-87: Input Amount (8 bytes, u64)
    - Bytes 88-119: Output Mint (32 bytes)
    - Bytes 120-127: Output Amount (8 bytes, u64)
    """
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
            "inputAmount": str(input_amount),
            "outputMint": output_mint,
            "outputAmount": str(output_amount),
            "source": "anchor_event"
        }
    except Exception as e:
        print(f"  Error decoding: {e}")
        return None


def extract_swap_events_from_logs(logs: List[str]) -> List[Dict[str, Any]]:
    """Extract SwapEvent data from transaction logs using correct discriminator."""
    events = []

    for log in logs:
        if "Program data:" in log:
            try:
                # Extract base64 data
                data_str = log.split("Program data: ")[1].strip()
                event_data = base64.b64decode(data_str)

                # Check if this is a swap event (discriminator at start)
                if len(event_data) >= 128 and event_data[:8] == SWAP_EVENT_DISCRIMINATOR:
                    decoded_event = decode_swap_event_from_data(event_data, 0)
                    if decoded_event:
                        events.append(decoded_event)
            except Exception as e:
                continue

    return events


def extract_events_from_inner_instructions(tx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract SwapEvent data from inner instructions (Anchor Self CPI).
    Inner instructions contain CPI calls that emit events via "Program data:" logs.
    """
    events = []

    # Get inner instructions
    inner_instructions = tx_data.get("meta", {}).get("innerInstructions", [])

    for inner_set in inner_instructions:
        for instruction in inner_set.get("instructions", []):
            # Check if this instruction has data
            if "data" in instruction:
                try:
                    # Decode the instruction data (base58 encoded)
                    import base58 as b58
                    inst_data = b58.b58decode(instruction["data"])

                    # Check if this contains the swap event discriminator
                    if len(inst_data) >= 128 and inst_data[:8] == SWAP_EVENT_DISCRIMINATOR:
                        decoded_event = decode_swap_event_from_data(inst_data, 0)
                        if decoded_event:
                            events.append(decoded_event)
                except Exception as e:
                    continue

    return events


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

    # Fetch full transaction with logs and inner instructions
    tx_with_logs = fetch_transaction_with_logs(signature)
    if tx_with_logs:
        # Method 1: Try to get from Program data logs
        logs = tx_with_logs.get("meta", {}).get("logMessages", [])
        log_events = extract_swap_events_from_logs(logs)

        for event_data in log_events:
            all_events.append({
                "tx_id": signature,
                "block_slot": slot,
                "block_time": timestamp,
                **event_data
            })

        # Method 2: Try to get from inner instructions (Anchor Self CPI)
        inner_events = extract_events_from_inner_instructions(tx_with_logs)

        for event_data in inner_events:
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
    print(f"Fetching DFlow program swap events")
    print(f"Using CORRECT discriminator: e445a52e51cb9a1d")
    print(f"Program: {PROGRAM_ID}\n")

    # Fetch transactions from Helius
    print("Fetching transactions from Helius...")
    transactions = fetch_parsed_transactions(limit=50)
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
    print(f"SUMMARY: Found {len(all_events)} SwapEvent(s) with CORRECT discriminator")
    print(f"{'='*80}")

    if all_events:
        print_table_header()

        for event in all_events:
            print_event_row(event)

        # Create outputs directory if it doesn't exist
        output_dir = "outputs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"\nCreated '{output_dir}' directory for storing results")

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/dflow_events_{timestamp}.json"

        # Also save to the main file for easy access
        main_output_file = "dflow_swap_events.json"

        # Export to timestamped JSON
        with open(output_file, 'w') as f:
            json.dump(all_events, f, indent=2)

        # Export to main JSON (overwrite)
        with open(main_output_file, 'w') as f:
            json.dump(all_events, f, indent=2)

        print(f"\n✅ Events exported to:")
        print(f"   - {output_file} (timestamped)")
        print(f"   - {main_output_file} (latest)")
    else:
        print("\nNo swap events found with this discriminator.")


if __name__ == "__main__":
    main()
