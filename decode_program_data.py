#!/usr/bin/env python3
"""
Decode the Program data log from the transaction
"""

import base64
import base58
import struct

# The Program data from the log
program_data_b64 = "Z/RSHyz1d3dvrGBpAAAAAGcwJPJSAAAAO8Y4BAAAAACWlZqZdwYAADvGOAQAAAAATNya+dEuAQCb39M0DwAAAHFuKwQAAAAAAgAAAAAAAACoNgAAAAAAAF0AAAAAAAAAWO0JAAAAAAAZpSsEAAAAADvGOAQAAAAAj1F/Bq+0tD+pp9MLjnRyyxFZCfZCG+/PN1+MeAFaNOGWBYWfofvZlYj2OxTa9NXzz2Q5NAw0cn9XxPaV9QNO3NjAkrgwF6bxDst5E7Ejihi8yaM1jnMYTanngANoQ7qIclqxVNzeNXQGd/Nx0zO/RwVP4sX9asPtHuijyH1tpJXXqo+wYNgpG0xNR12v92LJa9wNrOs2wBLq0S7TqUhBYQHIIfOo8I/viNwxQkp2gK6MloFwTPHl9ciOJ5m3+YIhKZjTpiJjFWUv+tSmqE4+uIwWFuPTAkaPt4fViflcplceAAAAAAAAAMozAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZzAk8lIAAAADAAAAYnV5"

data = base64.b64decode(program_data_b64)

print(f"Total length: {len(data)} bytes")
print(f"First 16 bytes (hex): {data[:16].hex()}")
print(f"First 8 bytes: {list(data[:8])}")

# SwapEvent discriminator
SWAP_EVENT_DISCRIMINATOR = bytes([64, 198, 205, 232, 38, 8, 113, 226])
print(f"\nSwapEvent discriminator: {list(SWAP_EVENT_DISCRIMINATOR)}")
print(f"Match: {data[:8] == SWAP_EVENT_DISCRIMINATOR}")

# Search for the discriminator in the data
for i in range(len(data) - 8):
    if data[i:i+8] == SWAP_EVENT_DISCRIMINATOR:
        print(f"\nFound SwapEvent discriminator at offset {i}!")

        offset = i + 8

        # Parse amm (32 bytes)
        amm = base58.b58encode(data[offset:offset+32]).decode('utf-8')
        print(f"AMM: {amm}")
        offset += 32

        # Parse inputMint (32 bytes)
        input_mint = base58.b58encode(data[offset:offset+32]).decode('utf-8')
        print(f"Input Mint: {input_mint}")
        offset += 32

        # Parse inputAmount (8 bytes, little-endian u64)
        input_amount = struct.unpack('<Q', data[offset:offset+8])[0]
        print(f"Input Amount: {input_amount}")
        offset += 8

        # Parse outputMint (32 bytes)
        output_mint = base58.b58encode(data[offset:offset+32]).decode('utf-8')
        print(f"Output Mint: {output_mint}")
        offset += 32

        # Parse outputAmount (8 bytes, little-endian u64)
        output_amount = struct.unpack('<Q', data[offset:offset+8])[0]
        print(f"Output Amount: {output_amount}")

        print("\n" + "="*80)
        print("Expected from your example:")
        print("AMM: pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
        print("Input Mint: So11111111111111111111111111111111111111112")
        print("Input Amount: 70829627")
        print("Output Mint: CdTwzpaYwpmSzdzqRMtTzvEqdoAV3ohCXsVWwPmJpump")
        print("Output Amount: 356249776231")
        break
