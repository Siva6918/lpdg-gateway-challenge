"""
Ranking Strategy — Abstract Base Class
=======================================

Why this exists:
    The API must NOT be tightly coupled to any specific ranking algorithm.
    By depending on this abstract interface, the API routes stay stable
    even if we swap the algorithm later (e.g., from 3-sigma to ML-based).

    This is the classic "Strategy" design pattern.

How to add a new ranking algorithm:
    1. Create a new file in src/ranking/ (e.g., `ml_ranker.py`)
    2. Define a class that inherits from RankingStrategy
    3. Implement the `rank_week` method
    4. Register it in src/ranking/registry.py
    DONE — you never need to edit src/api/routes.py

Data contract:
    `rank_week` receives a pandas DataFrame with at minimum:
      - gateway_id (str)
      - ts_utc (str, ISO 8601, hourly rows)
      - offline_duration_sec (float)
      - disconnection_cnt (float)
      - reboot_cnt (float)

    It must return a DataFrame with:
      - gateway_id (str)
      - rank (int, 1-indexed)
      - score (float)
      - reason (str, max 300 chars per validate_submission.py)
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

import pandas as pd


class RankingStrategy(ABC):
    """Abstract interface for all gateway ranking algorithms.

    Any concrete ranker must inherit from this class and implement
    the `rank_week` method. The rest of the application only knows
    about this interface — never the concrete class directly.
    """

    @abstractmethod
    def rank_week(self, frame: pd.DataFrame, monday: dt.date) -> pd.DataFrame:
        """Rank gateways for the week starting on `monday`.

        Args:
            frame:  Full telemetry DataFrame (all dates, all gateways).
                    The implementation is responsible for filtering to
                    the relevant window.
            monday: The Monday that starts the scored week (UTC date).

        Returns:
            A DataFrame with exactly these columns (in any order):
              - gateway_id  (str)
              - rank        (int, 1 = highest priority)
              - score       (float, higher = more anomalous)
              - reason      (str, human-readable, max 300 characters)

            Rows are ordered by rank ascending (rank 1 first).
            The caller (RankingService) decides how many rows to use.

        Raises:
            ValueError: if `monday` has no usable data in `frame`.
        """
        ...  # pragma: no cover — abstract, never called directly
