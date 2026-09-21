import json
from dataclasses import dataclass

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate


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
            return type('D', (), {'signal': 'hold', 'confidence': 0.0, 'reason': 'insufficient'})()

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
            return type('D', (), {'signal': 'hold', 'confidence': 0.5, 'reason': 'choppy'})()

        if recent_return > self.min_return and spread > self.spread_min and vol_ratio >= self.min_vol_ratio and score > self.buy_threshold:
            return type('D', (), {'signal': 'buy', 'confidence': min(max(0.55 + score, 0.0), 1.0), 'reason': 'buy_signal'})()

        if recent_return < -self.min_return and spread < -self.spread_min and vol_ratio >= self.min_vol_ratio and score < self.sell_threshold:
            return type('D', (), {'signal': 'sell', 'confidence': min(max(0.55 + abs(score), 0.0), 1.0), 'reason': 'sell_signal'})()

        return type('D', (), {'signal': 'hold', 'confidence': min(max(score, 0.0), 1.0), 'reason': 'neutral'})()


PRODUCTS = ['BTC-USD', 'ETH-USD', 'SOL-USD']


def score_config(product, cfg):
    closes, vols = fetch_candles(product, granularity=300, hours=168)
    strategy = CandidateStrategy(**cfg)
    bt = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    bt.strategy = strategy
    result = bt.run(closes, vols)
    gate = LiveReadinessGate().score(result.net_return, result.max_drawdown, result.win_rate, result.trades, 3)
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
    configs = []
    for short in [5, 8, 10, 12]:
        for long in [15, 20, 25, 30, 35, 40, 50]:
            if long <= short:
                continue
            for spread in [0.00005, 0.0001, 0.0002, 0.00035, 0.0005, 0.0008]:
                for buy in [0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.012]:
                    for min_return in [0.0004, 0.0008, 0.0012, 0.002, 0.003, 0.004]:
                        for volume in [0.5, 0.7, 0.9, 1.1]:
                            configs.append({
                                'short_span': short,
                                'long_span': long,
                                'spread_min': spread,
                                'buy_threshold': buy,
                                'sell_threshold': -buy,
                                'min_return': min_return,
                                'min_vol_ratio': volume,
                            })

    all_results = []
    for product in PRODUCTS:
        for cfg in configs:
            all_results.append(score_config(product, cfg))

    ranked = sorted(
        all_results,
        key=lambda item: (item['ready'], item['score'], item['net_return'], item['win_rate'], item['trades']),
        reverse=True,
    )

    print(json.dumps(ranked[:30], indent=2))
    print('READY_COUNT', sum(1 for item in ranked if item['ready']))
    print('TOP_POSITIVE', max((item for item in ranked if item['net_return'] > 0), key=lambda item: (item['net_return'], item['win_rate'], item['trades']), default=None))


if __name__ == '__main__':
    main()
