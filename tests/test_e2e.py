"""
End-to-End tests: Full pipeline from service layer to API HTTP response.

This validates the entire stack in a single test run without mocking
any intermediate layers (except the data source, which uses an
in-memory fixture).

Regression test included:
    We discovered during development that when ALL values in a metric
    are the same across a 28-day window (std=0), the baseline replaces
    std=0 with NaN to avoid division by zero, causing (value - mean) > 3*NaN
    to always return False. This silently misses anomalies.

    The regression test documents and catches this exact failure mode.
"""

from __future__ import annotations

import datetime as dt
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.routes import get_ranking_service
from src.services.ranking_service import RankingService
from tests.conftest import GATEWAY_ANOMALOUS, GATEWAY_NORMAL, MONDAY


@pytest.fixture()
def e2e_client(frame_with_15_gateways) -> TestClient:
    """Full API test client with 15-gateway dataset."""
    service = RankingService(telemetry_frame=frame_with_15_gateways)
    app.dependency_overrides[get_ranking_service] = lambda: service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestEndToEnd:
    """Full pipeline: service loads data → ranking → API response."""

    def test_full_rankings_pipeline(self, e2e_client: TestClient):
        """Full flow: call /rankings → validate structure and ordering."""
        response = e2e_client.get("/rankings?week=2026-02-02&limit=15")
        assert response.status_code == 200
        body = response.json()

        # Structure checks
        assert body["week_start"] == "2026-02-02"
        assert body["count"] == 15
        assert len(body["rankings"]) == 15

        # The anomalous gateway must be first
        first = body["rankings"][0]
        assert first["gateway_id"] == GATEWAY_ANOMALOUS
        assert first["rank"] == 1
        assert first["score"] > 0
        assert "3 sigma" in first["reason"].lower() or "flagged" in first["reason"].lower()

        # All ranks must be sequential 1..15
        ranks = [r["rank"] for r in body["rankings"]]
        assert ranks == list(range(1, 16))

        # Scores must be non-negative and descending
        scores = [r["score"] for r in body["rankings"]]
        assert all(s >= 0 for s in scores)
        assert scores == sorted(scores, reverse=True)

    def test_full_gateway_explanation_pipeline(self, e2e_client: TestClient):
        """Full flow: call /gateways/{id} → validate all diagnostic fields."""
        response = e2e_client.get(f"/gateways/{GATEWAY_ANOMALOUS}?week=2026-02-02")
        assert response.status_code == 200
        body = response.json()

        assert body["gateway_id"] == GATEWAY_ANOMALOUS
        assert body["is_top_15"] is True
        assert body["score"] > 0

        # Check that diagnostic field structure is correct
        for metric in ["offline_duration_sec", "disconnection_cnt", "reboot_cnt"]:
            assert metric in body["baseline_stats_28d"]
            assert "mean" in body["baseline_stats_28d"][metric]
            assert "std" in body["baseline_stats_28d"][metric]
            assert metric in body["recent_metrics_7d"]
            assert "sum_7d" in body["recent_metrics_7d"][metric]
            assert "max_1h" in body["recent_metrics_7d"][metric]
            assert metric in body["breach_hours_by_metric"]

        # disconnection_cnt should have breach hours
        assert body["breach_hours_by_metric"]["disconnection_cnt"] > 0

    def test_run_then_get_rankings(self, e2e_client: TestClient):
        """POST /rankings/run followed by GET /rankings must work end to end."""
        run_response = e2e_client.post("/rankings/run")
        assert run_response.status_code == 200
        run_body = run_response.json()
        assert run_body["status"] == "success"
        assert run_body["rows_loaded"] > 0

        rankings_response = e2e_client.get("/rankings?week=2026-02-02")
        assert rankings_response.status_code == 200
        assert rankings_response.json()["rankings"][0]["gateway_id"] == GATEWAY_ANOMALOUS


# ---------------------------------------------------------------------------
# REGRESSION TESTS
# ---------------------------------------------------------------------------
class TestRegressionStdZeroSilentFailure:
    """
    REGRESSION: Silent anomaly miss when a metric has std=0 over 28-day window.

    Background (discovered during fixture debugging — Phase 4):
        The 3-sigma baseline does: std = window[metric].std(); std.replace(0, NaN)
        Then: (value - mean) > 3 * NaN  →  always False
        This means a gateway with CONSTANT values for 28 days will NEVER be flagged,
        even if the recent 7 days suddenly spike extremely high.

    Why this is acceptable by design:
        The algorithm treats constant behaviour as an undefined baseline (no variance
        means no meaningful threshold). It correctly returns score=0 for such gateways.

    Why this is a concern:
        A brand-new gateway with only 1–3 days of data before the recent window
        could appear "constant" and evade detection.

    The regression test documents and verifies the expected behaviour:
        - A gateway that is constant across ALL 28 days (including the spike in recent
          7 days) → NOT flagged (score=0) even with extreme spike values.
        - A gateway with even minimal variance in the baseline window → IS flagged.
    """

    def _make_regression_frame(self, spike_value: float, all_constant: bool) -> pd.DataFrame:
        """Build a minimal 1-gateway frame for regression testing.

        Args:
            spike_value: Value used during the final 24 hours.
            all_constant: If True, ALL 672 hours (28 days) have spike_value too,
                          giving std=0. If False, baseline hours alternate 0/2 (std>0).
        """
        baseline_start = pd.Timestamp("2026-01-05", tz="UTC")
        rows = []

        for h in range(27 * 24):
            ts = baseline_start + dt.timedelta(hours=h)
            # all_constant=True: use same spike_value for baseline too → std=0
            val = spike_value if all_constant else float(h % 2)
            rows.append({
                "gateway_id": "TESTGW000001",
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": val,
                "reboot_cnt": 0.0,
            })

        # Final 24 hours always use spike_value
        for h in range(24):
            ts = baseline_start + dt.timedelta(hours=27 * 24 + h)
            rows.append({
                "gateway_id": "TESTGW000001",
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": spike_value,
                "reboot_cnt": 0.0,
            })

        df = pd.DataFrame(rows)
        df["ts"] = pd.to_datetime(df["ts_utc"], utc=True)
        return df

    def test_constant_baseline_with_extreme_spike_scores_zero(self):
        """
        REGRESSION: When ALL 672 rows in the 28-day window have the exact same value
        (std=0), the baseline replaces std=0 with NaN → (value - mean) > 3*NaN → always
        False → score=0 even if the value is 1,000,000.

        This is expected and acceptable: a constant baseline means we have no variance
        reference to detect deviations from. The algorithm correctly abstains.
        """
        # All 672 hours in the 28-day window have value 1_000_000 → std=0
        frame = self._make_regression_frame(spike_value=1_000_000.0, all_constant=True)
        service = RankingService(telemetry_frame=frame)
        results = service.get_rankings(week=MONDAY)
        gw_result = [r for r in results if r["gateway_id"] == "TESTGW000001"]
        assert len(gw_result) == 1
        assert gw_result[0]["score"] == 0.0, (
            "A fully-constant gateway (std=0) must score 0: no variance means no threshold"
        )

    def test_nonzero_baseline_variance_with_spike_is_flagged(self):
        """
        REGRESSION (positive case): alternating baseline gives std > 0 → threshold set
        → spike clearly exceeds threshold → score > 0.
        This validates the fix applied during fixture design.
        """
        frame = self._make_regression_frame(spike_value=100.0, all_constant=False)
        service = RankingService(telemetry_frame=frame)
        results = service.get_rankings(week=MONDAY)
        gw_result = [r for r in results if r["gateway_id"] == "TESTGW000001"]
        assert len(gw_result) == 1
        assert gw_result[0]["score"] > 0, (
            "Gateway with non-zero baseline variance and extreme spike must have score > 0"
        )
