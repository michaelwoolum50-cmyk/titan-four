"""Grid optimizer for the EMA-crossover CandidateStrategy (rebuilt 2026-09-21).

Import-safe: importing this module does ZERO work (no network, no prints).
All executable logic lives in main(), under __main__.
Data comes from paper_runner.fetch_candles (cached 6h; each product fetched once).
"""
import json
from dataclasses import dataclass, asdict

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate


@dataclass
class Decision:
    signal: str
    confidence: float
    reason: str


@dataclass
class CandidateStrategy:
    short_span: int = 8
    long_span: int = 21
    spread_min: float = 0.0002
    buy_threshold: float = 0.003
    sell_threshold: float = -0.003
    min_return: float = 0.001
    min_vol_ratio: float = 0.7

    def ema(self, values, span):
        if not values:
            return 0.0
        k = 2.0 / (span + 1.0)
        value = values[0]
        for item in values[1:]:
            value = (item * k) + (value * (1.0 - k))
        return value

    def evaluate(self, prices, volumes):
        prices = list(map(float, prices))
        volumes = list(map(float, volumes))
        if len(prices) < max(self.short_span, self.long_span):
            return Decision('hold', 0.0, 'insufficient')

        recent = prices[-self.short_span:]
        earlier = prices[-self.long_span:]
        short_ema = self.ema(recent, self.short_span)
        long_ema = self.ema(earlier, self.long_span)
        spread = (short_ema - long_ema) / max(abs(long_ema), 1e-9)

        recent_return = (prices[-1] - prices[0]) / max(abs(prices[0]), 1e-9)
        avg_vol = sum(volumes[-self.short_span:]) / max(len(volumes[-self.short_span:]), 1)
        vol_ratio = volumes[-1] / max(avg_vol, 1e-9)
        score = recent_return * 3.0 + spread * 10.0 + max(0.0, vol_ratio - 1.0) * 0.5

        if abs(spread) < self.spread_min and abs(recent_return) < self.min_return * 2.0:
            return Decision('hold', 0.5, 'choppy')

        if (recent_return > self.min_return and spread > self.spread_min
                and vol_ratio >= self.min_vol_ratio and score > self.buy_threshold):
            return Decision('buy', min(max(0.55 + score, 0.0), 1.0), 'buy_signal')

        if (recent_return < -self.min_return and spread < -self.spread_min
                and vol_ratio >= self.min_vol_ratio and score < self.sell_threshold):
            return Decision('sell', min(max(0.55 + abs(score), 0.0), 1.0), 'sell_signal')

        return Decision('hold', min(max(score, 0.0), 1.0), 'neutral')


# Bounded grid (aim: full run finishes well under 10 minutes).
PRODUCTS = ['BTC-USD', 'ETH-USD', 'SOL-USD']
SHORT_SPANS = [5, 8, 12]
LONG_SPANS = [20, 30, 50]
SPREAD_MINS = [0.0001, 0.0003, 0.0006]
BUY_THRESHOLDS = [0.002, 0.005, 0.01]
MIN_RETURNS = [0.001, 0.002, 0.004]
MIN_VOL_RATIOS = [0.7, 1.0]

GRANULARITY = 300
HOURS = 168


def build_configs():
    configs = []
    for short in SHORT_SPANS:
        for long in LONG_SPANS:
            if long <= short:
                continue
            for spread in SPREAD_MINS:
                for buy in BUY_THRESHOLDS:
                    for min_return in MIN_RETURNS:
                        for vol_ratio in MIN_VOL_RATIOS:
                            configs.append({
                                'short_span': short,
                                'long_span': long,
                                'spread_min': spread,
                                'buy_threshold': buy,
                                'sell_threshold': -buy,
                                'min_return': min_return,
                                'min_vol_ratio': vol_ratio,
                            })
    return configs


def score_config(strategy_cfg, closes, vols, product):
    strategy = CandidateStrategy(**strategy_cfg)
    bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    bt.strategy = strategy
    result = bt.run(closes, vols)
    gate = LiveReadinessGate().score(
        result.net_return, result.max_drawdown, result.win_rate, result.trades, 3
    )
    return {
        'product': product,
        'cfg': strategy_cfg,
        'trades': result.trades,
        'wins': result.wins,
        'losses': result.losses,
        'net_return': round(result.net_return, 6),
        'win_rate': round(result.win_rate, 4),
        'max_drawdown': round(result.max_drawdown, 6),
        'final_value': round(result.final_value, 2),
        'ready': gate.ready,
        'score': round(gate.score, 4),
        'reasons': gate.reasons,
    }


def main():
    configs = build_configs()
    all_results = []
    for product in PRODUCTS:
        # Single fetch per product; cache makes this free on repeats.
        closes, vols = fetch_candles(product, granularity=GRANULARITY, hours=HOURS)
        for cfg in configs:
            all_results.append(score_config(cfg, closes, vols, product))

    ranked = sorted(
        all_results,
        key=lambda item: (
            item['ready'], item['score'], item['net_return'],
            item['win_rate'], item['trades'],
        ),
        reverse=True,
    )

    ready_count = sum(1 for item in ranked if item['ready'])
    best_positive = max(
        (item for item in ranked if item['net_return'] > 0),
        key=lambda item: (item['net_return'], item['win_rate'], item['trades']),
        default=None,
    )

    print(json.dumps(ranked[:15], indent=2))
    print('READY_COUNT', ready_count)
    print('BEST_POSITIVE', json.dumps(best_positive))
    print('TOTAL_CONFIGS', len(all_results))


if __name__ == '__main__':
    main()
