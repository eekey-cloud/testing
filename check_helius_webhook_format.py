#!/usr/bin/env python3
"""
Check if Helius webhook/enhanced API provides parsed events
According to Helius docs, enhanced webhooks include parsed instruction data
"""

import json
import requests

HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key=40cc947b-4381-47a9-b554-5b693c015ac6"
TX_SIG = "3yvsCSS9dDoKBqtoGcvRZtjbtFian5QC7caUkapcTTLfDTiyjUP4AhDhm8tYaYoXTdBqvLm71d2NTXxeZB4k3LP7"

# Try using parseTransaction RPC method (if available)
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "parseTransaction",
    "params": [TX_SIG]
}

response = requests.post(HELIUS_RPC, json=payload)
print(f"parseTransaction response: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2)[:1000])

# The issue is that Anchor events are emitted via CPI (Cross Program Invocation)
# and stored in the transaction's event logs in a specific format.
# Let me check the Anchor event CPI pattern

print("\n" + "="*80)
print("Based on your sample, the actual event data structure suggests:")
print("The swap events are embedded in instruction data or via Anchor's event CPI")
print("\nThe transaction you showed has:")
print("- AMM: pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
print("- Input: SOL (So11111...112), Amount: 70829627")
print("- Output: CdTwzpa...pump, Amount: 356249776231")
print("\nBut our decoded transaction shows token transfers that match the amounts")
print("Let me verify by checking the token transfers in the Helius data...")
