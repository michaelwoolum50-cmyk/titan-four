from __future__ import annotations

from typing import Iterable, Sequence

from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate
from titan_four.strategy import MomentumStrategy


def _candidate_score(net_return: float, win_rate: float, trades: int, gate: LiveReadinessGate) -> float:
    """Weighted scoring used to rank candidate strategies.

    The gate still decides whether a strategy is live-eligible, but this score is
    useful for selecting the strongest candidate within the sandbox search.
    """
    return (
        gate.score
        + max(net_return, 0.0) * 2.0
        + max(win_rate, 0.0) * 1.5
        + min(max(trades, 0), 100) * 0.01
    )


def select_best_candidate(
    prices: Sequence[float],
    volumes: Sequence[float],
    buy_grid: Iterable[float],
    sell_grid: Iterable[float],
    min_return_grid: Iterable[float],
    *,
    starting_cash: float = 10000.0,
    position_fraction: float = 0.2,
    scenarios_passed: int = 3,
):
    """Evaluate a grid of momentum candidates and return the best one.

    The result is intentionally conservative: a strategy must satisfy the live
    readiness gate to become eligible. In sandbox mode we still rank candidates by
    score so the system can surface the strongest option even when none are ready.
    """
    if len(prices) < 8 or len(volumes) < 8:
        raise ValueError("prices and volumes must include at least 8 samples")

    best = None
    best_score = float("-inf")

    for buy in buy_grid:
        for sell in sell_grid:
            for min_return in min_return_grid:
                strategy = MomentumStrategy(
                    buy_threshold=float(buy),
                    sell_threshold=float(sell),
                    min_return=float(min_return),
                    min_sell_return=-float(min_return),
                )
                backtest = MomentumBacktest(starting_cash=starting_cash, position_fraction=position_fraction)
                backtest.strategy = strategy
                result = backtest.run(list(float(v) for v in prices), list(float(v) for v in volumes))
                gate = LiveReadinessGate().score(
                    net_return=result.net_return,
                    max_drawdown=result.max_drawdown,
                    win_rate=result.win_rate,
                    trades=result.trades,
                    scenarios_passed=scenarios_passed,
                )
                candidate_score = _candidate_score(result.net_return, result.win_rate, result.trades, gate)
                candidate = {
                    "buy": float(buy),
                    "sell": float(sell),
                    "min_return": float(min_return),
                    "trades": result.trades,
                    "wins": result.wins,
                    "losses": result.losses,
                    "net_return": result.net_return,
                    "win_rate": result.win_rate,
                    "max_drawdown": result.max_drawdown,
                    "final_value": result.final_value,
                    "gate_ready": gate.ready,
                    "gate_score": gate.score,
                    "reasons": list(gate.reasons),
                    "candidate_score": candidate_score,
                    "best_score": None,
                }
                if candidate_score > best_score:
                    best = candidate
                    best_score = candidate_score

    if best is None:
        raise ValueError("No candidate configuration was evaluated")

    best["best_score"] = best_score
    return best
