from market_probe import fetch_live_ticks
from titan_four.strategy import MomentumStrategy
from titan_four.risk import RiskManager


def test_fetch_live_ticks_returns_chronological_prices(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    payloads = [
        [{"price": "102.00"}, {"price": "101.50"}, {"price": "101.00"}],
        [{"price": "100.75"}, {"price": "100.50"}, {"price": "100.25"}],
    ]

    def fake_get(*args, **kwargs):
        return FakeResponse(payloads.pop(0))

    monkeypatch.setattr("market_probe.requests.get", fake_get)

    prices = fetch_live_ticks("BTC-USD", trade_limit=3, samples=2)

    assert prices == [100.25, 100.5, 100.75, 101.0, 101.5, 102.0]


def test_buy_signal_when_momentum_is_strong_and_positive():
    prices = [100.0, 101.0, 103.0, 106.0, 110.0, 116.0, 122.0, 129.0]
    volumes = [120.0] * len(prices)

    strategy = MomentumStrategy()
    decision = strategy.evaluate(prices, volumes)

    assert decision.signal == "buy"
    assert decision.confidence > 0.5


def test_sell_signal_when_trend_reverses():
    prices = [129.0, 126.0, 121.0, 115.0, 109.0, 104.0, 99.0, 94.0]
    volumes = [120.0] * len(prices)

    strategy = MomentumStrategy()
    decision = strategy.evaluate(prices, volumes)

    assert decision.signal == "sell"


def test_buy_signal_when_trend_is_clear_without_a_spike_breakout():
    prices = [100.0, 101.0, 101.5, 102.2, 102.8, 103.1, 103.9, 104.4, 104.8]
    volumes = [200.0] * len(prices)

    strategy = MomentumStrategy()
    decision = strategy.evaluate(prices, volumes)

    assert decision.signal == "buy"


def test_buy_signal_on_clear_uptrend_with_modest_volatility():
    prices = [100.0, 100.8, 101.9, 103.0, 104.1, 105.2, 106.1, 107.5, 108.8]
    volumes = [150.0] * len(prices)

    strategy = MomentumStrategy()
    decision = strategy.evaluate(prices, volumes)

    assert decision.signal == "buy"


def test_defaults_still_fire_on_healthy_uptrend_without_explosive_breakout():
    prices = [100.0, 100.5, 101.1, 101.8, 102.6, 103.4, 104.0, 104.9, 105.7, 106.8]
    volumes = [180.0] * len(prices)

    decision = MomentumStrategy().evaluate(prices, volumes)

    assert decision.signal == "buy"


def test_hold_when_market_is_choppy_even_if_prices_are_up():
    prices = [100.0, 101.0, 101.5, 102.0, 102.3, 102.1, 101.9, 101.8, 102.0, 101.7, 102.2, 102.0]
    volumes = [120.0] * len(prices)

    strategy = MomentumStrategy()
    decision = strategy.evaluate(prices, volumes)

    assert decision.signal == "hold"


def test_buy_signal_for_healthy_uptrend_with_short_pullbacks():
    prices = [110.73, 111.60, 112.70, 112.03, 112.34, 110.96, 111.06, 111.15]
    volumes = [100.0] * len(prices)

    decision = MomentumStrategy().evaluate(prices, volumes)

    assert decision.signal == "buy"
    assert decision.confidence > 0.5


def test_risk_manager_prevents_leverage_and_trims_position_size():
    risk = RiskManager(max_position_fraction=0.2, max_positions=3, leverage_allowed=False)

    assert risk.can_trade() is True
    assert risk.calculate_position_value(1000.0, 0.15) == 150.0
    assert risk.calculate_position_value(1000.0, 0.3) == 200.0
