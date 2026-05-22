# tests/test_api_endpoints.py
import os
from datetime import datetime, timedelta

import pytest

from src.orchestrator.marketData.fmpMarketData import FMPMarketData

RUN_LIVE_API_TESTS = os.getenv("RUN_LIVE_API_TESTS", "").strip() == "1"

pytestmark = [
    pytest.mark.api,
    pytest.mark.integration,
    pytest.mark.workflow_nlp,
    pytest.mark.skipif(
        not RUN_LIVE_API_TESTS,
        reason=(
            "Opt-in live API tests are disabled by default. "
            "Set RUN_LIVE_API_TESTS=1 to run manually."
        ),
    ),
]


@pytest.fixture
def start_date():
    start_date = datetime.now() - timedelta(days=7)
    return start_date.strftime("%Y-%m-%d")


@pytest.fixture
def end_date():
    return datetime.now().strftime("%Y-%m-%d")


@pytest.fixture
def fmp():
    return FMPMarketData()


def test_historical_data(fmp, start_date, end_date):
    data = fmp.get_historical_data("AAPL", start_date, end_date)
    assert data is not None, "Historical data returned None"
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    assert len(data) > 0, "Historical data returned empty list"


def test_intraday_data(fmp, start_date, end_date):
    data = fmp.get_intraday_data("AAPL", start_date, end_date, 5)
    assert data is not None, "Intraday data returned None"
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    assert len(data) > 0, "Intraday data returned empty list"


def test_realtime_data(fmp, start_date, end_date):
    data = fmp.get_realtime_data("NASDAQ")
    assert data is not None, "Realtime data returned None"
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    assert len(data) > 0, "Realtime data returned empty list"


def test_curent_price(fmp):
    price = fmp.get_current_price("AAPL")
    assert isinstance(price, float) and price > 0, "Current Price api failed"
