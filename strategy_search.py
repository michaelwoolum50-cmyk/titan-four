"""Grid search over the SearchStrategy EMA/trend-strength space (rebuilt 2026-09-21).

Import-safe: importing this module does ZERO work (no network, no prints).
All executable logic lives in main(), under __main__.
Data comes from paper_runner.fetch_candles (cached 6h; each product fetched once).
"""
import json
from dataclasses import dataclass, asdict

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.strategy import StrategyDecision
from titan_four.paper_trading import LiveReadinessGate


@dataclass
class SearchStrategy:
    short_span: int = 8
    long_span: int = 21
    buy_threshold: float = 0.01
    sell_threshold: float = -0.01
    min_return: float = 0.003
    min_sell_return: float = -0.003
    min_volume_ratio: float = 0.7

    def _ema(self, vals, span):
        if not vals:
            return 0.0
        k = 2.0 / (span + 1.0)
        ema = vals[0]
        for v in vals[1:]:
            ema = (v * k) + (ema * (1.0 - k))
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
        score = (recent_return * 2.5 + trend_strength * 3.0
                 + max(0.0, volume_ratio - 1.0) * 0.3)

        if (recent_return > self.min_return and trend_strength > 0
                and score > self.buy_threshold
                and volume_ratio >= self.min_volume_ratio):
            return StrategyDecision('buy', min(max(0.5 + score, 0.0), 1.0), 'trend_bull')
        if (recent_return < self.min_sell_return and trend_strength < 0
                and score < self.sell_threshold
                and volume_ratio >= self.min_volume_ratio):
            return StrategyDecision('sell', min(max(0.5 + abs(score), 0.0), 1.0), 'trend_bear')
        return StrategyDecision('hold', min(max(score, 0.0), 1.0), 'neutral')


# Bounded grid: 72 configs/product.
PRODUCTS = ['BTC-USD', 'ETH-USD']
SHORT_SPANS = [5, 8, 10]
LONG_SPANS = [18, 21, 30]
BUY_THRESHOLDS = [0.005, 0.01]
SELL_THRESHOLDS = [-0.005, -0.01]
MIN_RETURNS = [0.003, 0.005]

GRANULARITY = 300
HOURS = 168


def build_configs():
    configs = []
    for short in SHORT_SPANS:
        for long in LONG_SPANS:
            if long <= short:
                continue
            for buy in BUY_THRESHOLDS:
                for sell in SELL_THRESHOLDS:
                    for min_return in MIN_RETURNS:
                        configs.append({
                            'short_span': short,
                            'long_span': long,
                            'buy_threshold': buy,
                            'sell_threshold': sell,
                            'min_return': min_return,
                            'min_sell_return': -min_return,
                        })
    return configs


def score_config(cfg, closes, vols, product):
    strategy = SearchStrategy(**cfg)
    bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    bt.strategy = strategy
    result = bt.run(closes, vols)
    gate = LiveReadinessGate().score(
        result.net_return, result.max_drawdown, result.win_rate, result.trades, 3
    )
    return {
        'product': product,
        'cfg': cfg,
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
    top_candidate = ranked[0] if ranked else None

    print('READY_COUNT', ready_count)
    print('BEST_POSITIVE', json.dumps(best_positive))
    print('TOP_CANDIDATE', json.dumps(top_candidate))
    print('TOTAL_CONFIGS', len(all_results))


if __name__ == '__main__':
    main()
