from dataclasses import dataclass

from titan_four.strategy import MomentumStrategy


@dataclass
class BacktestResult:
    trades: int
    wins: int
    losses: int
    net_return: float
    win_rate: float
    max_drawdown: float
    equity_curve: list[float]
    final_value: float


class MomentumBacktest:
    def __init__(self, starting_cash=10000.0, position_fraction=0.2):
        self.starting_cash = starting_cash
        self.position_fraction = position_fraction
        self.strategy = MomentumStrategy()

    def run(self, prices, volumes):
        cash = self.starting_cash
        position = 0.0
        entry_price = 0.0
        trades = 0
        wins = 0
        losses = 0
        equity_curve = []
        peak = self.starting_cash
        max_drawdown = 0.0

        for idx in range(len(prices)):
            window_prices = prices[max(0, idx - 7):idx + 1]
            window_volumes = volumes[max(0, idx - 7):idx + 1]
            decision = self.strategy.evaluate(window_prices, window_volumes)

            if decision.signal == "buy" and position == 0:
                position = cash * self.position_fraction / max(prices[idx], 1e-9)
                entry_price = prices[idx]
                cash = cash - (position * prices[idx])
                trades += 1

            elif decision.signal == "sell" and position > 0:
                exit_value = position * prices[idx]
                pnl = exit_value - (position * entry_price)
                cash += exit_value
                position = 0.0
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

            current_value = cash + (position * prices[idx])
            equity_curve.append(current_value)
            if current_value > peak:
                peak = current_value
            drawdown = (peak - current_value) / peak if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        final_value = cash + position * prices[-1]
        net_return = (final_value - self.starting_cash) / self.starting_cash
        win_rate = wins / trades if trades > 0 else 0.0

        return BacktestResult(
            trades=trades,
            wins=wins,
            losses=losses,
            net_return=net_return,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            equity_curve=equity_curve,
            final_value=final_value,
        )
