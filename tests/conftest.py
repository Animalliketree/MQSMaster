# tests/conftest.py

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

# This path manipulation allows the import below to work.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Use the correct, full import path for your connector.
from src.common.database.MQSDBConnector import MQSDBConnector


@pytest.fixture(scope="module")
def db_connection():
    """
    A pytest fixture that creates and yields a database connector instance.
    """
    connector = None
    try:
        connector = MQSDBConnector()
        yield connector
    except Exception as e:
        pytest.fail(f"❌ Failed to initialize the MQSDBConnector: {e}")
    finally:
        if connector is None:
            return

        cleanup_method_names = (
            "close_all_connections",
            "close",
            "disconnect",
            "shutdown",
            "cleanup",
        )

        for method_name in cleanup_method_names:
            cleanup_method = getattr(connector, method_name, None)
            if not callable(cleanup_method):
                continue

            try:
                cleanup_method()
                break
            except Exception as cleanup_error:
                logging.exception(
                    "Error while calling %s on MQSDBConnector during teardown: %s",
                    method_name,
                    cleanup_error,
                )


@pytest.fixture
def smoke_window():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=21)
    return start, end


@pytest.fixture
def deep_window():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=90)
    return start, end


@pytest.fixture
def require_fmp_env():
    if not os.getenv("FMP_API_KEY"):
        pytest.skip("FMP_API_KEY not set")


@pytest.fixture
def require_db_env():
    required_names = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]
    missing_names = [name for name in required_names if not os.getenv(name)]
    if missing_names:
        pytest.skip(
            f"Database credentials not configured: missing {', '.join(missing_names)}"
        )
