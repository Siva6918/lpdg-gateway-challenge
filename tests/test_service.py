"""
Unit tests for the RankingService layer.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import pytest
import pandas as pd

from src.services.ranking_service import (
    RankingService,
    DataNotFoundError,
    GatewayNotFoundError,
    InvalidWeekError,
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

    def test_get_rankings_date_outside_range(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        with pytest.raises(InvalidWeekError) as exc:
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

    def test_explain_date_without_data_raises_invalid_week(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        with pytest.raises(InvalidWeekError):
            service.get_gateway_explanation(GATEWAY_ANOMALOUS, week="2020-01-01")


class TestServiceDataErrors:
    def test_missing_data_dir_raises_data_not_found(self, tmp_path: pathlib.Path):
        non_existent = tmp_path / "does_not_exist"
        service = RankingService(data_dir=non_existent)
        with pytest.raises(DataNotFoundError) as exc:
            service.get_data()
        assert "Telemetry directory not found" in str(exc.value)

    def test_get_available_weeks(self, minimal_frame: pd.DataFrame):
        service = RankingService(telemetry_frame=minimal_frame)
        weeks = service.get_available_weeks()
        assert len(weeks) == 8
        assert weeks[0] == "2026-02-02"
        assert weeks[-1] == "2026-03-23"
