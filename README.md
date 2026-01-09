# DFlow Event Fetcher

Fetches and decodes SwapEvent transactions from the DFlow Aggregator v4 program on Solana.

## Program Details
- **Program ID**: `DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH`
- **Event**: `SwapEvent`
- **Discriminator**: `e445a52e51cb9a1d` (hex) or `[228, 69, 165, 46, 81, 203, 154, 29]`

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

Run the script:
```bash
python3 fetch_dflow_correct.py
```

The script will:
- Fetch 50 recent transactions from the DFlow program using Helius API
- Decode SwapEvent data from **Anchor Self CPI logs** in inner instructions
- Display results in a Dune-style table format with columns:
  - Transaction ID
  - Block Slot
  - Block Time
  - AMM
  - Input Mint & Amount
  - Output Mint & Amount
- Export events to TWO locations:
  - `outputs/dflow_events_YYYYMMDD_HHMMSS.json` (timestamped)
  - `dflow_swap_events.json` (latest run, overwritten each time)

### Output Files

Each run creates a **timestamped JSON file** in the `outputs/` directory, allowing you to:
- Keep historical records of all fetches
- Track changes over time
- Compare results from different runs

Example: `outputs/dflow_events_20260109_132525.json`

## Output Format

Each event includes:
- `tx_id`: Transaction signature
- `block_slot`: Block slot number
- `block_time`: Unix timestamp
- `source`: Data source (`anchor_event` or `inferred_from_transfers`)
- `amm`: AMM pool address
- `inputMint`: Input token mint address
- `inputAmount`: Input token amount (as string to preserve precision)
- `outputMint`: Output token mint address
- `outputAmount`: Output token amount (as string to preserve precision)

## Example Output

```
TX_ID: 5zJtLShoaRhJok8eVrURPrkr31S9d6JGwR6hTMhMNfDv...
SLOT: 392300377
TIME: 2026-01-09 12:47:27
SOURCE: anchor_event
AMM: 7DYHBVJNBSu3pZZkSt6Sdq3rbGuCQH2MJAuHqVY6oG2Q
INPUT_MINT: 6jQAJNVRpGUF88KVramXYCnx19mqUstLRwKqwyEWtuHB
INPUT_AMOUNT: 482043698780799464
OUTPUT_MINT: 5Nvvg1rFGcq19Z8tui85bUJi5ERZBSsLGBbWgmMbjvdB
OUTPUT_AMOUNT: 12417205911893661141
```

## Files

- `fetch_dflow_correct.py` - **Main script** (uses correct discriminator, extracts from inner instructions)
- `outputs/` - Directory containing timestamped JSON outputs from each run
- `dflow_swap_events.json` - Latest run output (overwritten)
- `requirements.txt` - Python dependencies
- `debug_transaction.py` - Debug utility to inspect transaction structure
- `.gitignore` - Git ignore rules
