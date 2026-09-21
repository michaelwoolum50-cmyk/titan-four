import json
import time
from typing import Any

import requests

from paper_runner import fetch_candles
from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate
from titan_four.strategy import MomentumStrategy


def fetch_live_ticks(product_id: str, trade_limit: int = 100, samples: int = 5) -> list[float]:
    prices: list[float] = []
    for _ in range(samples):
        response = requests.get(
            f"https://api.exchange.coinbase.com/products/{product_id}/trades",
            params={"limit": str(trade_limit)},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        prices.extend(float(item["price"]) for item in data)
        time.sleep(0.5)
    return prices[-(trade_limit * samples):]


def evaluate_live_ticks(product_id: str, prices: list[float]) -> dict[str, Any]:
    if len(prices) < 8:
        raise ValueError(f"Not enough live tick prices for {product_id}")

    strategy = MomentumStrategy()
    backtest = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    backtest.strategy = strategy
    result = backtest.run(prices, [1.0] * len(prices))
    gate = LiveReadinessGate()
    report = gate.score(
        net_return=result.net_return,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        trades=result.trades,
        scenarios_passed=1,
    )
    return {
        "product": product_id,
        "samples": len(prices),
        "trades": result.trades,
        "wins": result.wins,
        "losses": result.losses,
        "net_return": round(result.net_return, 6),
        "win_rate": round(result.win_rate, 4),
        "max_drawdown": round(result.max_drawdown, 6),
        "final_value": round(result.final_value, 2),
        "ready": report.ready,
        "score": round(report.score, 2),
        "reasons": report.reasons,
    }


def evaluate_thresholds(product_id: str, hours: int):
    closes, vols = fetch_candles(product_id, granularity=300, hours=hours)
    best = {
        "net_return": float("-inf"),
        "buy": None,
        "sell": None,
        "min_return": None,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
    }

    for buy in [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]:
        for sell in [-0.02, -0.03, -0.04, -0.05, -0.06, -0.08, -0.10]:
            for min_return in [0.002, 0.005, 0.01, 0.02]:
                cash = 10000.0
                position = 0.0
                entry_price = 0.0
                trades = 0
                wins = 0
                losses = 0

                for i in range(8, len(closes) - 1):
                    recent = closes[max(0, i - 7): i + 1]
                    earlier = closes[max(0, i - 15): i - 7] if i - 7 > 0 else closes[: i + 1]
                    if not earlier:
                        earlier = closes[: i + 1]

                    recent_start = recent[0]
                    recent_end = recent[-1]
                    recent_return = (recent_end - recent_start) / recent_start if recent_start else 0.0

                    early_avg = sum(earlier) / len(earlier)
                    recent_avg = sum(recent) / len(recent)
                    slope = (recent_avg - early_avg) / max(abs(early_avg), 1e-9)

                    avg_volume = sum(vols[max(0, i - 7): i + 1]) / len(vols[max(0, i - 7): i + 1])
                    vol_strength = vols[i] / max(avg_volume, 1e-9)
                    momentum_score = recent_return + (slope * 0.5) + (vol_strength - 1.0) * 0.2

                    if momentum_score > buy and recent_return > min_return and position == 0:
                        position = cash * 0.2 / max(closes[i], 1e-9)
                        entry_price = closes[i]
                        cash -= position * closes[i]
                        trades += 1
                    elif (momentum_score < sell or recent_return < -min_return) and position > 0:
                        cash += position * closes[i]
                        position = 0.0
                        if closes[i] > entry_price:
                            wins += 1
                        else:
                            losses += 1

                final_value = cash + position * closes[-1]
                net_return = (final_value - 10000.0) / 10000.0
                win_rate = wins / trades if trades > 0 else 0.0

                if trades > 0 and net_return > best["net_return"]:
                    best = {
                        "net_return": float(net_return),
                        "buy": buy,
                        "sell": sell,
                        "min_return": min_return,
                        "trades": trades,
                        "wins": wins,
                        "losses": losses,
                        "win_rate": float(win_rate),
                    }

    gate = LiveReadinessGate()
    readiness = gate.score(
        net_return=best["net_return"],
        max_drawdown=0.15,
        win_rate=best["win_rate"],
        trades=best["trades"],
        scenarios_passed=1,
    )

    return {
        "product": product_id,
        "hours": hours,
        "samples": len(closes),
        "best": best,
        "live_readiness": {
            "ready": readiness.ready,
            "score": readiness.score,
            "reasons": readiness.reasons,
        },
    }


def main():
    results = []
    for product_id in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        tick_prices = fetch_live_ticks(product_id, trade_limit=50, samples=4)
        results.append(evaluate_live_ticks(product_id, tick_prices))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
