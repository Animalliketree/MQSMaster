from collections import defaultdict
from datetime import datetime

import pandas as pd

from src.portfolios.portfolio_BASE.strategy import BasePortfolio

from .data.backfill_cache import cache as _cache
from .data.backfill_cache.cache import load as _fetch_from_db
from .data.backfill_cache.cache import missing_ranges as _missing_ranges
from .data.backfill_cache.cache import save as _save_to_cache


def fetch_historical_data(
    portfolio: BasePortfolio, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """
    Returns daily OHLCV data for all portfolio tickers in [start_date, end_date].

    When db is queried for new tickers, new .parquet files are created in the cache
    which store tickers' data for the specified date range. Cached data is
    returned when possible. If a ticker is already cached but a date range is
    requested that is not included in the cache, db is queried for the missing
    ticker data and is added to the .parquet file.

    Files cached in src/backtest/data/backfill_cache/tickername.parquet.
    """
    logger = portfolio.logger  # Initialize debug logger
    tickers = getattr(portfolio, "tickers", [])  # Fetch desired tickers

    if not tickers:
        # If portfolio config has no tickers, return empty df
        logger.warning(
            "No tickers specified in the portfolio; returning empty DataFrame."
        )
        return pd.DataFrame()

    # Initialize start and end dates
    start = pd.to_datetime(start_date, utc=True)
    # Ensure end date includes the entire end day, up until close
    end = pd.to_datetime(end_date, utc=True) + pd.Timedelta(hours=23, minutes=59, seconds=59)

    # Load any available ticker data from local cache
    caches = {t: _cache.load(t) for t in tickers}

    # Group tickers in dict by missing date range needed for batching db queries. Speeds
    # up query time. E.g., If one portfolio backtested with 3 tickers for a given date
    # range, then another portfolio is backtested with a wider date range and 5 tickers,
    # 2 already having been cached from the previous backtest, then the missing
    # date range for both extant ticker caches is fetched in one db query.
    #
    #   {[start, end] : (ticker1, ticker2, ..., tickerk)}
    #
    # @see backfill_cache/cache.py for missing_ranges calculation
    range_to_tickers = defaultdict(list)
    for ticker in tickers:
        for gap in _cache.missing_ranges(caches[ticker], start, end):
            range_to_tickers[gap].append(ticker)

    # --- Step 2: Fetch each unique missing range from DB (batched by range) ---
    # Fetch each unique missing range from db. Batch identical ranges into one query.
    #
    if range_to_tickers:
        unique_tickers_needing_fetch = {
            t for ts in range_to_tickers.values() for t in ts
        }
        logger.info(
            "Cache miss: fetching %d date range(s) from DB covering %d ticker(s).",
            len(range_to_tickers),
            len(unique_tickers_needing_fetch),
        )
        for (gap_start, gap_end), gap_tickers in range_to_tickers.items():
            # query missing data for a given range and tickers missing that range.
            fetched = _fetch_from_db(portfolio, gap_tickers, gap_start, gap_end)
            if fetched.empty:
                continue
            for ticker in gap_tickers:
                ticker_rows = fetched[fetched["ticker"] == ticker]
                caches[ticker] = _cache.merge_and_save(
                    ticker, caches[ticker], ticker_rows
                )
    else:
        logger.info("Fetching all data from local cache")

    # Splice each ticker's cache to the specified range
    parts = []
    for ticker in tickers:
        df = caches[ticker]
        if not df.empty:
            parts.append(df[(df["timestamp"] >= start) & (df["timestamp"] <= end)])

    if not parts:
        # Failed to splice any data
        logger.error("No data available after cache splice.")
        return pd.DataFrame()

    # Concatenate processed (spliced) ticker data, sort by timestamp, reset index, return
    result = pd.concat(parts, ignore_index=True)
    result.sort_values("timestamp", inplace=True)
    result.reset_index(drop=True, inplace=True)
    logger.info(
        "Returning %d rows of historical data (%d tickers).", len(result), len(tickers)
    )
    return result
