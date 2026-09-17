"""
Integration tests for FastAPI API endpoints.
"""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.routes import get_ranking_service
from src.services.ranking_service import RankingService
from tests.conftest import GATEWAY_ANOMALOUS, GATEWAY_NORMAL, MONDAY


@pytest.fixture()
def test_client(minimal_frame) -> TestClient:
    """Return a TestClient backed by minimal in-memory data."""
    service = RankingService(telemetry_frame=minimal_frame)
    app.dependency_overrides[get_ranking_service] = lambda: service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def client_15gw(frame_with_15_gateways) -> TestClient:
    """Return a TestClient backed by 15-gateway data."""
    service = RankingService(telemetry_frame=frame_with_15_gateways)
    app.dependency_overrides[get_ranking_service] = lambda: service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestHealthCheck:
    def test_health_check_returns_200(self, test_client: TestClient):
        response = test_client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"


class TestGetRankings:
    def test_rankings_valid_week(self, test_client: TestClient):
        response = test_client.get("/rankings?week=2026-02-02")
        assert response.status_code == 200
        body = response.json()
        assert body["week_start"] == "2026-02-02"
        assert body["strategy"] == "three_sigma"
        assert body["count"] == 2
        rankings = body["rankings"]
        assert len(rankings) == 2

    def test_rankings_first_is_anomalous(self, test_client: TestClient):
        response = test_client.get("/rankings?week=2026-02-02")
        assert response.status_code == 200
        body = response.json()
        assert body["rankings"][0]["gateway_id"] == GATEWAY_ANOMALOUS
        assert body["rankings"][0]["rank"] == 1
        assert body["rankings"][0]["score"] > 0

    def test_rankings_has_required_fields(self, test_client: TestClient):
        response = test_client.get("/rankings?week=2026-02-02")
        assert response.status_code == 200
        for item in response.json()["rankings"]:
            assert "gateway_id" in item
            assert "rank" in item
            assert "score" in item
            assert "reason" in item

    def test_rankings_limit_parameter(self, client_15gw: TestClient):
        response = client_15gw.get("/rankings?week=2026-02-02&limit=5")
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 5
        assert len(body["rankings"]) == 5

    def test_rankings_invalid_date_returns_400(self, test_client: TestClient):
        response = test_client.get("/rankings?week=not-a-date")
        assert response.status_code == 400

    def test_rankings_no_data_for_week_returns_400(self, test_client: TestClient):
        response = test_client.get("/rankings?week=2020-01-06")
        assert response.status_code == 400

    def test_rankings_unknown_strategy_returns_400(self, test_client: TestClient):
        response = test_client.get("/rankings?week=2026-02-02&strategy=unknown_algo")
        assert response.status_code == 400

    def test_rankings_corrupt_data_returns_422(self):
        service = RankingService(telemetry_frame=pd.DataFrame())
        app.dependency_overrides[get_ranking_service] = lambda: service
        client = TestClient(app)
        try:
            response = client.get("/rankings?week=2026-02-02")
            assert response.status_code == 422
            assert "empty" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


class TestGetGatewayExplanation:
    def test_known_gateway_returns_200(self, test_client: TestClient):
        response = test_client.get(f"/gateways/{GATEWAY_ANOMALOUS}?week=2026-02-02")
        assert response.status_code == 200

    def test_response_has_all_diagnostic_fields(self, test_client: TestClient):
        response = test_client.get(f"/gateways/{GATEWAY_ANOMALOUS}?week=2026-02-02")
        body = response.json()
        assert body["gateway_id"] == GATEWAY_ANOMALOUS
        assert body["week_start"] == "2026-02-02"
        assert body["rank"] == 1
        assert body["is_top_15"] is True
        assert body["score"] > 0
        assert "baseline_stats_28d" in body
        assert "offline_duration_sec" in body["baseline_stats_28d"]
        assert "recent_metrics_7d" in body
        assert "breach_hours_by_metric" in body

    def test_normal_gateway_has_zero_score(self, test_client: TestClient):
        response = test_client.get(f"/gateways/{GATEWAY_NORMAL}?week=2026-02-02")
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 0.0
        assert body["breach_hours_by_metric"]["disconnection_cnt"] == 0

    def test_unknown_gateway_returns_404(self, test_client: TestClient):
        response = test_client.get("/gateways/FFFFFFFFFFFF?week=2026-02-02")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_gateway_with_no_data_in_window_returns_400(self, test_client: TestClient):
        response = test_client.get(f"/gateways/{GATEWAY_ANOMALOUS}?week=2020-01-06")
        assert response.status_code == 400


class TestRunPipeline:
    def test_run_pipeline_returns_200(self, test_client: TestClient):
        response = test_client.post("/rankings/run")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["rows_loaded"] > 0
        assert body["gateways_count"] == 2
        assert "min_timestamp" in body
        assert "max_timestamp" in body

    def test_run_pipeline_data_dir_not_found(self):
        """When no data dir exists and no in-memory data, run returns 503."""
        import pathlib
        service = RankingService(data_dir=pathlib.Path("/nonexistent/path"))
        app.dependency_overrides[get_ranking_service] = lambda: service
        client = TestClient(app)
        try:
            response = client.post("/rankings/run")
            assert response.status_code == 503
        finally:
            app.dependency_overrides.clear()

    def test_run_pipeline_corrupt_data_returns_422(self):
        """When data frame is corrupt or empty, run returns 422."""
        service = RankingService(telemetry_frame=pd.DataFrame())
        app.dependency_overrides[get_ranking_service] = lambda: service
        client = TestClient(app)
        try:
            response = client.post("/rankings/run")
            assert response.status_code == 422
            assert "empty" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


class TestWeeksList:
    def test_weeks_list_returns_8_weeks(self, test_client: TestClient):
        response = test_client.get("/rankings/weeks")
        assert response.status_code == 200
        weeks = response.json()["weeks"]
        assert len(weeks) == 8
        assert weeks[0] == "2026-02-02"
        assert weeks[-1] == "2026-03-23"


class TestStrategiesList:
    def test_strategies_list_includes_three_sigma(self, test_client: TestClient):
        response = test_client.get("/strategies")
        assert response.status_code == 200
        strategies = response.json()["strategies"]
        names = [s["name"] for s in strategies]
        assert "three_sigma" in names

    def test_strategies_list_default_is_three_sigma(self, test_client: TestClient):
        response = test_client.get("/strategies")
        strategies = response.json()["strategies"]
        defaults = [s for s in strategies if s["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "three_sigma"


class TestDocumentationOffline:
    """Regression tests: verify docs work 100% offline with zero CDN dependencies."""

    def test_docs_served_with_local_assets_only(self, test_client: TestClient):
        response = test_client.get("/docs")
        assert response.status_code == 200
        html = response.text

        # Verify local asset paths are linked
        assert 'href="/static/swagger-ui.css"' in html
        assert 'src="/static/swagger-ui-bundle.js"' in html
        assert 'href="/static/favicon.png"' in html

        # Verify no external CDN or external web URLs are present in the HTML
        assert "cdn.jsdelivr.net" not in html
        assert "unpkg.com" not in html
        assert "cdnjs.cloudflare.com" not in html
        assert "fastapi.tiangolo.com" not in html
        assert "http://" not in html
        assert "https://" not in html

    def test_static_swagger_assets_served_locally(self, test_client: TestClient):
        # JS bundle
        res_js = test_client.get("/static/swagger-ui-bundle.js")
        assert res_js.status_code == 200
        assert len(res_js.content) > 100_000

        # CSS stylesheet
        res_css = test_client.get("/static/swagger-ui.css")
        assert res_css.status_code == 200
        assert len(res_css.content) > 50_000

        # Favicon
        res_fav = test_client.get("/static/favicon.png")
        assert res_fav.status_code == 200
        assert len(res_fav.content) > 100

    def test_openapi_schema_available_locally(self, test_client: TestClient):
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/rankings" in schema["paths"]
        assert "/gateways/{gateway_id}" in schema["paths"]
        assert "/rankings/run" in schema["paths"]

    def test_redoc_disabled_to_prevent_cdn_leak(self, test_client: TestClient):
        response = test_client.get("/redoc")
        assert response.status_code == 404
