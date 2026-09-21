import os
from typing import List

from titan_four.coinbase_client import CoinbaseClient
from titan_four.risk import RiskManager
from titan_four.strategy import MomentumStrategy


class TitanFourEngine:
    def __init__(self, product_ids: List[str], dry_run: bool = True):
        self.product_ids = product_ids
        self.dry_run = dry_run
        self.strategy = MomentumStrategy()
        self.risk = RiskManager(max_position_fraction=0.2, max_positions=3, leverage_allowed=False)
        self.client = CoinbaseClient()

    def fetch_prices(self, product_id: str):
        ticker = self.client.get_product(product_id)
        price = float(ticker.get("price", 0.0))
        return [price]

    def evaluate_symbol(self, symbol: str, prices: List[float], volumes: List[float]):
        decision = self.strategy.evaluate(prices, volumes)
        if decision.signal == "buy":
            if not self.risk.can_trade():
                return "hold"
            if self.dry_run:
                return "dry_run_buy"
            return "buy"
        if decision.signal == "sell":
            if self.dry_run:
                return "dry_run_sell"
            return "sell"
        return "hold"

    def run_once(self):
        for symbol in self.product_ids:
            prices = self.fetch_prices(symbol)
            volumes = [1.0] * len(prices)
            result = self.evaluate_symbol(symbol, prices, volumes)
            if result in {"dry_run_buy", "dry_run_sell"}:
                print(f"{symbol}: {result}")
            elif result in {"buy", "sell"}:
                print(f"{symbol}: executing real trade -> {result}")
