# DFlow Swap Events Output Files

This directory contains timestamped JSON files with DFlow swap events from each script run.

## File Naming Convention

Files are named: `dflow_events_YYYYMMDD_HHMMSS.json`

Example: `dflow_events_20260109_132525.json`
- Date: 2026-01-09
- Time: 13:25:25

## File Contents

Each JSON file contains an array of swap events with:
- `tx_id`: Transaction signature
- `block_slot`: Block slot number
- `block_time`: Unix timestamp
- `amm`: AMM pool address
- `inputMint`: Input token mint
- `inputAmount`: Input amount (as string)
- `outputMint`: Output token mint
- `outputAmount`: Output amount (as string)
- `source`: "anchor_event" (extracted from Anchor Self CPI logs)

## Usage

Each run of `fetch_dflow_correct.py` creates a new timestamped file, allowing you to:
- Track historical data
- Compare results across different time periods
- Keep a record of all fetched events

The latest run is also saved to the parent directory as `dflow_swap_events.json` for quick access.
