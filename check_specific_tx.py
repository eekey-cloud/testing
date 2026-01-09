#!/usr/bin/env python3
"""
Check the specific transaction that should have the swap event
"""

import json
import requests

HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key=40cc947b-4381-47a9-b554-5b693c015ac6"
TX_SIG = "3yvsCSS9dDoKBqtoGcvRZtjbtFian5QC7caUkapcTTLfDTiyjUP4AhDhm8tYaYoXTdBqvLm71d2NTXxeZB4k3LP7"

def fetch_transaction(signature: str):
    """Fetch transaction details."""
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

print(f"Fetching transaction: {TX_SIG[:16]}...")
tx_data = fetch_transaction(TX_SIG)

if tx_data:
    # Save to file
    with open("specific_tx.json", "w") as f:
        json.dump(tx_data, f, indent=2)
    print("Transaction saved to: specific_tx.json")

    # Check logs for Program data
    logs = tx_data.get("meta", {}).get("logMessages", [])
    print(f"\nFound {len(logs)} log messages")

    program_data_logs = [log for log in logs if "Program data:" in log]
    print(f"Found {len(program_data_logs)} 'Program data:' logs")

    for i, log in enumerate(program_data_logs):
        print(f"\nProgram data log #{i}:")
        print(log)

    # Check for program return data
    if "returnData" in tx_data.get("meta", {}):
        print("\n=== Return Data Found ===")
        return_data = tx_data["meta"]["returnData"]
        print(json.dumps(return_data, indent=2))

    # Check inner instructions
    inner_instructions = tx_data.get("meta", {}).get("innerInstructions", [])
    print(f"\n=== Inner Instructions: {len(inner_instructions)} ===")

else:
    print("Transaction not found")
