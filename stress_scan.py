import json

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.strategy import MomentumStrategy
from titan_four.paper_trading import LiveReadinessGate

PRODUCTS = ["BTC-USD", "ETH-USD", "SOL-USD"]
BUY_GRID = [0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]
SELL_GRID = [-0.003, -0.005, -0.008, -0.01, -0.015, -0.02, -0.03]
MIN_RETURN_GRID = [0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]
WINDOWS = [24, 72, 168, 336, 720]


def evaluate(product_id, hours):
    closes, vols = fetch_candles(product_id, granularity=300, hours=hours)
    best = None
    for buy in BUY_GRID:
        for sell in SELL_GRID:
            for minr in MIN_RETURN_GRID:
                strategy = MomentumStrategy(
                    buy_threshold=buy,
                    sell_threshold=sell,
                    min_return=minr,
                    min_sell_return=-minr,
                )
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
                    "params": {"buy": buy, "sell": sell, "min_return": minr},
                    "net_return": round(result.net_return, 6),
                    "win_rate": round(result.win_rate, 4),
                    "trades": result.trades,
                    "drawdown": round(result.max_drawdown, 6),
                    "gate_ready": readiness.ready,
                    "gate_score": readiness.score,
                    "reasons": readiness.reasons,
                }
                if best is None or candidate["net_return"] > best["net_return"]:
                    best = candidate
    return best


if __name__ == "__main__":
    output = []
    for product in PRODUCTS:
        for hours in WINDOWS:
            output.append(evaluate(product, hours))
    print(json.dumps(output, indent=2))
