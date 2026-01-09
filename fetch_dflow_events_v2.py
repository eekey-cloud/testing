#!/usr/bin/env python3
"""
DFlow Program Event Fetcher v2
Uses Helius Enhanced Transactions API to fetch parsed SwapEvent data
"""

import json
import requests
from typing import List, Dict, Any
from datetime import datetime

# Configuration
PROGRAM_ID = "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH"
HELIUS_API_KEY = "40cc947b-4381-47a9-b554-5b693c015ac6"
HELIUS_BASE_URL = f"https://api.helius.xyz/v0"


def fetch_parsed_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch parsed transactions using Helius Enhanced Transactions API.
    This endpoint returns pre-parsed events including SwapEvent data.
    """
    url = f"{HELIUS_BASE_URL}/addresses/{PROGRAM_ID}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": limit,
        "type": "SWAP"  # Filter for swap transactions
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching parsed transactions: {e}")
        # Try without type filter
        params.pop("type", None)
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()


def extract_swap_events(tx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract SwapEvent data from Helius parsed transaction.
    """
    events = []

    # Get transaction metadata
    signature = tx.get("signature", "")
    slot = tx.get("slot", 0)
    timestamp = tx.get("timestamp", 0)

    # Check for events in the transaction
    # Helius may provide events in different locations depending on the API version

    # Method 1: Check 'events' field
    if "events" in tx:
        for event in tx.get("events", []):
            if event.get("type") == "SWAP" or "swap" in event.get("type", "").lower():
                events.append({
                    "tx_id": signature,
                    "block_slot": slot,
                    "block_time": timestamp,
                    "event_data": event
                })

    # Method 2: Check 'instructions' for swap data
    if "instructions" in tx:
        for instruction in tx.get("instructions", []):
            if instruction.get("programId") == PROGRAM_ID:
                # Check for parsed data
                if "parsed" in instruction:
                    parsed = instruction["parsed"]
                    if "swapEvent" in str(parsed).lower():
                        events.append({
                            "tx_id": signature,
                            "block_slot": slot,
                            "block_time": timestamp,
                            "event_data": parsed
                        })

    # Method 3: Check nativeTransfers or tokenTransfers (Helius enriched data)
    # Look for swap-like patterns in token transfers
    token_transfers = tx.get("tokenTransfers", [])
    if len(token_transfers) >= 2 and not events:
        # This might be a swap - record it
        events.append({
            "tx_id": signature,
            "block_slot": slot,
            "block_time": timestamp,
            "event_data": {
                "type": "inferred_swap",
                "tokenTransfers": token_transfers
            }
        })

    return events


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to readable format."""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return "N/A"


def print_table_header():
    """Print table header."""
    print("\n" + "="*180)
    print(f"{'TX_ID':<88} {'SLOT':<12} {'TIME':<20}")
    print(f"{'AMM':<44} {'INPUT_MINT':<44}")
    print(f"{'INPUT_AMOUNT':<20} {'OUTPUT_MINT':<44} {'OUTPUT_AMOUNT':<20}")
    print("="*180)


def print_event_row(event: Dict[str, Any]):
    """Print a single event as a table row."""
    tx_id = event.get("tx_id", "N/A")
    slot = event.get("block_slot", "N/A")
    time = format_timestamp(event.get("block_time"))

    # Try to extract swap data from various formats
    data = event.get("event_data", {})

    # Try to get standard swap event fields
    amm = data.get("amm", "N/A")
    input_mint = data.get("inputMint", "N/A")
    input_amount = data.get("inputAmount", "N/A")
    output_mint = data.get("outputMint", "N/A")
    output_amount = data.get("outputAmount", "N/A")

    print(f"{tx_id:<88} {slot:<12} {time:<20}")
    print(f"{amm:<44} {input_mint:<44}")
    print(f"{input_amount:<20} {output_mint:<44} {output_amount:<20}")
    print("-"*180)

    # Also print the raw event data for debugging
    if data:
        print(f"  Raw event data: {json.dumps(data, indent=2)[:200]}...")
        print("-"*180)


def main():
    """Main execution function."""
    print(f"Fetching DFlow program transactions from Helius Enhanced API")
    print(f"Program: {PROGRAM_ID}")

    # Fetch parsed transactions
    print("\nFetching transactions...")
    transactions = fetch_parsed_transactions(limit=50)
    print(f"Found {len(transactions)} transactions")

    # Process each transaction
    all_events = []

    for tx in transactions:
        signature = tx.get("signature", "unknown")[:16]
        print(f"Processing: {signature}...")

        events = extract_swap_events(tx)
        all_events.extend(events)

    # Display results
    if all_events:
        print(f"\nFound {len(all_events)} event(s)")
        print_table_header()

        for event in all_events:
            print_event_row(event)

        # Export to JSON
        output_file = "dflow_events_v2.json"
        with open(output_file, 'w') as f:
            json.dump(all_events, f, indent=2)
        print(f"\nEvents exported to: {output_file}")

        # Also save raw transactions for debugging
        with open("raw_transactions.json", 'w') as f:
            json.dump(transactions[:5], f, indent=2)
        print(f"Sample raw transactions saved to: raw_transactions.json")
    else:
        print("\nNo events found in transactions.")
        print("Saving sample transaction for debugging...")
        if transactions:
            with open("sample_transaction.json", 'w') as f:
                json.dump(transactions[0], f, indent=2)
            print("Sample saved to: sample_transaction.json")


if __name__ == "__main__":
    main()
