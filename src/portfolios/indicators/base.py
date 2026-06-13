# src/portfolios/indicators/base.py

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

class Indicator(ABC):
    """
    Abstract base class for all stateful technical indicators.
    """
    def __init__(self, ticker: str, **kwargs: Any):
        self.ticker: str = ticker
        self.kwargs: Any = kwargs  # Store all parameters
        self._is_ready: bool = False
        self._current_value = None
        self.period = ""

    @property
    def IsReady(self) -> bool:
        """Returns True if the indicator has enough data to produce a value."""
        return self._is_ready

    @property
    def Current(self):
        """Returns the latest value of the indicator."""
        return self._current_value

    @abstractmethod
    def Update(self, timestamp: datetime, data_row: Any) -> None:
        """
        Updates the indicator with a new data row (dict or pd.Series).
        """
        raise NotImplementedError("Each indicator must implement the 'Update' method.")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.ticker}, {self.period}) -> Value: {self.Current if self.IsReady else 'NotReady'}"