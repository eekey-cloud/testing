#!/usr/bin/env python3
"""
DFlow Program Event Fetcher
Fetches SwapEvent transactions from the DFlow program and decodes them into a table format.
"""

import json
import requests
import base64
import struct
from typing import List, Dict, Any
from datetime import datetime

# Configuration
PROGRAM_ID = "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key=40cc947b-4381-47a9-b554-5b693c015ac6"

# SwapEvent discriminator
SWAP_EVENT_DISCRIMINATOR = bytes([64, 198, 205, 232, 38, 8, 113, 226])


def decode_swap_event(data: bytes) -> Dict[str, Any]:
    """
    Decode SwapEvent from program log data.

    Expected structure after discriminator (8 bytes):
    - amm: 32 bytes (pubkey)
    - inputMint: 32 bytes (pubkey)
    - inputAmount: 8 bytes (u64)
    - outputMint: 32 bytes (pubkey)
    - outputAmount: 8 bytes (u64)
    """
    if len(data) < 8:
        return None

    # Check discriminator
    if data[:8] != SWAP_EVENT_DISCRIMINATOR:
        return None

    offset = 8

    try:
        # Parse amm (32 bytes)
        amm = base64.b58encode(data[offset:offset+32]).decode('utf-8')
        offset += 32

        # Parse inputMint (32 bytes)
        input_mint = base64.b58encode(data[offset:offset+32]).decode('utf-8')
        offset += 32

        # Parse inputAmount (8 bytes, little-endian u64)
        input_amount = struct.unpack('<Q', data[offset:offset+8])[0]
        offset += 8

        # Parse outputMint (32 bytes)
        output_mint = base64.b58encode(data[offset:offset+32]).decode('utf-8')
        offset += 32

        # Parse outputAmount (8 bytes, little-endian u64)
        output_amount = struct.unpack('<Q', data[offset:offset+8])[0]
        offset += 8

        return {
            "amm": amm,
            "inputMint": input_mint,
            "inputAmount": str(input_amount),
            "outputMint": output_mint,
            "outputAmount": str(output_amount)
        }
    except Exception as e:
        print(f"Error decoding event: {e}")
        return None


def fetch_program_transactions(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch transactions for the DFlow program using Helius RPC.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            PROGRAM_ID,
            {
                "limit": limit,
                "commitment": "confirmed"
            }
        ]
    }

    response = requests.post(HELIUS_RPC, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()

    result = response.json()
    return result.get("result", [])


def fetch_transaction_details(signature: str) -> Dict[str, Any]:
    """
    Fetch detailed transaction information including logs.
    """
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

    response = requests.post(HELIUS_RPC, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()

    result = response.json()
    return result.get("result")


def parse_transaction_for_events(tx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse transaction data to extract SwapEvent emissions.
    """
    events = []

    if not tx_data or tx_data.get("meta", {}).get("err"):
        return events

    # Extract basic transaction info
    tx_signature = None
    block_slot = tx_data.get("slot")
    block_time = tx_data.get("blockTime")

    # Parse logs for event data
    logs = tx_data.get("meta", {}).get("logMessages", [])

    for log in logs:
        # Look for program data logs that contain base64 encoded event data
        if "Program data:" in log:
            try:
                # Extract base64 data from log
                data_str = log.split("Program data: ")[1].strip()
                event_data = base64.b64decode(data_str)

                # Try to decode as SwapEvent
                decoded_event = decode_swap_event(event_data)

                if decoded_event:
                    events.append({
                        "block_slot": block_slot,
                        "block_time": block_time,
                        "event_data": decoded_event
                    })
            except Exception as e:
                continue

    return events


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to readable format."""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return "N/A"


def print_table_header():
    """Print table header."""
    print("\n" + "="*180)
    print(f"{'TX_ID':<88} {'SLOT':<12} {'TIME':<20} {'AMM':<44}")
    print(f"{'INPUT_MINT':<44} {'INPUT_AMOUNT':<20} {'OUTPUT_MINT':<44} {'OUTPUT_AMOUNT':<20}")
    print("="*180)


def print_event_row(tx_id: str, event: Dict[str, Any]):
    """Print a single event as a table row."""
    slot = event.get("block_slot", "N/A")
    time = format_timestamp(event.get("block_time"))
    data = event.get("event_data", {})

    print(f"{tx_id:<88} {slot:<12} {time:<20} {data.get('amm', 'N/A'):<44}")
    print(f"{data.get('inputMint', 'N/A'):<44} {data.get('inputAmount', 'N/A'):<20} {data.get('outputMint', 'N/A'):<44} {data.get('outputAmount', 'N/A'):<20}")
    print("-"*180)


def main():
    """Main execution function."""
    print(f"Fetching DFlow program events from: {PROGRAM_ID}")
    print(f"Using Helius RPC endpoint")

    # Fetch recent transactions
    print("\nFetching recent transactions...")
    signatures = fetch_program_transactions(limit=20)
    print(f"Found {len(signatures)} recent transactions")

    # Process each transaction
    all_events = []

    for sig_info in signatures:
        signature = sig_info["signature"]
        print(f"Processing transaction: {signature[:16]}...")

        # Fetch transaction details
        tx_data = fetch_transaction_details(signature)

        if not tx_data:
            continue

        # Parse for events
        events = parse_transaction_for_events(tx_data)

        for event in events:
            all_events.append({
                "tx_id": signature,
                **event
            })

    # Display results
    if all_events:
        print(f"\nFound {len(all_events)} SwapEvent(s)")
        print_table_header()

        for event in all_events:
            print_event_row(event["tx_id"], event)

        # Export to JSON
        output_file = "dflow_events.json"
        with open(output_file, 'w') as f:
            json.dump(all_events, f, indent=2)
        print(f"\nEvents exported to: {output_file}")
    else:
        print("\nNo SwapEvents found in recent transactions.")
        print("This could mean:")
        print("  - No swap events in the last 20 transactions")
        print("  - Events are encoded differently than expected")
        print("  - Need to adjust the event parsing logic")


if __name__ == "__main__":
    main()
