#!/usr/bin/env python3
"""
Find the correct discriminator by analyzing your sample data
"""

import hashlib

# From your sample, the event name is "swapEvent"
# Anchor generates discriminators using: first 8 bytes of sha256("event:swapEvent")

event_name = "swapEvent"
preimage = f"event:{event_name}"

# Calculate the discriminator
hash_result = hashlib.sha256(preimage.encode()).digest()
discriminator = list(hash_result[:8])

print(f"Event name: {event_name}")
print(f"Preimage: {preimage}")
print(f"SHA256 hash (first 8 bytes): {discriminator}")
print(f"Hex: {hash_result[:8].hex()}")

# Compare with what you provided
your_discriminator = [64, 198, 205, 232, 38, 8, 113, 226]
print(f"\nYour provided discriminator: {your_discriminator}")
print(f"Hex: {''.join(f'{b:02x}' for b in your_discriminator)}")

print(f"\nDo they match? {discriminator == your_discriminator}")

# Also check the instruction event data you provided
instruction_data_hex = "e445a52e51cb9a1d40c6cde8260871e20c14defc825ec67694250818bb654065f4298d3156d571b4d4f8090c18e9a863069b8857feab8184fb687f634618c035dac439dc1aeb3b5598a0f000000000013bc6380400000000acc7ef8e8bfd2fbc97cf116328b551b666b89f71357d5b24f9ca1bb36caa15df673024f252000000"

instruction_discriminator = [int(instruction_data_hex[i:i+2], 16) for i in range(0, 16, 2)]
print(f"\nInstruction data discriminator (first 8 bytes): {instruction_discriminator}")
print(f"Hex: {instruction_data_hex[:16]}")

# The instruction discriminator might be for the instruction itself
# Let's check if it's the discriminator for "swap" instruction
for name in ["swap", "Swap", "swap2", "Swap2"]:
    preimage = f"global:{name}"
    hash_result = hashlib.sha256(preimage.encode()).digest()
    disc = list(hash_result[:8])
    if disc == instruction_discriminator:
        print(f"\nInstruction discriminator matches: {name}")
        print(f"Preimage: {preimage}")
