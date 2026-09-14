"""
tests/test_new_data.py — New-data-without-restart test.

This is the most critical Round-2 requirement:

  1. Start the API (represented here by a RankingService pointing at real disk).
  2. Keep the process running — no restart.
  3. Add a new parquet file to data/telemetry/.
  4. Call POST /rankings/run  (reload_data).
  5. Verify the service picked up the new data.

The test writes synthetic Parquet to a temporary directory on disk, so it
exercises the actual file I/O path and confirms the cache-invalidation
mechanism works end-to-end.

IMPORTANT: We do NOT use the real 104 MB challenge dataset.
           We construct our own small Parquet fixture here.
"""

from __future__ import annotations

import datetime as dt
import pathlib

import pandas as pd
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from fastapi.testclient import TestClient

from src.main import app
from src.api.routes import get_ranking_service
from src.services.ranking_service import RankingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

METRICS = ["offline_duration_sec", "disconnection_cnt", "reboot_cnt"]
_MONDAY_1 = dt.date(2026, 2, 2)   # first scored week
_MONDAY_2 = dt.date(2026, 3, 2)   # a later scored week


def _make_telemetry_df(
    gateway_id: str,
    start: pd.Timestamp,
    hours: int,
    disconnection_cnt: float = 0.0,
) -> pd.DataFrame:
    """Create `hours` rows of synthetic hourly telemetry for one gateway."""
    ts_list = [start + dt.timedelta(hours=h) for h in range(hours)]
    return pd.DataFrame({
        "gateway_id": gateway_id,
        "ts_utc": [t.isoformat().replace("+00:00", "Z") for t in ts_list],
        "offline_duration_sec": 0.0,
        "disconnection_cnt": disconnection_cnt,
        "reboot_cnt": 0.0,
    })


def _write_parquet(df: pd.DataFrame, path: pathlib.Path) -> None:
    """Write DataFrame to a parquet file. Creates parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path))


def _build_baseline_gateways(n: int, start: pd.Timestamp) -> pd.DataFrame:
    """Build n gateways with normal (non-anomalous) 28-day baseline data.

    These provide the minimum 15 gateways required for a full week ranking.
    Each has consistent but non-zero variance so they are rankable.
    """
    frames = []
    for i in range(n):
        gw_id = f"NORM{i:08d}"
        rows = []
        for h in range(28 * 24):
            ts = start + dt.timedelta(hours=h)
            rows.append({
                "gateway_id": gw_id,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": float(h % 2),  # alternating 0/1 → std > 0
                "reboot_cnt": 0.0,
            })
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Core new-data-without-restart test
# ---------------------------------------------------------------------------

class TestNewDataWithoutRestart:
    """
    REQUIREMENT: POST /rankings/run must pick up new parquet files from disk
    without restarting the application process.

    This test simulates the live session scenario described in Round 2:
      - Drop a new month of telemetry into data/telemetry/
      - Call /run
      - Verify the system reflects the new data
    """

    def test_run_picks_up_new_parquet_file(self, tmp_path: pathlib.Path):
        """
        Scenario:
          1. Create a telemetry directory with one parquet file (Month A).
          2. Start the service pointing at that directory (no process restart).
          3. Verify initial state: service has Month A data.
          4. Write a SECOND parquet file with Month B data (the new month).
          5. Call reload_data() — same service instance, no restart.
          6. Verify: service now has Month A + Month B data.

        This directly tests the cache-invalidation mechanism.
        """
        telemetry_dir = tmp_path / "telemetry"
        telemetry_dir.mkdir()

        # --- Month A: baseline data for week 2026-02-02 ---
        # 28 days before 2026-02-02 starts on 2026-01-05
        month_a_start = pd.Timestamp("2026-01-05", tz="UTC")
        gw_anomalous = "AABB00000001"

        # 27 days of alternating 0/2, then 24h spike → flagged
        rows_a = []
        for h in range(27 * 24):
            ts = month_a_start + dt.timedelta(hours=h)
            rows_a.append({
                "gateway_id": gw_anomalous,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": float(h % 2) * 2.0,
                "reboot_cnt": 0.0,
            })
        for h in range(24):
            ts = month_a_start + dt.timedelta(hours=27 * 24 + h)
            rows_a.append({
                "gateway_id": gw_anomalous,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": 100.0,
                "reboot_cnt": 0.0,
            })

        # Add 14 normal gateways so we can rank top 15
        baseline_df = _build_baseline_gateways(14, month_a_start)
        month_a_df = pd.concat([pd.DataFrame(rows_a), baseline_df], ignore_index=True)

        _write_parquet(month_a_df, telemetry_dir / "month_a.parquet")

        # --- Start the service (no injected frame → reads from disk) ---
        service = RankingService(data_dir=tmp_path)

        # Initial load: verify Month A data
        data_before = service.get_data()
        rows_before = len(data_before)
        assert rows_before > 0, "Service should have loaded Month A data"

        # Verify we can rank for 2026-02-02 (Month A window)
        rankings_before = service.get_rankings(week=_MONDAY_1)
        assert len(rankings_before) == 15
        assert rankings_before[0]["gateway_id"] == gw_anomalous, (
            "Anomalous gateway should be rank 1 in Month A"
        )

        # --- Month B: NEW data arriving (simulated new month) ---
        # This represents the live session scenario: ops drops a new parquet
        # into data/telemetry/ after the service has already started.
        # Month B covers March 2026 (for 2026-03-02 week).
        month_b_start = pd.Timestamp("2026-02-02", tz="UTC")
        gw_new = "CCDD00000002"  # brand-new gateway not in Month A
        rows_b = []
        for h in range(27 * 24):
            ts = month_b_start + dt.timedelta(hours=h)
            rows_b.append({
                "gateway_id": gw_new,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": float(h % 2) * 2.0,
                "reboot_cnt": 0.0,
            })
        for h in range(24):
            ts = month_b_start + dt.timedelta(hours=27 * 24 + h)
            rows_b.append({
                "gateway_id": gw_new,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": 200.0,
                "reboot_cnt": 0.0,
            })

        # Also add 14 normal gateways for Month B
        month_b_baseline = _build_baseline_gateways(14, month_b_start)
        month_b_df = pd.concat([pd.DataFrame(rows_b), month_b_baseline], ignore_index=True)

        # Drop Month B file WHILE THE SERVICE IS STILL RUNNING (no restart)
        _write_parquet(month_b_df, telemetry_dir / "month_b.parquet")

        # --- Call reload_data() — same process, no restart ---
        reload_stats = service.reload_data()
        assert reload_stats["rows_loaded"] > rows_before, (
            "After reload, service must have MORE rows than before "
            "(Month A + Month B combined). "
            f"Before: {rows_before}, After: {reload_stats['rows_loaded']}"
        )

        # --- Verify new gateway is now visible ---
        data_after = service.get_data()
        gateways_after = set(data_after["gateway_id"].unique())
        assert gw_new in gateways_after, (
            f"New gateway {gw_new!r} from Month B must be visible after reload"
        )

        # Verify Month B ranking works (2026-03-02 week)
        rankings_after = service.get_rankings(week=_MONDAY_2)
        assert len(rankings_after) == 15
        assert rankings_after[0]["gateway_id"] == gw_new, (
            f"Brand-new anomalous gateway {gw_new!r} must be rank 1 in Month B"
        )

    def test_run_via_api_endpoint_picks_up_new_data(self, tmp_path: pathlib.Path):
        """
        Same as above, but exercised through the HTTP API layer.

        This is the true end-to-end new-data test:
          HTTP: GET /rankings → initial count
          File: write new parquet to disk
          HTTP: POST /rankings/run → reload
          HTTP: GET /rankings for new week → verify new gateway appears
        """
        telemetry_dir = tmp_path / "telemetry"
        telemetry_dir.mkdir()

        # Month A: 15 normal gateways
        month_a_start = pd.Timestamp("2026-01-05", tz="UTC")
        gw_anomalous = "EEFF00000003"

        rows_a = []
        for h in range(27 * 24):
            ts = month_a_start + dt.timedelta(hours=h)
            rows_a.append({
                "gateway_id": gw_anomalous,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": float(h % 2) * 2.0,
                "reboot_cnt": 0.0,
            })
        for h in range(24):
            ts = month_a_start + dt.timedelta(hours=27 * 24 + h)
            rows_a.append({
                "gateway_id": gw_anomalous,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": 100.0,
                "reboot_cnt": 0.0,
            })

        baseline_df = _build_baseline_gateways(14, month_a_start)
        month_a_df = pd.concat([pd.DataFrame(rows_a), baseline_df], ignore_index=True)
        _write_parquet(month_a_df, telemetry_dir / "month_a.parquet")

        # Wire up the API with a disk-reading service (no injected frame)
        service = RankingService(data_dir=tmp_path)
        app.dependency_overrides[get_ranking_service] = lambda: service
        client = TestClient(app)

        try:
            # Step 1: Initial GET /rankings — Month A data
            resp = client.get("/rankings?week=2026-02-02&limit=15")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            body_before = resp.json()
            gateways_before = {r["gateway_id"] for r in body_before["rankings"]}
            assert gw_anomalous in gateways_before

            # Step 2: Write Month B parquet WHILE SERVICE IS RUNNING
            month_b_start = pd.Timestamp("2026-02-02", tz="UTC")
            gw_new = "8899AABBCC01"
            rows_b = []
            for h in range(27 * 24):
                ts = month_b_start + dt.timedelta(hours=h)
                rows_b.append({
                    "gateway_id": gw_new,
                    "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                    "offline_duration_sec": 0.0,
                    "disconnection_cnt": float(h % 2) * 2.0,
                    "reboot_cnt": 0.0,
                })
            for h in range(24):
                ts = month_b_start + dt.timedelta(hours=27 * 24 + h)
                rows_b.append({
                    "gateway_id": gw_new,
                    "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                    "offline_duration_sec": 0.0,
                    "disconnection_cnt": 500.0,
                    "reboot_cnt": 0.0,
                })
            month_b_baseline = _build_baseline_gateways(14, month_b_start)
            month_b_df = pd.concat([pd.DataFrame(rows_b), month_b_baseline], ignore_index=True)
            _write_parquet(month_b_df, telemetry_dir / "month_b.parquet")

            # Step 3: POST /rankings/run — no restart, same process
            run_resp = client.post("/rankings/run")
            assert run_resp.status_code == 200
            run_body = run_resp.json()
            assert run_body["status"] == "success"

            # Step 4: GET /rankings for 2026-03-02 — Month B window
            resp_after = client.get("/rankings?week=2026-03-02&limit=15")
            assert resp_after.status_code == 200
            body_after = resp_after.json()
            gateways_after = {r["gateway_id"] for r in body_after["rankings"]}
            assert gw_new in gateways_after, (
                f"New gateway {gw_new!r} from Month B must appear after reload. "
                f"Got gateways: {gateways_after}"
            )

        finally:
            app.dependency_overrides.clear()

    def test_new_gateway_from_unseen_month_does_not_crash(self, tmp_path: pathlib.Path):
        """
        Robustness test: a gateway that appears for the first time in a new month
        (no historical baseline before the scored week) must NOT crash the pipeline.

        Expected behaviour: it scores 0 (no variance reference), not an error.
        """
        telemetry_dir = tmp_path / "telemetry"
        telemetry_dir.mkdir()

        # Write a gateway whose data only starts at the very edge of the window
        # (only 7 days of data, no full 28-day baseline)
        start = pd.Timestamp("2026-01-26", tz="UTC")  # only 7 days before 2026-02-02
        gw_brand_new = "FFFF00000099"
        rows = []
        for h in range(7 * 24):
            ts = start + dt.timedelta(hours=h)
            rows.append({
                "gateway_id": gw_brand_new,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": 999.0,  # extreme value, but std=0 (constant)
                "reboot_cnt": 0.0,
            })

        # Need 14 more gateways with full 28-day data to fill ranking
        month_a_start = pd.Timestamp("2026-01-05", tz="UTC")
        normal_df = _build_baseline_gateways(14, month_a_start)
        df = pd.concat([pd.DataFrame(rows), normal_df], ignore_index=True)
        _write_parquet(df, telemetry_dir / "partial.parquet")

        service = RankingService(data_dir=tmp_path)

        # Must not crash — gateway with no baseline returns score=0
        results = service.get_rankings(week=_MONDAY_1)
        assert len(results) == 15, "Should still return 15 gateways"

    def test_quiet_gateway_does_not_crash_after_reload(self, tmp_path: pathlib.Path):
        """
        Robustness: a gateway that was active in Month A but missing in Month B
        (went quiet) must not crash the pipeline for Month B rankings.
        """
        telemetry_dir = tmp_path / "telemetry"
        telemetry_dir.mkdir()

        # Month A: gw_active is anomalous
        month_a_start = pd.Timestamp("2026-01-05", tz="UTC")
        gw_active = "ACTIVE000001"
        rows_a_active = []
        for h in range(27 * 24):
            ts = month_a_start + dt.timedelta(hours=h)
            rows_a_active.append({
                "gateway_id": gw_active,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": float(h % 2) * 2.0,
                "reboot_cnt": 0.0,
            })
        for h in range(24):
            ts = month_a_start + dt.timedelta(hours=27 * 24 + h)
            rows_a_active.append({
                "gateway_id": gw_active,
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": 100.0,
                "reboot_cnt": 0.0,
            })

        normal_df = _build_baseline_gateways(14, month_a_start)
        month_a_df = pd.concat([pd.DataFrame(rows_a_active), normal_df], ignore_index=True)
        _write_parquet(month_a_df, telemetry_dir / "month_a.parquet")

        service = RankingService(data_dir=tmp_path)

        # Verify initial state
        rankings_a = service.get_rankings(week=_MONDAY_1)
        assert rankings_a[0]["gateway_id"] == gw_active

        # Month B: gw_active is absent (went quiet)
        month_b_start = pd.Timestamp("2026-02-02", tz="UTC")
        normal_df_b = _build_baseline_gateways(15, month_b_start)  # 15 normals fill the list
        _write_parquet(normal_df_b, telemetry_dir / "month_b.parquet")

        # Reload without restart — must not raise
        reload_stats = service.reload_data()
        assert reload_stats["rows_loaded"] > 0

        # gw_active is now absent from Month B window — should still return 15 results
        rankings_b = service.get_rankings(week=_MONDAY_2)
        assert len(rankings_b) == 15, (
            "Should return 15 gateways even when previously active gateway goes quiet"
        )
        # gw_active should NOT appear in Month B (it has no data there)
        gw_ids = {r["gateway_id"] for r in rankings_b}
        assert gw_active not in gw_ids, (
            "Quiet gateway should not appear in weeks where it has no data"
        )
