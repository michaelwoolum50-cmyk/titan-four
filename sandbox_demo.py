from titan_four.backtest import MomentumBacktest


MARKETS = {
    "bull_run": [100, 101, 103, 106, 110, 116, 122, 129, 138, 145, 151, 156, 160, 158, 154, 149, 144, 139, 135, 130],
    "sideways": [100, 101, 100, 102, 101, 103, 102, 104, 103, 105, 104, 106, 105, 107, 106, 108, 107, 109, 108, 110],
    "reversal": [100, 102, 105, 109, 114, 119, 123, 120, 116, 111, 106, 101, 96, 91, 87, 84, 80, 79, 76, 72],
}


def main():
    for name, prices in MARKETS.items():
        volumes = [120] * len(prices)
        backtest = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
        result = backtest.run(prices, volumes)
        print(f"{name}: trades={result.trades}, wins={result.wins}, losses={result.losses}, net_return={result.net_return:.4f}, final_value={result.final_value:.2f}")


if __name__ == "__main__":
    main()
