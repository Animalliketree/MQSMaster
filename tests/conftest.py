# tests/conftest.py

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
    try:
        db = MQSDBConnector()
        yield db
    except Exception as e:
        pytest.fail(f"❌ Failed to initialize the MQSDBConnector: {e}")


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
    required = [
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT"),
        os.getenv("DB_NAME"),
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
    ]
    if not all(required):
        pytest.skip("Database credentials not configured")
