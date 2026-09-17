"""
tests/test_determinism.py — Verification of deterministic rankings, tie-breaking, and cache refresh.

Requirements verified:
  1. The same input produces identical rankings across repeated executions.
  2. Input row shuffling does not alter the output ranking (order-invariant).
  3. Tied anomaly scores are resolved deterministically via secondary sort (gateway_id ascending).
  4. Cache reload (POST /rankings/run) on unchanged data yields 100% identical rankings.
  5. Gateway diagnostic explanations are deterministic across repeated queries.
"""

from __future__ import annotations

import datetime as dt
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.routes import get_ranking_service
from src.ranking.three_sigma import ThreeSigmaRanker
from src.services.ranking_service import RankingService
from tests.conftest import MONDAY, GATEWAY_ANOMALOUS, GATEWAY_NORMAL


# ---------------------------------------------------------------------------
# Helpers for deterministic tie fixtures
# ---------------------------------------------------------------------------

def _make_spike_gateway_rows(
    gateway_id: str,
    baseline_start: pd.Timestamp,
    spike_val: float = 100.0,
) -> list[dict]:
    """Create 28 days of hourly records: 27 days alternating 0/2, 24h spike."""
    rows = []
    for h in range(27 * 24):
        ts = baseline_start + dt.timedelta(hours=h)
        rows.append({
            "gateway_id": gateway_id,
            "ts_utc": ts.isoformat().replace("+00:00", "Z"),
            "offline_duration_sec": 0.0,
            "disconnection_cnt": float(h % 2) * 2.0,
            "reboot_cnt": 0.0,
        })
    for h in range(24):
        ts = baseline_start + dt.timedelta(hours=27 * 24 + h)
        rows.append({
            "gateway_id": gateway_id,
            "ts_utc": ts.isoformat().replace("+00:00", "Z"),
            "offline_duration_sec": 0.0,
            "disconnection_cnt": spike_val,
            "reboot_cnt": 0.0,
        })
    return rows


def _make_zero_gateway_rows(
    gateway_id: str,
    baseline_start: pd.Timestamp,
) -> list[dict]:
    """Create 28 days of constant zero records."""
    rows = []
    for h in range(28 * 24):
        ts = baseline_start + dt.timedelta(hours=h)
        rows.append({
            "gateway_id": gateway_id,
            "ts_utc": ts.isoformat().replace("+00:00", "Z"),
            "offline_duration_sec": 0.0,
            "disconnection_cnt": 0.0,
            "reboot_cnt": 0.0,
        })
    return rows


@pytest.fixture()
def tied_gateways_frame() -> pd.DataFrame:
    """Fixture containing two pairs of tied gateways:

    Pair 1 (both have 24 flagged hours):
      - 'BBBB00000002'
      - 'AAAA00000001'

    Pair 2 (both have 0 flagged hours):
      - 'DDDD00000004'
      - 'CCCC00000003'
    """
    baseline_start = pd.Timestamp("2026-01-05", tz="UTC")

    # Deliberately insert 'BBBB' before 'AAAA' to prove sorting doesn't depend on insertion order
    rows = (
        _make_spike_gateway_rows("BBBB00000002", baseline_start)
        + _make_spike_gateway_rows("AAAA00000001", baseline_start)
        + _make_zero_gateway_rows("DDDD00000004", baseline_start)
        + _make_zero_gateway_rows("CCCC00000003", baseline_start)
    )
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestRankingDeterminism:
    """Verify that repeated runs and row permutations produce identical rankings."""

    def test_repeated_service_rankings_are_strictly_identical(
        self, frame_with_15_gateways: pd.DataFrame
    ):
        """Repeated calls to get_rankings on identical data must yield identical results."""
        service = RankingService(telemetry_frame=frame_with_15_gateways)
        run_1 = service.get_rankings(week=MONDAY, limit=15)
        run_2 = service.get_rankings(week=MONDAY, limit=15)
        run_3 = service.get_rankings(week=MONDAY, limit=15)

        assert run_1 == run_2
        assert run_2 == run_3

    def test_ranker_is_order_invariant(self, tied_gateways_frame: pd.DataFrame):
        """Shuffling input DataFrame rows must produce 100% identical rankings."""
        ranker = ThreeSigmaRanker()
        res_original = ranker.rank_week(tied_gateways_frame, MONDAY)

        # Shuffle rows completely
        shuffled_frame = tied_gateways_frame.sample(frac=1.0, random_state=42).reset_index(drop=True)
        res_shuffled = ranker.rank_week(shuffled_frame, MONDAY)

        pd.testing.assert_frame_equal(res_original, res_shuffled)

    def test_deterministic_tie_breaking_order(self, tied_gateways_frame: pd.DataFrame):
        """When two gateways have equal scores, secondary sort by gateway_id ascending must prevail."""
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(tied_gateways_frame, MONDAY)

        # Ranks 1 and 2 are tied at 24 score
        assert result.iloc[0]["score"] == result.iloc[1]["score"]
        assert result.iloc[0]["gateway_id"] == "AAAA00000001"
        assert result.iloc[1]["gateway_id"] == "BBBB00000002"

        # Ranks 3 and 4 are tied at 0 score
        assert result.iloc[2]["score"] == result.iloc[3]["score"] == 0.0
        assert result.iloc[2]["gateway_id"] == "CCCC00000003"
        assert result.iloc[3]["gateway_id"] == "DDDD00000004"


class TestCacheReloadDeterminism:
    """Verify cache reload behavior via the API."""

    def test_run_reload_maintains_deterministic_rankings(
        self, frame_with_15_gateways: pd.DataFrame
    ):
        """Calling POST /rankings/run on unchanged data produces identical GET /rankings."""
        service = RankingService(telemetry_frame=frame_with_15_gateways)
        app.dependency_overrides[get_ranking_service] = lambda: service
        client = TestClient(app)

        try:
            # 1. Initial GET
            resp_before = client.get("/rankings?week=2026-02-02&limit=15")
            assert resp_before.status_code == 200
            data_before = resp_before.json()

            # 2. Pipeline rerun (cache reload)
            run_resp = client.post("/rankings/run")
            assert run_resp.status_code == 200
            assert run_resp.json()["status"] == "success"

            # 3. Subsequent GET
            resp_after = client.get("/rankings?week=2026-02-02&limit=15")
            assert resp_after.status_code == 200
            data_after = resp_after.json()

            # Both outputs must be completely identical
            assert data_before == data_after
        finally:
            app.dependency_overrides.clear()

    def test_gateway_explanation_is_deterministic(
        self, minimal_frame: pd.DataFrame
    ):
        """Repeated calls to get_gateway_explanation must yield identical metrics."""
        service = RankingService(telemetry_frame=minimal_frame)
        diag_1 = service.get_gateway_explanation(GATEWAY_ANOMALOUS, week=MONDAY)
        diag_2 = service.get_gateway_explanation(GATEWAY_ANOMALOUS, week=MONDAY)

        assert diag_1 == diag_2
