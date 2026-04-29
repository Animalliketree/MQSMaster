from datetime import datetime, timedelta, timezone

import pytest

from src.portfolios.indicators.relative_momentum_index import RelativeMomentumIndex
from src.portfolios.indicators.relative_strength_index import RelativeStrengthIndex
from src.portfolios.indicators.simple_moving_average import SimpleMovingAverage

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.workflow_indicators,
]


def _feed_indicator(indicator, prices):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for idx, price in enumerate(prices):
        ts = start + timedelta(days=idx)
        indicator.Update(ts, price)


def test_rmi_becomes_ready_and_within_range():
    rmi = RelativeMomentumIndex("AAPL", period=14, momentum_period=3)
    prices = [100 + (i * 0.3) for i in range(50)]
    _feed_indicator(rmi, prices)

    assert rmi.IsReady
    assert 0.0 <= rmi.Current <= 100.0


def test_rsi_value_range_validation():
    rsi = RelativeStrengthIndex("AAPL", period=14)
    prices = [100 + (i * 0.5) for i in range(40)]
    _feed_indicator(rsi, prices)

    assert rsi.IsReady
    assert 0.0 <= rsi.Current <= 100.0


def test_sma_convergence():
    sma = SimpleMovingAverage("AAPL", period=5)
    prices = [10, 20, 30, 40, 50]
    _feed_indicator(sma, prices)

    assert sma.IsReady
    assert sma.Current == pytest.approx(30.0)


def test_indicator_monotonicity_for_increasing_prices():
    sma = SimpleMovingAverage("AAPL", period=3)
    prices = [100, 101, 102, 103, 104, 105]
    values = []

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for idx, price in enumerate(prices):
        sma.Update(start + timedelta(days=idx), price)
        if sma.IsReady:
            values.append(sma.Current)

    assert values
    assert all(curr >= prev for prev, curr in zip(values, values[1:]))
