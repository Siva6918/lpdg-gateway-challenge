"""
Ranking Service — Business Logic Layer
========================================

The service layer orchestrates data loading, ranking strategies, and
detailed gateway diagnostics.

Key design decisions:
  1. Separation of concerns: HTTP concerns live in src/api/routes.py,
     ranking algorithms live in src/ranking/, and data orchestration lives here.
  2. Testability: RankingService accepts an optional in-memory DataFrame
     so unit tests run in milliseconds without reading 104 MB of Parquet.
  3. Caching: In production, the loaded DataFrame is cached in memory.
     `reload_data()` refreshes the cache when new telemetry arrives.
"""

from __future__ import annotations

import datetime as dt
import pathlib
from typing import Any

import numpy as np
import pandas as pd

from src.config import DATA_DIR, TELEMETRY_DIR
from src.ranking.base import RankingStrategy
from src.ranking.registry import get_ranker
from src.ranking.three_sigma import METRICS, BASELINE_DAYS, RECENT_DAYS


class ServiceError(Exception):
    """Base exception for service layer errors."""


class DataNotFoundError(ServiceError):
    """Raised when telemetry data is missing or cannot be loaded."""


class GatewayNotFoundError(ServiceError):
    """Raised when a gateway_id does not exist in the dataset."""


class InvalidWeekError(ServiceError):
    """Raised when the requested week is invalid or outside the data range."""


class RankingService:
    """Service class managing gateway rankings and explanations."""

    def __init__(
        self,
        data_dir: pathlib.Path | None = None,
        telemetry_frame: pd.DataFrame | None = None,
        default_strategy: str = "three_sigma",
    ) -> None:
        """Initialize the service.

        Args:
            data_dir: Path to directory containing 'telemetry' parquet data.
            telemetry_frame: Optional in-memory DataFrame (used for unit tests).
            default_strategy: Strategy name to use if none is specified.
        """
        self.data_dir = data_dir or DATA_DIR
        self._telemetry_dir = self.data_dir / "telemetry" if data_dir else TELEMETRY_DIR
        self._frame: pd.DataFrame | None = telemetry_frame
        self.default_strategy = default_strategy

    def get_data(self) -> pd.DataFrame:
        """Return the loaded telemetry DataFrame, loading it if not already cached."""
        if self._frame is not None:
            return self._frame

        if not self._telemetry_dir.exists():
            raise DataNotFoundError(
                f"Telemetry directory not found at: {self._telemetry_dir}. "
                "Ensure data is placed in the configured DATA_DIR or set the DATA_DIR env var."
            )

        try:
            # We only read the columns needed for ranking to conserve memory
            cols = ["gateway_id", "ts_utc", *METRICS]
            frame = pd.read_parquet(self._telemetry_dir, columns=cols)
            frame["ts"] = pd.to_datetime(frame["ts_utc"], utc=True)
            self._frame = frame
            return self._frame
        except Exception as exc:
            raise DataNotFoundError(f"Failed to read parquet telemetry data: {exc}") from exc

    def reload_data(self) -> dict[str, Any]:
        """Invalidate the cache and reload data from disk (used by POST /rankings/run).

        Returns:
            Dictionary with reload statistics.
        """
        self._frame = None
        frame = self.get_data()
        return {
            "status": "success",
            "rows_loaded": len(frame),
            "gateways_count": int(frame["gateway_id"].nunique()),
            "min_timestamp": frame["ts"].min().isoformat() if not frame.empty else None,
            "max_timestamp": frame["ts"].max().isoformat() if not frame.empty else None,
        }

    def get_available_weeks(self) -> list[str]:
        """Return the list of standard scored Mondays (ISO date strings)."""
        base = dt.date(2026, 2, 2)
        return [(base + dt.timedelta(days=7 * i)).isoformat() for i in range(8)]

    def get_rankings(
        self,
        week: dt.date | str,
        strategy_name: str | None = None,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Get ranked gateways for a given week Monday.

        Args:
            week: Monday date (dt.date or 'YYYY-MM-DD').
            strategy_name: Name of ranking strategy (default: self.default_strategy).
            limit: Number of top gateways to return (default: 15).

        Returns:
            List of dicts with keys: gateway_id, rank, score, reason.
        """
        monday = self._parse_week_date(week)
        frame = self.get_data()

        strategy: RankingStrategy = get_ranker(strategy_name or self.default_strategy)

        try:
            ranked_df = strategy.rank_week(frame, monday)
        except ValueError as exc:
            raise InvalidWeekError(str(exc)) from exc

        top_df = ranked_df.head(limit)
        return top_df.to_dict(orient="records")

    def get_gateway_explanation(
        self,
        gateway_id: str,
        week: dt.date | str | None = None,
        strategy_name: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve detailed diagnostic metrics and anomaly status for a gateway.

        Args:
            gateway_id: The 12-char hex gateway identifier.
            week: Monday date for the evaluation window (defaults to 2026-02-02).
            strategy_name: Ranking strategy name.

        Returns:
            Dictionary with comprehensive gateway diagnostics.
        """
        frame = self.get_data()

        # Check if gateway exists anywhere in data
        gw_rows = frame[frame["gateway_id"] == gateway_id]
        if gw_rows.empty:
            raise GatewayNotFoundError(f"Gateway '{gateway_id}' not found in telemetry data.")

        monday = self._parse_week_date(week) if week else dt.date(2026, 2, 2)
        end = pd.Timestamp(monday, tz="UTC")
        baseline_start = end - dt.timedelta(days=BASELINE_DAYS)
        recent_start = end - dt.timedelta(days=RECENT_DAYS)

        # Baseline window rows
        base_window = gw_rows[(gw_rows["ts"] >= baseline_start) & (gw_rows["ts"] < end)]
        if base_window.empty:
            raise InvalidWeekError(
                f"No telemetry records for gateway '{gateway_id}' in 28-day window before {monday}."
            )

        # Recent 7-day rows
        recent_window = base_window[base_window["ts"] >= recent_start]

        # Compute baseline mean & std
        baseline_stats = {}
        for metric in METRICS:
            mean_val = float(base_window[metric].mean())
            std_val = float(base_window[metric].std(ddof=1)) if len(base_window) > 1 else 0.0
            baseline_stats[metric] = {
                "mean": round(mean_val, 3),
                "std": round(std_val, 3) if not np.isnan(std_val) else 0.0,
            }

        # Compute recent 7-day metrics
        recent_metrics = {}
        breach_counts = {}
        for metric in METRICS:
            total_val = float(recent_window[metric].sum()) if not recent_window.empty else 0.0
            max_val = float(recent_window[metric].max()) if not recent_window.empty else 0.0
            recent_metrics[metric] = {
                "sum_7d": round(total_val, 2),
                "max_1h": round(max_val, 2),
            }
            # Calculate breach hours
            mean_val = baseline_stats[metric]["mean"]
            std_val = baseline_stats[metric]["std"]
            if std_val > 0:
                thresh = mean_val + 3.0 * std_val
                breaches = int((recent_window[metric] > thresh).sum())
            else:
                breaches = 0
            breach_counts[metric] = breaches

        total_breach_hours = sum(breach_counts.values())

        # Determine rank among all gateways for that week
        strategy = get_ranker(strategy_name or self.default_strategy)
        ranked_df = strategy.rank_week(frame, monday)
        gw_rank_match = ranked_df[ranked_df["gateway_id"] == gateway_id]
        if not gw_rank_match.empty:
            rank_val = int(gw_rank_match.iloc[0]["rank"])
            score_val = float(gw_rank_match.iloc[0]["score"])
            reason_str = str(gw_rank_match.iloc[0]["reason"])
        else:
            rank_val = None
            score_val = float(total_breach_hours)
            reason_str = f"{total_breach_hours} flagged breach hours detected"

        return {
            "gateway_id": gateway_id,
            "week_start": monday.isoformat(),
            "rank": rank_val,
            "is_top_15": (rank_val is not None and rank_val <= 15),
            "score": score_val,
            "reason": reason_str,
            "baseline_stats_28d": baseline_stats,
            "recent_metrics_7d": recent_metrics,
            "breach_hours_by_metric": breach_counts,
        }

    def _parse_week_date(self, week: dt.date | str | None) -> dt.date:
        """Parse and validate that the week is a date string or date object."""
        if week is None:
            return dt.date(2026, 2, 2)

        if isinstance(week, dt.date):
            return week

        try:
            parsed = dt.date.fromisoformat(str(week).strip())
            return parsed
        except ValueError as exc:
            raise InvalidWeekError(
                f"Invalid date format '{week}'. Expected YYYY-MM-DD (e.g. 2026-02-02)."
            ) from exc
