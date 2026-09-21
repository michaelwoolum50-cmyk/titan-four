# Titan Four

Titan Four is a non-margin, single-strategy momentum trading bot designed around a deterministic rule set rather than an LLM live-trading loop.

## Strategy goal

The bot tries to:
- buy when short-term momentum is accelerating upward
- sell when momentum fades or reverses
- keep execution simple and systematic
- avoid leverage and margin calls

## Safety principles

- no leverage
- no margin borrowing
- maximum account fraction per position
- per-symbol position caps
- market-order execution only when explicitly enabled
- dry-run mode recommended before live trading

## Setup

1. Create a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Configure your Coinbase API credentials as environment variables:
   - `COINBASE_API_KEY`
   - `COINBASE_API_SECRET`
   - `COINBASE_API_PASSPHRASE`
4. Run tests:
   `pytest -q`

## Live trading caution

This project is for experimentation and learning. Coinbase API trading carries real financial risk. Do not enable live trading without a paper-trading test and carefully reviewed risk settings.
