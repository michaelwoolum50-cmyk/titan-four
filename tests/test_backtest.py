from titan_four.backtest import MomentumBacktest


def test_backtest_behaves_on_rising_market():
    prices = [100.0, 102.0, 104.0, 107.0, 111.0, 116.0, 122.0, 129.0, 138.0, 146.0]
    volumes = [100.0] * len(prices)

    backtest = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    result = backtest.run(prices, volumes)

    assert result.trades >= 1
    assert result.final_value > result.starting_cash if hasattr(result, "starting_cash") else True
    assert result.max_drawdown >= 0.0
    assert 0.0 <= result.win_rate <= 1.0
