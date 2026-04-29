# Test Modes — Quick Reference

See [docs/TEST_MODES.md](../docs/TEST_MODES.md) for detailed documentation.

## Commands

### Smoke tests (PR gate, ~2 min)
```bash
pytest -m smoke
```

### Deep tests (scheduled, ~10 min)
```bash
pytest -m "slow or e2e"
```

### Database integration tests
```bash
pytest -m db
```

### All tests except slow/e2e
```bash
pytest -m "not slow and not e2e and not synthetic"
```

### Specific workflow
```bash
pytest -m "smoke and workflow_backtest"
pytest -m "slow and workflow_live"
```

### Full suite
```bash
pytest -q
```

### With coverage
```bash
pytest -q --cov=src --cov-report=term-missing
```

### Strict marker mode
```bash
pytest --strict-markers -q
```

## Markers

| Marker | Tier | PR? | Scheduled? |
|--------|------|-----|-----------|
| `smoke` | Fast unit tests | ✅ | ✅ |
| `slow` | Long-running | ❌ | ✅ |
| `e2e` | End-to-end | ❌ | ✅ |
| `integration` | Multi-module | ❌ | ✅ |
| `db` | Requires database | ✅* | ✅ |
| `workflow_backtest` | Backtest workflow | ✅/✅ | ✅ |
| `workflow_live` | Live trading | ✅/✅ | ✅ |
| `workflow_backfill` | Backfill workflow | ✅/✅ | ✅ |
| `workflow_indicators` | Indicators | ✅/✅ | ✅ |
| `workflow_nlp` | NLP/sentiment | ✅/✅ | ✅ |

*if secrets available

## Environment Variables

```bash
# For deep tests (optional)
export DB_HOST=...
export DB_PORT=5432
export DB_NAME=...
export DB_USER=...
export DB_PASSWORD=...

# For synthetic monitoring
export FMP_API_KEY=...
```

## CI/CD

**PR**: smoke + db (if secrets) + coverage

**Scheduled (6h)**: smoke + slow/e2e + synthetic monitoring

See [.github/workflows/main.yml](../.github/workflows/main.yml) for details.
