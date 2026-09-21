from dataclasses import dataclass
import statistics


@dataclass
class StrategyDecision:
    signal: str
    confidence: float
    reason: str


class MomentumStrategy:
    """Rule-based momentum strategy.

    The strategy buys when recent price acceleration is strong and positive,
    and sells when momentum deteriorates or reverses. It is intentionally
    deterministic and does not use LLM inference in the order loop.
    """

    def __init__(
        self,
        buy_threshold=0.003,
        sell_threshold=-0.003,
        min_return=0.0004,
        min_sell_return=-0.0004,
    ):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.min_return = min_return
        self.min_sell_return = min_sell_return

    def evaluate(self, prices, volumes):
        if len(prices) < 8:
            return StrategyDecision("hold", 0.0, "insufficient_data")

        prices = list(map(float, prices))
        volumes = list(map(float, volumes))

        recent = prices[-8:]
        earlier = prices[-16:-8] if len(prices) >= 16 else prices[:-8] or prices[:-1]

        if not earlier:
            earlier = recent[:-1]

        recent_return = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-9)
        earlier_return = (earlier[-1] - earlier[0]) / max(abs(earlier[0]), 1e-9)

        recent_avg = sum(recent) / len(recent)
        earlier_avg = sum(earlier) / len(earlier)
        price_slope = (recent_avg - earlier_avg) / max(abs(earlier_avg), 1e-9)
        closing_pressure = (prices[-1] - earlier_avg) / max(abs(earlier_avg), 1e-9)
        tail_pressure = (prices[-1] - earlier[-1]) / max(abs(earlier[-1]), 1e-9)

        recent_deltas = [
            (recent[i] - recent[i - 1]) / max(abs(recent[i - 1]), 1e-9)
            for i in range(1, len(recent))
        ]
        directional_noise = sum(abs(delta) for delta in recent_deltas) / max(len(recent_deltas), 1)

        avg_volume = sum(volumes[-8:]) / len(volumes[-8:])
        recent_volume = volumes[-1]
        volume_strength = recent_volume / max(avg_volume, 1e-9)

        score = (
            recent_return * 3.0
            + earlier_return * 1.25
            + max(0.0, tail_pressure) * 12.0
            + max(0.0, price_slope) * 10.0
            + max(0.0, closing_pressure) * 5.0
            + max(0.0, volume_strength - 1.0) * 1.0
        )

        # Allow healthy momentum with short pullbacks to keep trading, while
        # still suppressing flat or directionless periods.
        choppy = (
            abs(recent_return) < 0.0015
            and abs(tail_pressure) < 0.0002
            and abs(closing_pressure) < 0.00018
            and directional_noise < 0.006
        )

        if choppy:
            return StrategyDecision("hold", 0.5, "choppy_market_no_clear_direction")

        buy_condition = (
            recent_return > self.min_return
            and (tail_pressure > 0.00005 or closing_pressure > 0.00008 or recent_return > earlier_return)
            and score > self.buy_threshold * 0.7
            and volume_strength >= 0.6
        )

        sell_condition = (
            recent_return < self.min_sell_return
            and (tail_pressure < -0.00005 or closing_pressure < -0.00008 or recent_return < earlier_return)
            and score < self.sell_threshold * 0.7
            and volume_strength >= 0.6
        )

        if buy_condition:
            confidence = min(max(0.5 + score, 0.0), 1.0)
            return StrategyDecision("buy", confidence, "clear_uptrend")

        if sell_condition:
            confidence = min(max(0.5 + abs(score), 0.0), 1.0)
            return StrategyDecision("sell", confidence, "clear_downtrend")

        return StrategyDecision("hold", min(max(score, 0.0), 1.0), "neutral_market")
