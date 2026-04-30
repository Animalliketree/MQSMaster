# NLP Commands

## Quick Commands

```bash
python NLP/daemon.py start
python -m NLP.fetch_articles AAPL 2025-12-01 2025-12-31
python -m NLP.process_sentiment_pipeline AAPL MSFT
python -m NLP.test_pipeline
python -m NLP.update_database --query AAPL MSFT
python NLP/monitor_daemon.py --synthetic --max-log-age-hours 72
```

## More Details

See [docs/NLP/README.md](../docs/NLP/README.md) for the full NLP pipeline guide, runtime behavior, data layout, and monitoring notes.
