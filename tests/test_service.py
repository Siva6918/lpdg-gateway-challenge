"""
Unit tests for the RankingService layer.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import pytest
import pandas as pd

from src.services.ranking_service import (
    CorruptDataError,
    DataNotFoundError,
    GatewayNotFoundError,
    InvalidWeekError,
    NoDataInWindowError,
    RankingService,
)
from tests.conftest import GATEWAY_ANOMALOUS, GATEWAY_NORMAL, MONDAY


class TestServiceRankings:
    def test_get_rankings_returns_list_of_dicts(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        results = service.get_rankings(week=MONDAY)
        assert isinstance(results, list)
        assert len(results) == 2
        for item in results:
            assert "gateway_id" in item
            assert "rank" in item
            assert "score" in item
            assert "reason" in item

    def test_get_rankings_top_1_is_anomalous(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        results = service.get_rankings(week=MONDAY)
        assert results[0]["gateway_id"] == GATEWAY_ANOMALOUS
        assert results[0]["rank"] == 1
        assert results[0]["score"] > 0

    def test_get_rankings_respects_limit(self, frame_with_15_gateways: pd.DataFrame):
        service = RankingService(telemetry_frame=frame_with_15_gateways)
        results = service.get_rankings(week=MONDAY, limit=5)
        assert len(results) == 5
        assert results[0]["rank"] == 1
        assert results[4]["rank"] == 5

    def test_get_rankings_invalid_date_format(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        with pytest.raises(InvalidWeekError) as exc:
            service.get_rankings(week="not-a-date")
        assert "Invalid date format" in str(exc.value)

    def test_get_rankings_date_outside_range_raises_no_data_in_window(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        with pytest.raises(NoDataInWindowError) as exc:
            service.get_rankings(week="2020-01-01")
        assert "No telemetry data available" in str(exc.value)


class TestServiceGatewayExplanation:
    def test_explain_anomalous_gateway(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        diag = service.get_gateway_explanation(GATEWAY_ANOMALOUS, week=MONDAY)

        assert diag["gateway_id"] == GATEWAY_ANOMALOUS
        assert diag["week_start"] == "2026-02-02"
        assert diag["rank"] == 1
        assert diag["is_top_15"] is True
        assert diag["score"] > 0
        assert "baseline_stats_28d" in diag
        assert "disconnection_cnt" in diag["baseline_stats_28d"]
        assert "recent_metrics_7d" in diag
        assert "breach_hours_by_metric" in diag
        assert diag["breach_hours_by_metric"]["disconnection_cnt"] > 0

    def test_explain_normal_gateway(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        diag = service.get_gateway_explanation(GATEWAY_NORMAL, week=MONDAY)

        assert diag["gateway_id"] == GATEWAY_NORMAL
        assert diag["score"] == 0.0
        assert diag["breach_hours_by_metric"]["disconnection_cnt"] == 0

    def test_explain_nonexistent_gateway_raises_not_found(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        with pytest.raises(GatewayNotFoundError) as exc:
            service.get_gateway_explanation("UNKNOWN_GW_123", week=MONDAY)
        assert "UNKNOWN_GW_123" in str(exc.value)

    def test_explain_date_without_data_raises_no_data_in_window(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        with pytest.raises(NoDataInWindowError):
            service.get_gateway_explanation(GATEWAY_ANOMALOUS, week="2020-01-01")


class TestServiceDataErrors:
    def test_missing_data_dir_raises_data_not_found(self, tmp_path: pathlib.Path):
        non_existent = tmp_path / "does_not_exist"
        service = RankingService(data_dir=non_existent)
        with pytest.raises(DataNotFoundError) as exc:
            service.get_data()
        assert "Telemetry directory not found" in str(exc.value)

    def test_empty_telemetry_dir_raises_data_not_found(self, tmp_path: pathlib.Path):
        empty_telemetry = tmp_path / "telemetry"
        empty_telemetry.mkdir(parents=True)
        service = RankingService(data_dir=tmp_path)
        with pytest.raises(DataNotFoundError) as exc:
            service.get_data()
        assert "No parquet files found" in str(exc.value)

    def test_empty_injected_dataframe_raises_corrupt_data_error(self):
        service = RankingService(telemetry_frame=pd.DataFrame())
        with pytest.raises(CorruptDataError) as exc:
            service.get_data()
        assert "Telemetry dataset is empty" in str(exc.value)

    def test_parquet_missing_required_columns_raises_corrupt_data_error(self, tmp_path: pathlib.Path):
        telemetry_dir = tmp_path / "telemetry"
        telemetry_dir.mkdir(parents=True)
        # Create a parquet file missing required columns like offline_duration_sec
        bad_df = pd.DataFrame({"gateway_id": ["GW001"], "ts_utc": ["2026-01-01T00:00:00Z"]})
        bad_df.to_parquet(telemetry_dir / "bad.parquet")

        service = RankingService(data_dir=tmp_path)
        with pytest.raises(CorruptDataError) as exc:
            service.get_data()
        assert "missing required column" in str(exc.value).lower()

    def test_get_available_weeks(self, minimal_frame: pd.DataFrame):
        # minimal_frame contains telemetry covering 2026-01-05 to 2026-02-01
        service = RankingService(telemetry_frame=minimal_frame)
        weeks = service.get_available_weeks()
        assert "2026-02-02" in weeks
        assert all(isinstance(w, str) for w in weeks)

    def test_get_available_weeks_dynamically_expands_with_new_data(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        weeks_before = service.get_available_weeks()
        assert "2026-02-02" in weeks_before
        assert "2026-02-09" not in weeks_before

        # Simulate new week of data added (e.g. week 2026-02-09)
        extra_start = pd.Timestamp("2026-02-02", tz="UTC")
        extra_rows = []
        for h in range(7 * 24):
            extra_rows.append({
                "gateway_id": GATEWAY_NORMAL,
                "ts_utc": (extra_start + dt.timedelta(hours=h)).isoformat().replace("+00:00", "Z"),
                "offline_duration_sec": 0.0,
                "disconnection_cnt": 0.0,
                "reboot_cnt": 0.0,
            })
        extra_df = pd.DataFrame(extra_rows)
        extra_df["ts"] = pd.to_datetime(extra_df["ts_utc"], utc=True)
        expanded_frame = pd.concat([minimal_frame, extra_df], ignore_index=True)

        service_expanded = RankingService(telemetry_frame=expanded_frame)
        weeks_after = service_expanded.get_available_weeks()
        assert "2026-02-02" in weeks_after
        assert "2026-02-09" in weeks_after
        assert len(weeks_after) == len(weeks_before) + 1
