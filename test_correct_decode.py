#!/usr/bin/env python3
"""
Test correct decoding with the extra 8 bytes
"""

import base58
import struct

# Your sample data
hex_data = "e445a52e51cb9a1d40c6cde8260871e28ab0688461397e679cc47b10009e50fc184a59de618ecc70bbad9731ecf4aebd07072f054ab48d987da4e5969e632cddf38dd64141349da41b0b695b91d15c3a7804920000000000c6fa7af3bedbad3a3d65f36aabc97431b1bbe4c2d2f6e0e47ca60203452f5d6168f3910000000000"

data = bytes.fromhex(hex_data)

print(f"Total length: {len(data)} bytes")
print(f"Discriminator (bytes 0-7): {data[:8].hex()}")
print(f"Unknown field (bytes 8-15): {data[8:16].hex()}")
print()

# Skip discriminator (8 bytes) AND unknown field (8 bytes)
offset = 16

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
print("Expected:")
print("AMM: ALPHAQmeA7bjrVuccPsYPiCvsi428SNwte66Srvs4pHA")
print("Input Mint: USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB")
print("Input Amount: 9569400")
print("Output Mint: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
print("Output Amount: 9565032")
print("\n✓ MATCH!" if (amm == "ALPHAQmeA7bjrVuccPsYPiCvsi428SNwte66Srvs4pHA" and
                          input_mint == "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB" and
                          input_amount == 9569400 and
                          output_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" and
                          output_amount == 9565032) else "\n✗ NO MATCH")
