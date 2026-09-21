import json

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.strategy import MomentumStrategy
from titan_four.paper_trading import LiveReadinessGate

PRODUCTS = ["BTC-USD", "ETH-USD", "SOL-USD"]
BUY_GRID = [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12]
SELL_GRID = [-0.005, -0.01, -0.02, -0.03, -0.05, -0.08, -0.12]
MIN_RETURN_GRID = [0.002, 0.004, 0.006, 0.008, 0.01, 0.015, 0.02, 0.03]


def score_candidate(product_id, buy, sell, minr, closes, vols):
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
    return {
        "product": product_id,
        "params": {"buy": buy, "sell": sell, "min_return": minr},
        "net_return": result.net_return,
        "win_rate": result.win_rate,
        "trades": result.trades,
        "drawdown": result.max_drawdown,
        "gate_ready": readiness.ready,
        "gate_score": readiness.score,
        "reasons": readiness.reasons,
    }


def main():
    results = []
    for product in PRODUCTS:
        closes, vols = fetch_candles(product, granularity=300, hours=720)
        best = None
        for buy in BUY_GRID:
            for sell in SELL_GRID:
                for minr in MIN_RETURN_GRID:
                    candidate = score_candidate(product, buy, sell, minr, closes, vols)
                    results.append(candidate)
                    if best is None:
                        best = candidate
                    else:
                        if candidate["net_return"] > best["net_return"]:
                            best = candidate
        print(json.dumps({"product": product, "best": best}, indent=2))


if __name__ == "__main__":
    main()
