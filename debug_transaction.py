#!/usr/bin/env python3
"""
Debug script to inspect transaction structure and find SwapEvents
"""

import json
import requests
import base64
import base58

PROGRAM_ID = "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key=40cc947b-4381-47a9-b554-5b693c015ac6"

def fetch_transaction_details(signature: str):
    """Fetch detailed transaction information."""
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
    return response.json().get("result")

def fetch_recent_signatures(limit=5):
    """Fetch recent transaction signatures."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            PROGRAM_ID,
            {"limit": limit, "commitment": "confirmed"}
        ]
    }

    response = requests.post(HELIUS_RPC, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    return response.json().get("result", [])

# Fetch a recent transaction
print("Fetching recent transactions...")
sigs = fetch_recent_signatures(1)

if sigs:
    sig = sigs[0]["signature"]
    print(f"\nAnalyzing transaction: {sig}")

    tx_data = fetch_transaction_details(sig)

    if tx_data:
        # Save full transaction to file for inspection
        with open("transaction_debug.json", "w") as f:
            json.dump(tx_data, f, indent=2)
        print(f"Full transaction saved to: transaction_debug.json")

        # Print logs
        logs = tx_data.get("meta", {}).get("logMessages", [])
        print(f"\n=== Transaction Logs ({len(logs)} total) ===")
        for i, log in enumerate(logs):
            print(f"{i}: {log}")

        # Look for "Program data:" logs
        print("\n=== Program Data Logs ===")
        for i, log in enumerate(logs):
            if "Program data:" in log:
                print(f"\nLog #{i}: {log}")
                try:
                    data_str = log.split("Program data: ")[1].strip()
                    data_bytes = base64.b64decode(data_str)
                    print(f"  Length: {len(data_bytes)} bytes")
                    print(f"  First 16 bytes (hex): {data_bytes[:16].hex()}")
                    print(f"  First 8 bytes (discriminator): {list(data_bytes[:8])}")
                except Exception as e:
                    print(f"  Error decoding: {e}")

        # Check for inner instructions
        inner_instructions = tx_data.get("meta", {}).get("innerInstructions", [])
        print(f"\n=== Inner Instructions ({len(inner_instructions)} total) ===")
        for idx, inner in enumerate(inner_instructions):
            print(f"\nInner Instruction Set #{idx}:")
            print(f"  Index: {inner.get('index')}")
            print(f"  Instructions: {len(inner.get('instructions', []))}")
else:
    print("No transactions found")
