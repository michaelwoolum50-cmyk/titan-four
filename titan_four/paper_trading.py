from dataclasses import dataclass


@dataclass
class ReadinessReport:
    ready: bool
    reasons: list[str]
    score: float

    def __getitem__(self, key):
        if key == "ready":
            return self.ready
        if key == "reasons":
            return self.reasons
        if key == "score":
            return self.score
        raise KeyError(key)


class LiveReadinessGate:
    """Conservative gate before any real-money trading."""

    def score(self, net_return, max_drawdown, win_rate, trades, scenarios_passed):
        reasons = []
        score = 0.0

        if net_return >= 0.10:
            score += 0.35
        elif net_return >= 0.05:
            score += 0.20
        else:
            reasons.append("net_return_is_too_low")

        if max_drawdown <= 0.10:
            score += 0.25
        elif max_drawdown <= 0.20:
            score += 0.15
        else:
            reasons.append("max_drawdown_too_high")

        if win_rate >= 0.60:
            score += 0.20
        elif win_rate >= 0.50:
            score += 0.10
        else:
            reasons.append("win_rate_too_low")

        if trades >= 20:
            score += 0.10
        elif trades >= 10:
            score += 0.05
        else:
            reasons.append("too_few_trades")

        if scenarios_passed >= 3:
            score += 0.10
        else:
            reasons.append("insufficient_varied_scenarios")

        ready = score >= 0.85 and not reasons
        return ReadinessReport(ready=ready, reasons=reasons, score=score)
