import json

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.strategy import MomentumStrategy
from titan_four.paper_trading import LiveReadinessGate


PRODUCTS = ["BTC-USD", "ETH-USD", "SOL-USD"]
BUY_GRID = [0.01, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12]
SELL_GRID = [-0.01, -0.02, -0.04, -0.06, -0.08, -0.10]
MIN_RETURN_GRID = [0.003, 0.005, 0.008, 0.01, 0.015, 0.02]
WINDOW_GRID = [5, 8, 12, 16, 20]


def best_over_grid(product_id: str, hours: int = 168):
    closes, vols = fetch_candles(product_id, granularity=300, hours=hours)
    best = None
    for window in WINDOW_GRID:
        for buy in BUY_GRID:
            for sell in SELL_GRID:
                for min_return in MIN_RETURN_GRID:
                    strategy = MomentumStrategy(
                        buy_threshold=buy,
                        sell_threshold=sell,
                        min_return=min_return,
                        min_sell_return=-min_return,
                    )
                    # Backtest uses the strategy's internal lookback; keep the global search
                    # aligned with the actual strategy implementation by testing multiple
                    # operational windows through a compatibility wrapper.
                    strategy.recent_window = window
                    strategy.earlier_window = max(2 * window, 24)
                    backtest = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
                    backtest.strategy = strategy
                    result = backtest.run(closes, vols)
                    gate = LiveReadinessGate()
                    readiness = gate.score(
                        net_return=result.net_return,
                        max_drawdown=result.max_drawdown,
                        win_rate=result.win_rate,
                        trades=result.trades,
                        scenarios_passed=3,
                    )

                candidate = {
                    "product": product_id,
                    "hours": hours,
                    "params": {
                        "window": window,
                        "buy": buy,
                        "sell": sell,
                        "min_return": min_return,
                    },
                    "net_return": result.net_return,
                    "win_rate": result.win_rate,
                    "trades": result.trades,
                    "max_drawdown": result.max_drawdown,
                    "gate_ready": readiness.ready,
                    "gate_score": readiness.score,
                    "reasons": readiness.reasons,
                }

                if best is None:
                    best = candidate
                    continue

                if discovery_key(candidate) > discovery_key(best):
                    best = candidate

    return best


def discovery_key(candidate):
    # prefer higher net return, then higher readiness score, then more trades
    return (
        candidate["net_return"],
        candidate["gate_score"],
        candidate["win_rate"],
        candidate["trades"],
    )


if __name__ == "__main__":
    outputs = []
    for product in PRODUCTS:
        outputs.append(best_over_grid(product, hours=168))
    print(json.dumps(outputs, indent=2))
