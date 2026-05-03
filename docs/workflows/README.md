# Workflow Diagrams

Architecture and data flow diagrams for the MQS Trading System core (`src/`). For an index of all docs, see [../README.md](../README.md).

## Diagrams

| File | Topic |
|------|-------|
| [system-architecture.md](system-architecture.md) | High-level system overview — entry points, engines, executors, data layer |
| [backtest-flow.md](backtest-flow.md) | Backtest driver: multiprocess pool → engine → event vs fast (vectorized + Monte Carlo) |
| [live-trading-flow.md](live-trading-flow.md) | Live trading: thread-per-portfolio, circuit breaker, atomic state fetch |
| [portfolio-strategy-flow.md](portfolio-strategy-flow.md) | `BasePortfolio`, indicators, `StrategyContext`, signal-to-trade path |
| [data-pipeline.md](data-pipeline.md) | FMP client, backfill CLI, parquet cache, ticker refresh, real-time ingestor |
| [capital-management.md](capital-management.md) | Master portfolio, daily rebalancing, internal transfers |
| [database-schema.md](database-schema.md) | Tables, ER, atomic state query, connection pool |

## Rendering

Mermaid blocks render automatically in:
- GitHub (web UI, PR diffs)
- VS Code with the Mermaid extension
- [mermaid.live](https://mermaid.live)
- Any Markdown viewer with Mermaid support

## Updating Diagrams

When code structure changes, update both the Mermaid block and any prose tables that reference component names so the two stay in sync. Keep diagrams *behavioral* (what happens) rather than *exhaustive* (every helper) — readers should be able to predict actual control flow from the diagram alone.
