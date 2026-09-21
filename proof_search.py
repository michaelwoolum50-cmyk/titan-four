import json
import math
from typing import List

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate


class Candidate:
    def __init__(self, short_ema=8, long_ema=21, atr_mult=2.0, min_trend=0.002, min_vol=1.0, stop_atr=1.2, trail_atr=0.8):
        self.short_ema = short_ema
        self.long_ema = long_ema
        self.atr_mult = atr_mult
        self.min_trend = min_trend
        self.min_vol = min_vol
        self.stop_atr = stop_atr
        self.trail_atr = trail_atr

    def ema(self, values, span):
        if len(values) < 2:
            return values[-1]
        k = 2 / (span + 1)
        ema_val = values[0]
        for v in values[1:]:
            ema_val = (v * k) + (ema_val * (1 - k))
        return ema_val

    def atr(self, closes, spans=14):
        if len(closes) < 2:
            return 0.0
        tr = []
        for i in range(1, len(closes)):
            high = closes[i]
            low = closes[i-1]
            prev_close = closes[i-1]
            tr.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        if not tr:
            return 0.0
        avg = sum(tr[:spans]) / min(spans, len(tr))
        for v in tr[spans:]:
            avg = (avg * (spans - 1) + v) / spans
        return avg

    def evaluate(self, prices, volumes):
        if len(prices) < max(self.short_ema, self.long_ema):
            return 'hold', 0.0
        short = self.ema(prices[-self.short_ema:], self.short_ema)
        long = self.ema(prices[-self.long_ema:], self.long_ema)
        recent = prices[-self.short_ema:]
        recent_return = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-9)
        trend_strength = (short - long) / max(abs(long), 1e-9)
        atr = self.atr(prices[-60:])
        vol = volumes[-1] / max(sum(volumes[-20:]) / max(len(volumes[-20:]), 1), 1e-9)
        score = recent_return * 2.5 + trend_strength * 3.0 + max(0.0, vol - 1.0) * 0.5
        if score > self.min_trend and atr > 0 and trend_strength > 0 and vol > self.min_vol:
            return 'buy', score
        if score < -self.min_trend and atr > 0 and trend_strength < 0 and vol > self.min_vol:
            return 'sell', score
        return 'hold', score


def run(product, cfg):
    closes, vols = fetch_candles(product, granularity=300, hours=720)
    strategy = Candidate(
        short_ema=cfg['short'],
        long_ema=cfg['long'],
        atr_mult=cfg['atr_mult'],
        min_trend=cfg['min_trend'],
        min_vol=cfg['min_vol'],
        stop_atr=cfg['stop_atr'],
        trail_atr=cfg['trail_atr'],
    )
    bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    bt.strategy = type('S', (), {'evaluate': lambda self, p, v: strategy.evaluate(p, v)})()
    result = bt.run(closes, vols)
    gate = LiveReadinessGate().score(result.net_return, result.max_drawdown, result.win_rate, result.trades, 3)
    return {
        'product': product,
        'params': cfg,
        'trades': result.trades,
        'wins': result.wins,
        'losses': result.losses,
        'net_return': round(result.net_return, 6),
        'win_rate': round(result.win_rate, 4),
        'max_drawdown': round(result.max_drawdown, 6),
        'ready': gate.ready,
        'score': round(gate.score, 4),
        'reasons': gate.reasons,
    }


configs = []
for short in [5, 8, 10, 12, 14]:
    for long in [15, 20, 25, 30, 35, 40, 50, 60]:
        if long <= short:
            continue
        for min_trend in [0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.01]:
            for min_vol in [0.7, 0.9, 1.0, 1.2, 1.5]:
                configs.append({'short': short, 'long': long, 'min_trend': min_trend, 'min_vol': min_vol, 'atr_mult': 2.0, 'stop_atr': 1.2, 'trail_atr': 0.8})

all_results = []
for product in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
    for cfg in configs:
        all_results.append(run(product, cfg))

ranked = sorted(all_results, key=lambda x: (x['ready'], x['score'], x['net_return'], x['win_rate'], x['trades']), reverse=True)
print(json.dumps(ranked[:30], indent=2))
print('READY_COUNT', sum(1 for r in ranked if r['ready']))
print('BEST_POSITIVE', max((r for r in ranked if r['net_return'] > 0), key=lambda r: (r['net_return'], r['win_rate'], r['trades']), default=None))
