import argparse

from titan_four.config import Config
from titan_four.coinbase_client import CoinbaseClient
from titan_four.trading import TradingEngine


def main():
    parser = argparse.ArgumentParser(description="Titan Four momentum bot")
    parser.add_argument("--live", action="store_true", help="Enable live execution only if explicit approval is set")
    parser.add_argument("--approve-live", action="store_true", help="Explicit live-trading approval gate")
    parser.add_argument("--symbol", default="BTC-USD", help="Coinbase product ID, e.g. BTC-USD")
    args = parser.parse_args()

    cfg = Config(dry_run=not args.live, allow_live_trading=args.approve_live)
    if args.symbol:
        cfg.product_ids = [args.symbol]

    if args.live and not cfg.allow_live_trading:
        print("Live execution blocked: --approve-live is required before enabling real trading.")
        return

    client = CoinbaseClient()
    engine = TradingEngine(client, cfg)
    decisions = engine.run_cycle()

    for decision in decisions:
        print(f"{decision.symbol}: {decision.action} ({decision.reason})")


if __name__ == "__main__":
    main()
