#!/usr/bin/env python3
"""
Test decoding the instruction event data you provided
"""

import base58
import struct

# Your instruction event data
event_data_hex = "e445a52e51cb9a1d40c6cde8260871e20c14defc825ec67694250818bb654065f4298d3156d571b4d4f8090c18e9a863069b8857feab8184fb687f634618c035dac439dc1aeb3b5598a0f000000000013bc6380400000000acc7ef8e8bfd2fbc97cf116328b551b666b89f71357d5b24f9ca1bb36caa15df673024f252000000"

# Convert hex to bytes
data = bytes.fromhex(event_data_hex)

print(f"Total length: {len(data)} bytes")
print(f"First 8 bytes (discriminator): {list(data[:8])}")
print(f"First 8 bytes (hex): {data[:8].hex()}")

# Expected discriminator for SwapEvent
SWAP_EVENT_DISCRIMINATOR = bytes([64, 198, 205, 232, 38, 8, 113, 226])
print(f"\nExpected discriminator: {list(SWAP_EVENT_DISCRIMINATOR)}")
print(f"Match: {data[:8] == SWAP_EVENT_DISCRIMINATOR}")

# Try decoding
offset = 8

# Parse amm (32 bytes)
amm_bytes = data[offset:offset+32]
amm = base58.b58encode(amm_bytes).decode('utf-8')
print(f"\nAMM: {amm}")
offset += 32

# Parse inputMint (32 bytes)
input_mint_bytes = data[offset:offset+32]
input_mint = base58.b58encode(input_mint_bytes).decode('utf-8')
print(f"Input Mint: {input_mint}")
offset += 32

# Parse inputAmount (8 bytes, little-endian u64)
input_amount = struct.unpack('<Q', data[offset:offset+8])[0]
print(f"Input Amount: {input_amount}")
offset += 8

# Parse outputMint (32 bytes)
output_mint_bytes = data[offset:offset+32]
output_mint = base58.b58encode(output_mint_bytes).decode('utf-8')
print(f"Output Mint: {output_mint}")
offset += 32

# Parse outputAmount (8 bytes, little-endian u64)
output_amount = struct.unpack('<Q', data[offset:offset+8])[0]
print(f"Output Amount: {output_amount}")
offset += 8

print(f"\nBytes remaining: {len(data) - offset}")

print("\n" + "="*80)
print("Expected output from your example:")
print("AMM: pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
print("Input Mint: So11111111111111111111111111111111111111112")
print("Input Amount: 70829627")
print("Output Mint: CdTwzpaYwpmSzdzqRMtTzvEqdoAV3ohCXsVWwPmJpump")
print("Output Amount: 356249776231")
