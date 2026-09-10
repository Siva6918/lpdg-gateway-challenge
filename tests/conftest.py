"""
tests/conftest.py — Shared fixtures for all tests.

IMPORTANT: Tests must NOT require the real 104 MB dataset.
We create small, deterministic DataFrames here that:
  - Match the shape of the real telemetry data
  - Contain predictable anomalies so we can assert exact results
  - Are fast to create (no file I/O)

Gateway IDs used in fixtures:
  - AABBCCDDEEFF  → consistently anomalous gateway (many flagged hours)
  - 112233445566  → normal gateway (no anomalies)
  - DEADBEEF0001  → gateway with data only in old window (outside recent 7d)

Scored week used in tests: monday = 2026-02-02
Baseline window: 28 days before 2026-02-02 = 2026-01-05 to 2026-02-01
Recent window:    7 days before 2026-02-02 = 2026-01-26 to 2026-02-01
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Constants matching the baseline
# ---------------------------------------------------------------------------
MONDAY = dt.date(2026, 2, 2)      # first scored week
GATEWAY_ANOMALOUS = "AABBCCDDEEFF"
GATEWAY_NORMAL = "112233445566"
GATEWAY_NO_RECENT = "DEADBEEF0001"


def _make_hourly_rows(
    gateway_id: str,
    start: pd.Timestamp,
    hours: int,
    offline_duration_sec: float = 0.0,
    disconnection_cnt: float = 0.0,
    reboot_cnt: float = 0.0,
) -> pd.DataFrame:
    """Helper: create `hours` rows for one gateway starting at `start`."""
    ts_list = [start + dt.timedelta(hours=h) for h in range(hours)]
    return pd.DataFrame(
        {
            "gateway_id": gateway_id,
            "ts_utc": [t.isoformat().replace("+00:00", "Z") for t in ts_list],
            "offline_duration_sec": offline_duration_sec,
            "disconnection_cnt": disconnection_cnt,
            "reboot_cnt": reboot_cnt,
        }
    )


@pytest.fixture()
def minimal_frame() -> pd.DataFrame:
    """A minimal telemetry DataFrame with two gateways.

    GATEWAY_ANOMALOUS: 27 days of small-variance baseline (alternating 0/2),
                       then 1 day (24 hours) of severe disconnection spike (100.0).
                       In a 28-day window (672 hours), a spike occurring across all
                       7 days (168 hours = 25% of data) cannot exceed 3 sigma due to
                       mathematical bounds (max z-score for 25% proportion is sqrt(3) ≈ 1.73).
                       A 24-hour burst (~3.5% of data) cleanly exceeds 3-sigma.
    GATEWAY_NORMAL:    28 days of constant 0.0 values (score=0).

    Expected result for MONDAY=2026-02-02:
      - GATEWAY_ANOMALOUS  → rank 1 (24 flagged hours)
      - GATEWAY_NORMAL     → rank 2 (0 flagged hours, score=0)
    """
    baseline_start = pd.Timestamp("2026-01-05", tz="UTC")

    # ANOMALOUS: 27 days alternating 0 and 2, plus 24 hours of extreme spike (100.0)
    anom_rows = []
    for h in range(27 * 24):
        ts = baseline_start + dt.timedelta(hours=h)
        anom_rows.append({
            "gateway_id": GATEWAY_ANOMALOUS,
            "ts_utc": ts.isoformat().replace("+00:00", "Z"),
            "offline_duration_sec": 0.0,
            "disconnection_cnt": float(h % 2) * 2,
            "reboot_cnt": 0.0,
        })
    for h in range(24):
        ts = baseline_start + dt.timedelta(hours=27 * 24 + h)
        anom_rows.append({
            "gateway_id": GATEWAY_ANOMALOUS,
            "ts_utc": ts.isoformat().replace("+00:00", "Z"),
            "offline_duration_sec": 0.0,
            "disconnection_cnt": 100.0,
            "reboot_cnt": 0.0,
        })
    anomalous_frame = pd.DataFrame(anom_rows)

    # NORMAL: 28 days of all zeros (score = 0)
    normal_rows = _make_hourly_rows(
        GATEWAY_NORMAL,
        start=baseline_start,
        hours=28 * 24,
        disconnection_cnt=0.0,
    )

    frame = pd.concat([anomalous_frame, normal_rows], ignore_index=True)
    frame["ts"] = pd.to_datetime(frame["ts_utc"], utc=True)
    return frame


@pytest.fixture()
def frame_with_15_gateways(minimal_frame: pd.DataFrame) -> pd.DataFrame:
    """Extend minimal_frame to have 15 gateways (needed for full week ranking).

    Gateways 3-15 are normal (no anomalies). Only GATEWAY_ANOMALOUS has flags.
    """
    baseline_start = pd.Timestamp("2026-01-05", tz="UTC")
    extra_frames = []
    for i in range(3, 16):
        gw_id = f"FFFFFF{i:06d}"
        rows = _make_hourly_rows(
            gw_id,
            start=baseline_start,
            hours=28 * 24,
            disconnection_cnt=float(i),  # non-zero but consistent → std=0 if constant
        )
        extra_frames.append(rows)

    extra = pd.concat(extra_frames, ignore_index=True)
    extra["ts"] = pd.to_datetime(extra["ts_utc"], utc=True)
    return pd.concat([minimal_frame, extra], ignore_index=True)
