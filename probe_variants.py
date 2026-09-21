import json
import math
import sys

sys.path.insert(0, r"C:\Users\micha\Desktop\titan-four")

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate
from titan_four.strategy import StrategyDecision


class VariantStrategy:
    def __init__(self, buy_threshold=0.02, sell_threshold=-0.02, min_return=0.005, min_sell_return=-0.005):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.min_return = min_return
        self.min_sell_return = min_sell_return

    def evaluate(self, prices, volumes):
        if len(prices) < 20:
            return StrategyDecision('hold', 0.0, 'insufficient_data')
        recent = prices[-8:]
        prior = prices[-16:-8] if len(prices) >= 16 else prices[-max(4, len(prices)-1):]
        longer = prices[-20:-12] if len(prices) >= 20 else prices[-max(6, len(prices)-3):]
        if not prior:
            prior = recent[:-1]
        if not longer:
            longer = prior[:-1] or recent[:-1]

        recent_return = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-9)
        prior_return = (prior[-1] - prior[0]) / max(abs(prior[0]), 1e-9)
        longer_return = (longer[-1] - longer[0]) / max(abs(longer[0]), 1e-9)

        short_sma = sum(recent) / len(recent)
        prior_sma = sum(prior) / len(prior)
        long_sma = sum(longer) / len(longer)
        short_vs_long = (short_sma - long_sma) / max(abs(long_sma), 1e-9)
        prior_vs_long = (prior_sma - long_sma) / max(abs(long_sma), 1e-9)

        avg_vol = sum(volumes[-8:]) / len(volumes[-8:])
        vol_strength = volumes[-1] / max(avg_vol, 1e-9)

        score = (
            recent_return * 1.7
            + prior_return * 1.2
            + longer_return * 0.6
            + short_vs_long * 3.0
            + prior_vs_long * 1.5
            + max(0.0, vol_strength - 1.0) * 1.2
        )

        if recent_return > self.min_return and short_sma > prior_sma > long_sma and score > self.buy_threshold and vol_strength > 0.9:
            return StrategyDecision('buy', min(max(0.5 + score, 0.0), 1.0), 'trend_confirmed')
        if recent_return < self.min_sell_return and short_sma < prior_sma < long_sma and score < self.sell_threshold and vol_strength > 0.9:
            return StrategyDecision('sell', min(max(0.5 + abs(score), 0.0), 1.0), 'downtrend_confirmed')
        return StrategyDecision('hold', 0.5, 'neutral_market')


products = ['BTC-USD', 'ETH-USD', 'SOL-USD']
configs = []
for buy in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.12, 0.15]:
    for sell in [-0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.08, -0.1, -0.12, -0.15]:
        for min_return in [0.002, 0.004, 0.006, 0.008, 0.01, 0.015, 0.02, 0.03]:
            configs.append((buy, sell, min_return))

all_results = []
for product in products:
    closes, vols = fetch_candles(product, granularity=300, hours=168)
    for buy, sell, min_return in configs:
        strategy = VariantStrategy(buy_threshold=buy, sell_threshold=sell, min_return=min_return, min_sell_return=-min_return)
        bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
        bt.strategy = strategy
        result = bt.run(closes, vols)
        gate = LiveReadinessGate().score(result.net_return, result.max_drawdown, result.win_rate, result.trades, 3)
        all_results.append({
            'product': product,
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
        })

ranked = sorted(all_results, key=lambda x: (x['ready'], x['net_return'], x['win_rate'], x['trades']), reverse=True)
print(json.dumps(ranked[:25], indent=2))
