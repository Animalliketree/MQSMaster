import math
from datetime import datetime, timedelta, timezone

import pandas as pd

from src.portfolios.portfolio_3.strategy import RegimeAdaptiveStrategy


def _build_history_rows(ticker: str, start_ts: datetime, count: int):
    rows = []
    for idx in range(count):
        ts = start_ts + timedelta(minutes=idx)
        if ticker == "^VIX":
            close = 17.0 + (idx * 0.02)
        else:
            close = 100.0 + (idx * 0.35)
        high = close + 0.7
        low = close - 0.7
        open_price = close - 0.2
        volume = 1000 + (idx * 10)
        rows.append(
            {
                "timestamp": ts,
                "ticker": ticker,
                "open_price": open_price,
                "high_price": high,
                "low_price": low,
                "close_price": close,
                "volume": volume,
            }
        )
    return rows


class _FakeDB:
    def __init__(self, rows_by_ticker):
        self._rows_by_ticker = rows_by_ticker

    def execute_query(self, _sql, params, fetch="all"):
        ticker = params[0]
        return {"status": "success", "data": self._rows_by_ticker.get(ticker, [])}


class _FakeExecutor:
    def __init__(self):
        self.trades = []

    def execute_trade(self, **kwargs):
        self.trades.append(kwargs)


def test_portfolio3_indicators_are_ready_and_finite_after_updates():
    backtest_start = datetime(2025, 1, 10, 15, 30, tzinfo=timezone.utc)
    warmup_start = backtest_start - timedelta(minutes=80)
    rows_by_ticker = {
        "AAPL": _build_history_rows("AAPL", warmup_start, 80),
        "^VIX": _build_history_rows("^VIX", warmup_start, 80),
    }

    strategy = RegimeAdaptiveStrategy(
        db_connector=_FakeDB(rows_by_ticker),
        executor=_FakeExecutor(),
        debug=True,
        config_dict={
            "PORTFOLIO_ID": "3",
            "TICKERS": ["AAPL", "^VIX"],
            "INTERVAL": 60,
            "LOOKBACK_DAYS": 90,
            "DATA_FEEDS": ["MARKET_DATA", "POSITIONS", "CASH_EQUITY", "PORT_NOTIONAL"],
        },
        backtest_start_date=backtest_start,
    )

    for name in ("vwap", "atr", "momentum_pct"):
        indicator = getattr(strategy, name)["AAPL"]
        assert indicator.IsReady, f"{name} should be ready after warmup"
        assert indicator.Current is not None, f"{name} should have a current value"
        assert math.isfinite(indicator.Current), f"{name} should be finite"

    next_ts = backtest_start + timedelta(minutes=1)
    live_market_data = pd.DataFrame(
        [
            {
                "timestamp": next_ts,
                "ticker": "AAPL",
                "open_price": 131.0,
                "high_price": 132.0,
                "low_price": 130.0,
                "close_price": 131.5,
                "volume": 2500,
            },
            {
                "timestamp": next_ts,
                "ticker": "^VIX",
                "open_price": 18.0,
                "high_price": 18.2,
                "low_price": 17.8,
                "close_price": 18.1,
                "volume": 1000,
            },
        ]
    )

    strategy.generate_signals_and_trade(
        {
            "MARKET_DATA": live_market_data,
            "POSITIONS": pd.DataFrame([{"ticker": "AAPL", "quantity": 0.0}]),
            "CASH_EQUITY": pd.DataFrame([{"notional": 100000.0}]),
            "PORT_NOTIONAL": pd.DataFrame([{"notional": 100000.0}]),
        },
        current_time=next_ts,
    )

    for name in ("vwap", "atr", "momentum_pct"):
        indicator = getattr(strategy, name)["AAPL"]
        assert indicator.IsReady, f"{name} should remain ready after live update"
        assert indicator.Current is not None, f"{name} should keep a current value"
        assert math.isfinite(indicator.Current), f"{name} should remain finite"
