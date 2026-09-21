import json
import math

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate


class CurrentMomentum:
    def __init__(self, buy=0.01, sell=-0.01, min_return=0.02):
        self.buy = buy
        self.sell = sell
        self.min_return = min_return

    def evaluate(self, prices, volumes):
        if len(prices) < 8:
            return "hold", 0.0
        recent = prices[-8:]
        earlier = prices[-16:-8] if len(prices) > 16 else prices[:-1]
        if not earlier:
            earlier = prices[:-1]
        start = recent[0]
        end = recent[-1]
        recent_return = (end - start) / start if start else 0.0
        early_avg = sum(earlier) / len(earlier)
        recent_avg = sum(recent) / len(recent)
        slope = (recent_avg - early_avg) / max(abs(early_avg), 1e-9)
        avg_vol = sum(volumes[-8:]) / len(volumes[-8:])
        vol_strength = volumes[-1] / max(avg_vol, 1e-9)
        score = recent_return + (slope * 0.5) + (vol_strength - 1.0) * 0.2
        if score > self.buy and recent_return > self.min_return:
            return "buy", score
        if score < self.sell:
            return "sell", score
        return "hold", score


class EmaMomentum:
    def __init__(self, short_span=8, long_span=20, buy_step=0.0005):
        self.short_span = short_span
        self.long_span = long_span
        self.buy_step = buy_step

    def _ema(self, series, span):
        k = 2 / (span + 1)
        ema = series[0]
        for v in series[1:]:
            ema = (v * k) + (ema * (1 - k))
        return ema

    def evaluate(self, prices, volumes):
        if len(prices) < max(self.short_span, self.long_span):
            return "hold", 0.0
        short_ema = self._ema(prices[-self.short_span:], self.short_span)
        long_ema = self._ema(prices[-self.long_span:], self.long_span)
        price_return = (prices[-1] - prices[0]) / prices[0]
        impulse = (short_ema - long_ema) / max(abs(long_ema), 1e-9)
        if impulse > self.buy_step and price_return > 0:
            return "buy", impulse
        if impulse < -self.buy_step and price_return < 0:
            return "sell", impulse
        return "hold", impulse


class BreakoutMomentum:
    def __init__(self, lookback=20, threshold=0.015):
        self.lookback = lookback
        self.threshold = threshold

    def evaluate(self, prices, volumes):
        if len(prices) < self.lookback:
            return "hold", 0.0
        window = prices[-self.lookback:]
        base = sum(window[:-5]) / max(len(window[:-5]), 1)
        last = prices[-1]
        vol = max(abs(last - base) / max(abs(base), 1e-9), 0.0)
        trend = (prices[-1] - prices[-5]) / max(prices[-5], 1e-9)
        if vol > self.threshold and trend > 0:
            return "buy", vol
        if vol > self.threshold and trend < 0:
            return "sell", vol
        return "hold", vol


STRATEGIES = {
    "current_momentum": CurrentMomentum,
    "ema_momentum": EmaMomentum,
    "breakout_momentum": BreakoutMomentum,
}


def run_strategy_on_product(strategy_name, product_id, hours=168):
    closes, vols = fetch_candles(product_id, granularity=300, hours=hours)
    strategy = STRATEGIES[strategy_name]()
    cash = 10000.0
    position = 0.0
    entry = 0.0
    wins = 0
    losses = 0
    trades = 0
    peak = cash
    max_drawdown = 0.0

    for idx in range(len(closes)):
        window_prices = closes[max(0, idx - 60): idx + 1]
        window_vols = vols[max(0, idx - 60): idx + 1]
        signal, _ = strategy.evaluate(window_prices, window_vols)

        if signal == "buy" and position == 0:
            qty = cash * 0.2 / max(closes[idx], 1e-9)
            cash -= qty * closes[idx]
            position = qty
            entry = closes[idx]
            trades += 1
        elif signal == "sell" and position > 0:
            exit_value = position * closes[idx]
            pnl = exit_value - (position * entry)
            cash += exit_value
            position = 0.0
            if pnl > 0:
                wins += 1
            else:
                losses += 1

        current_value = cash + position * closes[idx]
        if current_value > peak:
            peak = current_value
        drawdown = (peak - current_value) / peak if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    final_value = cash + position * closes[-1]
    net_return = (final_value - 10000.0) / 10000.0
    win_rate = wins / trades if trades > 0 else 0.0
    gate = LiveReadinessGate().score(net_return, max_drawdown, win_rate, trades, 3)

    return {
        "product": product_id,
        "strategy": strategy_name,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "net_return": round(net_return, 6),
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(max_drawdown, 6),
        "final_value": round(final_value, 2),
        "ready": gate.ready,
        "gate_score": gate.score,
        "reasons": gate.reasons,
    }


if __name__ == "__main__":
    products = ["BTC-USD", "ETH-USD", "SOL-USD"]
    results = []
    for product in products:
        for strategy_name in STRATEGIES:
            results.append(run_strategy_on_product(strategy_name, product, hours=168))
    print(json.dumps(results, indent=2))
