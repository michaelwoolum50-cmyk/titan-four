import json
import math
import sys

sys.path.insert(0, r"C:\Users\micha\Desktop\titan-four")

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate


class CandidateStrategy:
    def __init__(self, buy_threshold=0.02, sell_threshold=-0.02, min_return=0.005, min_sell_return=-0.005):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.min_return = min_return
        self.min_sell_return = min_sell_return

    def evaluate(self, prices, volumes):
        if len(prices) < 20:
            return "hold", 0.0

        recent = list(map(float, prices[-8:]))
        mid = list(map(float, prices[-16:-8])) if len(prices) >= 16 else list(map(float, prices[-max(4, len(prices) - 1):]))
        longer = list(map(float, prices[-32:-16])) if len(prices) >= 32 else list(map(float, prices[-max(8, len(prices) - 4):]))
        if not mid:
            mid = recent[:-1]
        if not longer:
            longer = mid[:-1] or recent[:-1]

        recent_return = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-9)
        mid_return = (mid[-1] - mid[0]) / max(abs(mid[0]), 1e-9)
        longer_return = (longer[-1] - longer[0]) / max(abs(longer[0]), 1e-9)

        short_sma = sum(recent) / len(recent)
        mid_sma = sum(mid) / len(mid)
        long_sma = sum(longer) / len(longer)
        short_vs_long = (short_sma - long_sma) / max(abs(long_sma), 1e-9)
        mid_vs_long = (mid_sma - long_sma) / max(abs(long_sma), 1e-9)

        recent_volatility = (__import__('statistics').pstdev(recent) / max(abs(sum(recent)/len(recent)), 1e-9))
        avg_step = sum(abs(recent[i] - recent[i-1]) / max(abs(recent[i-1]), 1e-9) for i in range(1, len(recent))) / max(len(recent)-1, 1)
        choppy = recent_volatility < 0.005 and abs(recent_return) < 0.01 and avg_step < 0.015

        avg_vol = sum(volumes[-8:]) / len(volumes[-8:])
        vol_strength = volumes[-1] / max(avg_vol, 1e-9)
        price_slope = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-9)
        momentum = recent_return * 2.0 + mid_return * 1.3 + longer_return * 0.7 + short_vs_long * 2.5 + mid_vs_long * 1.4 + max(0.0, vol_strength - 1.0)

        if choppy:
            return "hold", 0.0
        if (recent_return > self.min_return and short_sma > mid_sma > long_sma and momentum > self.buy_threshold and vol_strength >= 0.85):
            return "buy", min(max(0.5 + momentum, 0.0), 1.0)
        if (recent_return < self.min_sell_return and short_sma < mid_sma < long_sma and momentum < self.sell_threshold and vol_strength >= 0.85):
            return "sell", min(max(0.5 + abs(momentum), 0.0), 1.0)
        return "hold", momentum


def evaluate_candidate(product_id, buy, sell, min_return):
    closes, vols = fetch_candles(product_id, granularity=300, hours=168)
    strategy = CandidateStrategy(buy_threshold=buy, sell_threshold=sell, min_return=min_return, min_sell_return=-min_return)
    bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    bt.strategy = strategy
    result = bt.run(closes, vols)
    gate = LiveReadinessGate().score(result.net_return, result.max_drawdown, result.win_rate, result.trades, 3)
    return {
        'product': product_id,
        'buy': buy,
        'sell': sell,
        'min_return': min_return,
        'trades': result.trades,
        'wins': result.wins,
        'losses': result.losses,
        'net_return': round(result.net_return, 6),
        'win_rate': round(result.win_rate, 4),
        'drawdown': round(result.max_drawdown, 6),
        'ready': gate.ready,
        'score': round(gate.score, 4),
        'reasons': gate.reasons,
    }


if __name__ == '__main__':
    products = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    configs = []
    for buy in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1]:
        for sell in [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.08, -0.1]:
            for min_return in [0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]:
                configs.append((buy, sell, min_return))

    outputs = []
    for product in products:
        for cfg in configs:
            outputs.append(evaluate_candidate(product, *cfg))

    ranked = sorted(outputs, key=lambda x: (x['ready'], x['score'], x['net_return'], x['win_rate'], x['trades']), reverse=True)
    print(json.dumps(ranked[:30], indent=2))
    print('READY_COUNT=', sum(1 for x in ranked if x['ready']))
