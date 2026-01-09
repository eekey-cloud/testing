# DFlow Event Fetcher

Fetches and decodes SwapEvent transactions from the DFlow program on Solana.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script:
```bash
python fetch_dflow_events.py
```

The script will:
- Fetch recent transactions from the DFlow program
- Decode SwapEvent data from transaction logs
- Display results in a Dune-style table format
- Export events to `dflow_events.json`

## Output Format

Each event includes:
- `tx_id`: Transaction signature
- `block_slot`: Block slot number
- `block_time`: Block timestamp
- `event_data`: Decoded swap event containing:
  - `amm`: AMM pool address
  - `inputMint`: Input token mint address
  - `inputAmount`: Input token amount
  - `outputMint`: Output token mint address
  - `outputAmount`: Output token amount
