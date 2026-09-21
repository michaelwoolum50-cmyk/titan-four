from paper_runner import summarize_result
from titan_four.paper_trading import LiveReadinessGate


def test_live_readiness_gate_is_conservative_by_default():
    gate = LiveReadinessGate()
    report = gate.score(
        net_return=0.02,
        max_drawdown=0.22,
        win_rate=0.48,
        trades=4,
        scenarios_passed=1,
    )

    assert report["ready"] is False
    assert report["reasons"]


def test_live_readiness_gate_allows_only_proven_strategies():
    gate = LiveReadinessGate()
    report = gate.score(
        net_return=0.14,
        max_drawdown=0.08,
        win_rate=0.62,
        trades=18,
        scenarios_passed=3,
    )

    assert report["ready"] is True


def test_market_summary_blocks_single_sample_live_readiness():
    report = summarize_result(
        "BTC-USD",
        {
            "trades": 4,
            "win_rate": 0.40,
            "max_drawdown": 0.14,
            "net_return": 0.02,
        },
    )

    assert report["ready"] is False
    assert "net_return_is_too_low" in report["reasons"] or "win_rate_too_low" in report["reasons"]
