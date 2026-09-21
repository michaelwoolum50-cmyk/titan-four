import json

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.strategy import StrategyDecision
from titan_four.paper_trading import LiveReadinessGate


class SearchStrategy:
    def __init__(self, short_span=8, long_span=21, buy_threshold=0.018, sell_threshold=-0.018, min_return=0.003, min_sell_return=-0.003, min_volume_ratio=0.7):
        self.short_span = short_span
        self.long_span = long_span
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.min_return = min_return
        self.min_sell_return = min_sell_return
        self.min_volume_ratio = min_volume_ratio

    def _ema(self, vals, span):
        if not vals:
            return 0.0
        k = 2 / (span + 1)
        ema = vals[0]
        for v in vals[1:]:
            ema = (v * k) + (ema * (1 - k))
        return ema

    def evaluate(self, prices, volumes):
        if len(prices) < max(self.short_span, self.long_span):
            return StrategyDecision('hold', 0.0, 'insufficient_data')

        prices = list(map(float, prices))
        volumes = list(map(float, volumes))
        recent = prices[-self.short_span:]
        earlier = prices[-self.long_span:]

        short_ema = self._ema(recent, self.short_span)
        long_ema = self._ema(earlier, self.long_span)
        recent_return = (prices[-1] - prices[0]) / max(abs(prices[0]), 1e-9)
        trend_strength = (short_ema - long_ema) / max(abs(long_ema), 1e-9)
        avg_vol = sum(volumes[-self.short_span:]) / max(len(volumes[-self.short_span:]), 1)
        volume_ratio = volumes[-1] / max(avg_vol, 1e-9)
        score = recent_return * 2.5 + trend_strength * 3.0 + max(0.0, volume_ratio - 1.0) * 0.3

        if recent_return > self.min_return and trend_strength > 0 and score > self.buy_threshold and volume_ratio >= self.min_volume_ratio:
            return StrategyDecision('buy', min(max(0.5 + score, 0.0), 1.0), 'trend_bull')
        if recent_return < self.min_sell_return and trend_strength < 0 and score < self.sell_threshold and volume_ratio >= self.min_volume_ratio:
            return StrategyDecision('sell', min(max(0.5 + abs(score), 0.0), 1.0), 'trend_bear')
        return StrategyDecision('hold', min(max(score, 0.0), 1.0), 'neutral')


products = ['BTC-USD']
configs = []
for short in [5, 8, 10]:
    for long in [18, 21, 30]:
        if long <= short:
            continue
        for buy in [0.003, 0.005, 0.008, 0.01]:
            for sell in [-0.003, -0.005, -0.008, -0.01]:
                for min_return in [0.003, 0.005, 0.008]:
                    configs.append((short, long, buy, sell, min_return))

all_results = []
for product in products:
    closes, vols = fetch_candles(product, granularity=300, hours=720)
    for short, long, buy, sell, min_return in configs:
        strategy = SearchStrategy(short_span=short, long_span=long, buy_threshold=buy, sell_threshold=sell, min_return=min_return, min_sell_return=-min_return)
        bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
        bt.strategy = type('S', (), {'evaluate': lambda self, p, v, s=strategy: s.evaluate(p, v)})()
        result = bt.run(closes, vols)
        gate = LiveReadinessGate().score(result.net_return, result.max_drawdown, result.win_rate, result.trades, 3)
        all_results.append({
            'product': product,
            'short': short,
            'long': long,
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

ranked = sorted(all_results, key=lambda x: (x['ready'], x['score'], x['net_return'], x['win_rate'], x['trades']), reverse=True)
print('READY_COUNT=', sum(1 for r in ranked if r['ready']))
print('BEST_POSITIVE=', max((r for r in ranked if r['net_return'] > 0), key=lambda r: (r['net_return'], r['win_rate'], r['trades']), default=None))
if not any(r['ready'] for r in ranked):
    print('NO_READY_CANDIDATES=TRUE')
    print('TOP_CANDIDATE=', ranked[0] if ranked else None)
