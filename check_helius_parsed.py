#!/usr/bin/env python3
"""
Check Helius parsed/enhanced transaction for events
"""

import json
import requests

HELIUS_API_KEY = "40cc947b-4381-47a9-b554-5b693c015ac6"
TX_SIG = "3yvsCSS9dDoKBqtoGcvRZtjbtFian5QC7caUkapcTTLfDTiyjUP4AhDhm8tYaYoXTdBqvLm71d2NTXxeZB4k3LP7"

# Try Helius enhanced transactions endpoint
url = f"https://api.helius.xyz/v0/transactions"
params = {
    "api-key": HELIUS_API_KEY,
    "transactions": [TX_SIG]
}

print(f"Fetching enhanced transaction from Helius...")
response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    with open("helius_enhanced_tx.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to: helius_enhanced_tx.json")

    if data and len(data) > 0:
        tx = data[0]

        # Check for events field
        if "events" in tx:
            print(f"\n=== Found 'events' field ===")
            print(json.dumps(tx["events"], indent=2))

        # Check for instructions
        if "instructions" in tx:
            print(f"\n=== Instructions ({len(tx['instructions'])}) ===")
            for i, inst in enumerate(tx["instructions"]):
                if "parsed" in inst or "events" in inst:
                    print(f"\nInstruction #{i}:")
                    print(json.dumps(inst, indent=2)[:500])

        # Look for any field containing "swap" or "event"
        print(f"\n=== Keys in transaction ===")
        for key in tx.keys():
            if "swap" in key.lower() or "event" in key.lower():
                print(f"  - {key}: {type(tx[key])}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
