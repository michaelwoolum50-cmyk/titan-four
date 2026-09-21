from titan_four.paper_trading import LiveReadinessGate


def evaluate_strategy(backtest_results):
    gate = LiveReadinessGate()
    return gate.score(
        net_return=backtest_results["net_return"],
        max_drawdown=backtest_results["max_drawdown"],
        win_rate=backtest_results["win_rate"],
        trades=backtest_results["trades"],
        scenarios_passed=backtest_results["scenarios_passed"],
    )
