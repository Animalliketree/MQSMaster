# NLP Sentiment Pipeline

This guide documents the NLP article scraping and sentiment pipeline in detail. The matching quick command reference lives in [NLP/README.md](../../NLP/README.md).

## Overview

The NLP system has three main entrypoints:

- `NLP/daemon.py` for continuous batched scraping and processing
- `NLP/fetch_articles.py` for one-off article fetches
- `NLP/process_sentiment_pipeline.py` for sentiment scoring and database writes

A separate synthetic health-check path lives in `NLP/monitor_daemon.py`.

## Runtime Model

The daemon runs continuously with a repeating cycle:

- Main scrape interval: 5 minutes
- Delay between batches: 2 minutes
- Batches are generated dynamically from portfolio config files
- Unsupported tickers are filtered before batching
- Recent activity is tracked to skip repeated sentiment processing when there are no new articles

## Key Commands

### Start the daemon

```bash
python NLP/daemon.py start
```

### Fetch articles manually

```bash
python -m NLP.fetch_articles AAPL 2025-12-01 2025-12-31
```

### Run sentiment processing

```bash
python -m NLP.process_sentiment_pipeline AAPL MSFT
```

### Test the pipeline

```bash
python -m NLP.test_pipeline
```

### Query the database

```bash
python -m NLP.update_database --query AAPL MSFT
```

### Run synthetic monitoring

```bash
python NLP/monitor_daemon.py --synthetic --max-log-age-hours 72
```

## Key Files

### Core pipeline

- `daemon.py` - portfolio-driven scraper and sentiment daemon
- `fetch_articles.py` - article scraping and per-ticker CSV generation
- `process_sentiment_pipeline.py` - sentiment scoring and persistence
- `sentiment_processor.py` - FinBERT sentiment scoring helpers
- `update_database.py` - database integration and query helpers

### Monitoring and utilities

- `monitor_daemon.py` - synthetic checks for external health
- `test_pipeline.py` - end-to-end pipeline validation
- `fetch_alt_articles.py` - alternate article fetch path
- `news_scraper.py` - scraper helpers for individual sources

## Data Layout

### Articles

Stored under `NLP/articles/` as per-ticker CSVs.

Examples:

- `AAPL.csv`
- `MSFT.csv`
- `GOOGL.csv`

### Sentiment scores

Stored under `NLP/sentiment_scores/` as per-ticker outputs.

Examples:

- `AAPL_article_scores.csv`
- `AAPL_daily_scores.csv`

### Model assets

The FinBERT model lives in `NLP/finbert-combined-final/`.

## Portfolio-Driven Batching

The daemon loads tickers from portfolio config files under `src/portfolios/` and splits them into roughly equal batches.

Behavior:

- Reads tickers from portfolio configs in order
- Deduplicates tickers while preserving first-seen order
- Excludes tickers in the configured skip set, such as `^VIX`
- Builds up to four batches from the resulting list
- Processes each batch with a pause between batches

This means batch contents are data-driven and may change when portfolio configs change.

## Processing Flow

```text
Article scraping
      ↓
Per-ticker CSV merge
      ↓
Sentiment scoring with FinBERT
      ↓
Database update
      ↓
Trading strategy access
```

## Database Schema

The `news_sentiment` table stores:

- `ticker` - stock symbol
- `article_url` - unique article identifier
- `published_at` - article publication timestamp
- `sentiment_score` - FinBERT score in the range `[-1.0, 1.0]`
- `content_summary` - article summary or excerpt

## Monitoring and Logs

The daemon writes logs to `NLP/daemon.log` and reports:

- batch startup and completion
- fetch status per ticker
- sentiment processing status
- skip decisions for low-activity tickers
- memory cleanup activity
- errors and retries

## Configuration Notes

### Timing

- Scrape cycle interval: 300 seconds
- Delay between batches: 120 seconds
- Memory cleanup interval: every 10 cycles
- Log rotation size: 10 MB

### Environment

Typical runtime requirements include:

- Python dependencies from `requirements.txt`
- portfolio config files under `src/portfolios/`
- database connectivity for sentiment persistence
- optional market-data and API credentials for source fetches

## Legacy and Manual Workflows

Use the one-off commands above when you want to run a single pipeline step. Use the daemon only when you want continuous scheduled batching.

## Troubleshooting

### No tickers loaded

Check the portfolio config files under `src/portfolios/` and confirm they contain `TICKERS` entries.

### No new articles found

This is usually expected when the source has already been processed recently or no fresh articles exist for the selected date range.

### Sentiment step skipped

The daemon skips sentiment work when recent cycles show no new articles for a ticker.

### Monitoring failures

Use `NLP/monitor_daemon.py` for synthetic checks instead of treating external service probing as part of the normal pytest suite.

## Related Docs

- [Quick NLP commands](../../NLP/README.md)
- [Test modes](../TEST_MODES.md)
