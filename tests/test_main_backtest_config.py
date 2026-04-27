import src.main_backtest as main_backtest


class _DummyBacktestEngine:
    def __init__(self, db_connector, backtest_executor=None):
        self.db_connector = db_connector
        self.backtest_executor = backtest_executor
        self.setup_kwargs = None
        self.ran = False
        self.trade_log = [{"status": "ok"}]

    def setup(self, **kwargs):
        self.setup_kwargs = kwargs

    def run(self):
        self.ran = True
        return self.trade_log


def test_init_backtest_uses_passed_portfolios_and_merged_fast_config():
    custom_portfolios = [object]
    (
        portfolio_classes,
        _start_date,
        _end_date,
        _initial_capital,
        _slippage,
        backtest_mode,
        fast_cfg,
    ) = main_backtest.init_backtest(
        portfolio_classes=custom_portfolios,
        backtest_mode="fast",
        fast_years_back=4,
        fast_benchmark_label="QQQ",
        fast_config={"mc_enabled": True, "mc_n_sims": 321},
    )

    assert portfolio_classes == custom_portfolios
    assert backtest_mode == "fast"
    assert fast_cfg["years_back"] == 4
    assert fast_cfg["benchmark_label"] == "QQQ"
    assert fast_cfg["mc_enabled"] is True
    assert fast_cfg["mc_n_sims"] == 321
    assert "mc_method" in fast_cfg


def test_init_backtest_uses_available_defaults_when_none():
    portfolio_classes, *_ = main_backtest.init_backtest(
        portfolio_classes=None,
        backtest_mode="event",
    )

    assert portfolio_classes == list(main_backtest.AVAILABLE_PORTFOLIO_CLASSES[:2])


def test_run_backtest_wires_engine_setup_and_execution(monkeypatch):
    created = []

    def _engine_factory(db_connector, backtest_executor=None):
        engine = _DummyBacktestEngine(db_connector, backtest_executor)
        created.append(engine)
        return engine

    sentinel_db = object()
    monkeypatch.setattr(main_backtest, "MQSDBConnector", lambda: sentinel_db)
    monkeypatch.setattr(main_backtest, "BacktestEngine", _engine_factory)

    trade_log = main_backtest.run_backtest(
        portfolio_classes=[object],
        start_date="2025-01-01",
        end_date="2025-01-05",
        initial_capital=1000000.0,
        slippage=0.0,
        backtest_mode="fast",
        resolved_fast_config={"mc_enabled": True},
    )

    assert len(created) == 1
    engine = created[0]
    assert engine.db_connector is sentinel_db
    assert engine.ran is True
    assert trade_log == engine.trade_log
    assert engine.setup_kwargs is not None
    assert engine.setup_kwargs["portfolio_classes"] == [object]
    assert engine.setup_kwargs["start_date"] == "2025-01-01"
    assert engine.setup_kwargs["end_date"] == "2025-01-05"
    assert engine.setup_kwargs["initial_capital"] == 1000000.0
    assert engine.setup_kwargs["slippage"] == 0.0
    assert engine.setup_kwargs["backtest_mode"] == "fast"
    assert engine.setup_kwargs["fast_config"] == {"mc_enabled": True}
