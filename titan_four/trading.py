from typing import List

from titan_four.risk import RiskManager
from titan_four.strategy import MomentumStrategy


class TradingDecision:
    def __init__(self, symbol: str, action: str, confidence: float, reason: str):
        self.symbol = symbol
        self.action = action
        self.confidence = confidence
        self.reason = reason


class TradingEngine:
    def __init__(self, market_client, config):
        self.client = market_client
        self.config = config
        self.strategy = MomentumStrategy()
        self.risk = RiskManager(
            max_position_fraction=config.max_position_fraction,
            max_positions=config.max_positions,
            leverage_allowed=False,
        )

    def get_market_snapshot(self, product_id: str):
        ticker = self.client.get_product(product_id)
        price = float(ticker.get("price", 0.0))
        return {"price": price, "volume": 1.0}

    def can_execute_live(self):
        return not self.config.dry_run and self.config.allow_live_trading

    def evaluate_symbol(self, symbol: str, prices: List[float], volumes: List[float]):
        decision = self.strategy.evaluate(prices, volumes)
        if decision.signal == "buy":
            if self.config.dry_run:
                return TradingDecision(symbol, "dry_run_buy", decision.confidence, decision.reason)
            if not self.can_execute_live():
                return TradingDecision(symbol, "hold", decision.confidence, "live_trading_not_approved")
            return TradingDecision(symbol, "buy", decision.confidence, decision.reason)
        if decision.signal == "sell":
            if self.config.dry_run:
                return TradingDecision(symbol, "dry_run_sell", decision.confidence, decision.reason)
            if not self.can_execute_live():
                return TradingDecision(symbol, "hold", decision.confidence, "live_trading_not_approved")
            return TradingDecision(symbol, "sell", decision.confidence, decision.reason)
        return TradingDecision(symbol, "hold", decision.confidence, decision.reason)

    def run_cycle(self):
        results = []
        for symbol in self.config.product_ids:
            snapshot = self.get_market_snapshot(symbol)
            prices = [snapshot["price"]]
            volumes = [snapshot["volume"]]
            results.append(self.evaluate_symbol(symbol, prices, volumes))
        return results
