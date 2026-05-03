# Backtest Flow

End-to-end flow of `python -m src.main_backtest`, from process launch through report generation. The entry point fans portfolios out across worker processes, and each worker drives one of two execution modes.

## Top-level Driver

```mermaid
flowchart TD
    START([python -m src.main_backtest]) --> INIT["init_backtest()<br/>resolve dates, capital,<br/>slippage, fast_config"]
    INIT --> RESOLVE_BATCHES["_resolve_num_batches()<br/>min(num_portfolios, cpu_count)"]
    RESOLVE_BATCHES --> PARTITION["_partition_portfolios_evenly()<br/>even per-batch split"]
    PARTITION --> POOL["ProcessPoolExecutor<br/>max_workers = non-empty batches"]

    POOL --> W1["Worker 1<br/>run_backtest(batch_1)"]
    POOL --> W2["Worker 2<br/>run_backtest(batch_2)"]
    POOL --> WN["Worker N<br/>run_backtest(batch_N)"]

    W1 --> JOIN["as_completed()<br/>collect trade logs"]
    W2 --> JOIN
    WN --> JOIN

    JOIN --> DONE[("===== DONE =====")]

    classDef driver fill:#e3f2fd,stroke:#1565c0
    classDef worker fill:#fff3e0,stroke:#e65100
    class START,INIT,RESOLVE_BATCHES,PARTITION,POOL,JOIN,DONE driver
    class W1,W2,WN worker
```

Each worker process pins its `tqdm` row via `TQDM_POSITION` so progress bars don't collide on the terminal. A worker constructs its own `MQSDBConnector` and `BacktestEngine` — connections and engines are not shared across processes.

## Engine Dispatch (per worker)

```mermaid
flowchart TD
    BT_RUN["BacktestEngine.run()"] --> LOOP["For each portfolio class"]
    LOOP --> LOAD["Load config.json<br/>(by portfolio module path)"]
    LOAD --> MODE{"backtest_mode == 'fast'?"}

    MODE -->|"yes"| STUB["_build_fast_portfolio_stub<br/>(skips indicator warmup)"]
    STUB --> FAST["_run_fast_vectorized()"]

    MODE -->|"no (event)"| INST["Instantiate portfolio<br/>(warms up indicators)"]
    INST --> RUNNER["BacktestRunner(portfolio, ...)"]
    RUNNER --> EVENT["runner.run()"]

    classDef engine fill:#fff3e0,stroke:#e65100
    classDef event fill:#e8f5e9,stroke:#2e7d32
    classDef fast fill:#fce4ec,stroke:#c2185b
    class BT_RUN,LOOP,LOAD,MODE engine
    class INST,RUNNER,EVENT event
    class STUB,FAST fast
```

Mode is selected by `BACKTEST_MODE` in `main_backtest.py`. `"event"` is the default and full-fidelity simulation; `"fast"` swaps in a vectorized path with optional Monte Carlo overlay.

## Event Mode (`BacktestRunner`)

```mermaid
flowchart TD
    RUN["runner.run()"] --> PREP["_prepare_data()<br/>fetch_historical_data + sort"]
    PREP --> ADJ["Adjust start_date<br/>back by lookback_days<br/>(query window only)"]
    ADJ --> SETUP_EXEC["_setup_executor()<br/>build BacktestExecutor"]
    SETUP_EXEC --> LOOP["_run_event_loop()"]

    LOOP --> GROUP["Group bars by timestamp"]
    GROUP --> FILTER["Filter timestamps >=<br/>backtest_loop_start_date"]
    FILTER --> ITER["For each timestamp"]

    ITER --> POLL{"poll_interval<br/>elapsed?"}
    POLL -->|"no"| ITER
    POLL -->|"yes"| UPDATE["executor.update_price(t)<br/>for every ticker in chunk"]
    UPDATE --> SLICE["historical_slice =<br/>main_data_df[start_idx:end+1]<br/>(lookback window)"]
    SLICE --> SIGNAL["portfolio.generate_signals_and_trade(<br/>data_dict, current_time)"]
    SIGNAL --> ON_DATA["BasePortfolio updates indicators<br/>and calls strategy.OnData(context)"]
    ON_DATA --> RECORD["Append per-ticker value<br/>+ portfolio_value to perf_records"]
    RECORD --> ITER

    ITER --> CALC["_calculate_results()<br/>build perf_df, pnl_pct"]
    CALC --> REPORT["generate_backtest_report()"]
    REPORT --> RESTORE["_restore_executor()<br/>(undoes monkey-patch)"]

    classDef runner fill:#e8f5e9,stroke:#2e7d32
    class RUN,PREP,ADJ,SETUP_EXEC,LOOP,GROUP,FILTER,ITER,POLL,UPDATE,SLICE,SIGNAL,ON_DATA,RECORD,CALC,REPORT,RESTORE runner
```

Notable invariants:
- The lookback adjustment only widens the *query* window. The simulation loop still starts at the requested `start_date`.
- `BacktestExecutor` is monkey-patched onto the portfolio (replacing whatever live executor was passed) and restored in `finally`.
- Strategies see `data_dict["MARKET_DATA"]` as a sliced DataFrame containing only the lookback window up to and including the current bar.

## Fast Mode (`VectorBacktester`)

```mermaid
flowchart TD
    FAST["_run_fast_vectorized()"] --> ADAPTER["get_vector_adapter_for_portfolio()"]
    ADAPTER --> NO_ADAPT{"adapter found?"}
    NO_ADAPT -->|"no"| SKIP["log + skip"]
    NO_ADAPT -->|"yes"| FETCH["_fetch_fast_daily_close_data()<br/>(daily close window<br/>= years_back + range)"]

    FETCH --> PIVOT["Pivot to close_matrix<br/>(date × ticker)"]
    PIVOT --> SIGNALS["adapter(close_matrix)<br/>→ target_weights"]
    SIGNALS --> RETURNS["Compute returns,<br/>turnover, transaction costs"]
    RETURNS --> SLICE["Slice to backtest window"]
    SLICE --> VECT["VectorBacktester.run_from_returns()"]

    VECT --> CSV1["performance_timeseries_absolute.csv"]
    VECT --> CSV2["benchmark_buy_and_hold_performance.csv"]
    VECT --> CSV3["summary_metrics.csv"]

    SLICE --> SEASONAL["run_and_save_same_window_previous_years<br/>(seasonal overlay)"]

    SLICE --> MC{"fast_config.mc_enabled?"}
    MC -->|"yes"| MC_RUN["VectorBacktester.monte_carlo()<br/>n_sims, method, block_size"]
    MC_RUN --> CSV4["monte_carlo_summary_metrics.csv"]
    MC_RUN --> CSV5["monte_carlo_percentile_paths.csv"]
    MC -->|"no"| RISK
    CSV4 --> RISK
    CSV5 --> RISK

    RISK["Portfolio risk analytics:<br/>correlation, individual vols,<br/>rolling risk"] --> CSV6["portfolio_risk_components.csv"]
    RISK --> CSV7["annualized_correlation_matrix.csv"]
    RISK --> CSV8["rolling_portfolio_risk.csv"]
    RISK --> CSV9["portfolio_composition_daily.csv"]

    classDef fast fill:#fce4ec,stroke:#c2185b
    classDef out fill:#e0f2f1,stroke:#00695c
    class FAST,ADAPTER,NO_ADAPT,SKIP,FETCH,PIVOT,SIGNALS,RETURNS,SLICE,VECT,SEASONAL,MC,MC_RUN,RISK fast
    class CSV1,CSV2,CSV3,CSV4,CSV5,CSV6,CSV7,CSV8,CSV9 out
```

Fast mode bypasses indicator warmup and the event loop entirely. It instantiates a lightweight portfolio stub via `_build_fast_portfolio_stub()` (no `OnData` execution), pulls daily closes for an extended window, and lets the registered vector adapter produce target weights directly. Indicators in adapter modules (e.g. `_compute_rsi`, `_compute_rmi` in `vector_strategy_adapters.py`) are vectorized re-implementations — they do not import the event-mode indicator classes.

## Configuration Reference

```python
# src/main_backtest.py
START_DATE = "2025-01-01"
END_DATE = "2025-01-05"
INITIAL_CAPITAL = 1_000_000.0
SLIPPAGE = 0.000001              # 0.1 bp
BACKTEST_MODE = ""               # "" → defaults to "event" with FutureWarning; "fast" enables vectorized
BACKTEST_NUM_BATCHES = None      # None → min(num_portfolios, cpu_count)

FAST_MODE_CONFIG = {
    "years_back": 3,
    "benchmark_label": "SPY",
    "quick": True,
    "mc_enabled": True,
    "mc_n_sims": 10000,
    "mc_method": "bootstrap",
    "mc_block_size": 5,
    "mc_seed": None,
    "mc_plot_percentiles": [10, 50, 90],
}
```

| Knob | Purpose |
|------|---------|
| `START_DATE` / `END_DATE` | Backtest window (NY-zoned dates) |
| `INITIAL_CAPITAL` | Per-portfolio starting capital |
| `SLIPPAGE` | Per-trade slippage applied by `BacktestExecutor` and fast-mode turnover cost |
| `BACKTEST_MODE` | `"event"` for full simulation, `"fast"` for vectorized + MC |
| `BACKTEST_NUM_BATCHES` | Override worker count; `None` auto-selects |
| `fast_config.mc_*` | Monte Carlo controls (only used in fast mode) |
| `years_back` | How far back fast mode pulls daily history before the start date |

## Output Files

Each backtest run writes to a timestamped directory under `src/backtest/data/<run_ts>_backtest_<portfolio_id>/` (or the directory pointed to by `BACKTEST_OUTPUT_DIR`).

### Event mode

| File | Description |
|------|-------------|
| `trade_log.csv` | Every executed trade (timestamp, side, qty, prices, slippage) |
| `performance_timeseries_absolute.csv` | Portfolio value over time |
| `performance_timeseries_percentage.csv` | Returns as percentages |
| `performance_timeseries_minute_by_minute.csv` | High-frequency series |
| `summary_metrics.csv` | Final value, max drawdown, Sharpe, etc. |
| `benchmark_buy_and_hold_performance.csv` | Buy-and-hold reference |
| `30D_Rolling.csv` / `90D_Rolling.csv` / `180D_Rolling.csv` | Rolling stats |
| `monthly_returns.csv` | Resampled monthly returns |
| `portfolio_risk_components.csv` | Per-asset volatility |
| `annualized_correlation_matrix.csv` | Asset correlation matrix |
| `rolling_portfolio_risk.csv` | Rolling portfolio volatility |

### Fast mode

| File | Description |
|------|-------------|
| `performance_timeseries_absolute.csv` | Strategy P&L over the window |
| `benchmark_buy_and_hold_performance.csv` | Equal-weighted benchmark of the same tickers |
| `summary_metrics.csv` | Vectorized run metrics |
| `monte_carlo_summary_metrics.csv` | Aggregate stats across simulated paths (when `mc_enabled`) |
| `monte_carlo_percentile_paths.csv` | Per-percentile cumulative-return paths |
| `portfolio_risk_components.csv` | Final-weights × annualized vol |
| `annualized_correlation_matrix.csv` | Returns correlation across portfolio tickers |
| `rolling_portfolio_risk.csv` | Rolling weighted volatility |
| `portfolio_composition_daily.csv` | Daily allocation × portfolio value (approximation) |
| Seasonal overlay files | Same-window comparison for previous N years (`years_back`) |

## Adding a New Strategy to the Backtest

1. Create `src/portfolios/portfolio_<n>/strategy.py` with a `BasePortfolio` subclass.
2. Add `src/portfolios/portfolio_<n>/config.json` with at least `PORTFOLIO_ID`, `TICKERS`, `INTERVAL`, `LOOKBACK_DAYS`.
3. Import and register the class in `AVAILABLE_PORTFOLIO_CLASSES` (and optionally `DEFAULT_PORTFOLIO_CLASSES`) in `src/main_backtest.py`.
4. (Optional) Register a fast-mode adapter in `src/backtest/vector_strategy_adapters.py` if you want the strategy to participate in fast mode. Without an adapter, fast mode logs a warning and skips that portfolio.
