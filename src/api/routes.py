"""
FastAPI Routes for Gateway Rankings and Diagnostics.
====================================================

These route handlers form a thin HTTP layer:
  - Validating and extracting request parameters
  - Delegating business logic to RankingService
  - Converting exceptions into clear HTTP error responses
  - Returning typed Pydantic responses
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.models import (
    GatewayExplanationResponse,
    RankingResponse,
    RunResponse,
    StrategyItem,
    StrategyListResponse,
    WeeksListResponse,
)
from src.ranking.registry import available_strategies
from src.services.ranking_service import (
    DataNotFoundError,
    GatewayNotFoundError,
    InvalidWeekError,
    RankingService,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Default singleton instance of the service for application runtime
_service_instance = RankingService()


def get_ranking_service() -> RankingService:
    """Dependency provider for RankingService.

    Can be overridden in pytest using app.dependency_overrides[get_ranking_service].
    """
    return _service_instance


@router.get(
    "/rankings",
    response_model=RankingResponse,
    summary="Retrieve weekly gateway rankings",
    description="Returns the top recommended gateways for technician visits for a given week Monday.",
    tags=["Rankings"],
)
def get_rankings(
    week: str = Query(
        "2026-02-02",
        description="Monday starting the scored week (YYYY-MM-DD)",
        examples=["2026-02-02"],
    ),
    strategy: Optional[str] = Query(
        None,
        description="Ranking strategy algorithm (defaults to 'three_sigma')",
        examples=["three_sigma"],
    ),
    limit: int = Query(
        15,
        ge=1,
        le=100,
        description="Maximum number of gateways to return (default 15 per challenge spec)",
    ),
    service: RankingService = Depends(get_ranking_service),
) -> RankingResponse:
    try:
        results = service.get_rankings(week=week, strategy_name=strategy, limit=limit)
        return RankingResponse(
            week_start=week,
            strategy=strategy or service.default_strategy,
            count=len(results),
            rankings=results,
        )
    except DataNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InvalidWeekError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/gateways/{gateway_id}",
    response_model=GatewayExplanationResponse,
    summary="Retrieve diagnostic explanation for a gateway",
    description="Returns 28-day baseline stats, recent 7-day metric summaries, and anomaly breach counts.",
    tags=["Gateways"],
)
def get_gateway_explanation(
    gateway_id: str,
    week: Optional[str] = Query(
        "2026-02-02",
        description="Monday starting the evaluation window (YYYY-MM-DD)",
        examples=["2026-02-02"],
    ),
    strategy: Optional[str] = Query(
        None,
        description="Ranking strategy algorithm (defaults to 'three_sigma')",
    ),
    service: RankingService = Depends(get_ranking_service),
) -> GatewayExplanationResponse:
    try:
        explanation = service.get_gateway_explanation(
            gateway_id=gateway_id,
            week=week,
            strategy_name=strategy,
        )
        return GatewayExplanationResponse(**explanation)
    except GatewayNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DataNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InvalidWeekError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/rankings/run",
    response_model=RunResponse,
    summary="Trigger new ranking pipeline run / reload data",
    description=(
        "Reloads telemetry data from disk and refreshes in-memory caches. "
        "Use when new telemetry data is dropped into the data folder."
    ),
    tags=["Pipeline"],
)
def run_pipeline(
    service: RankingService = Depends(get_ranking_service),
) -> RunResponse:
    try:
        stats_dict = service.reload_data()
        return RunResponse(
            status="success",
            message="Telemetry reloaded and ready for ranking.",
            rows_loaded=stats_dict["rows_loaded"],
            gateways_count=stats_dict["gateways_count"],
            min_timestamp=stats_dict.get("min_timestamp"),
            max_timestamp=stats_dict.get("max_timestamp"),
        )
    except DataNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during pipeline run")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {exc}",
        ) from exc


@router.get(
    "/rankings/weeks",
    response_model=WeeksListResponse,
    summary="List available scored weeks",
    description="Returns the list of Mondays evaluated in the challenge baseline.",
    tags=["Rankings"],
)
def list_weeks(
    service: RankingService = Depends(get_ranking_service),
) -> WeeksListResponse:
    return WeeksListResponse(weeks=service.get_available_weeks())


@router.get(
    "/strategies",
    response_model=StrategyListResponse,
    summary="List registered ranking algorithms",
    description="Returns available ranking strategies registered in the system.",
    tags=["Strategies"],
)
def list_strategies() -> StrategyListResponse:
    strategies_info = [
        StrategyItem(
            name="three_sigma",
            description="3-sigma anomaly detector comparing trailing 7 days against 28-day gateway baseline",
            is_default=True,
        )
    ]
    # In case more are registered dynamically:
    registered = available_strategies()
    existing_names = {s.name for s in strategies_info}
    for name in registered:
        if name not in existing_names:
            strategies_info.append(
                StrategyItem(
                    name=name,
                    description=f"Alternative strategy: {name}",
                    is_default=False,
                )
            )
    return StrategyListResponse(strategies=strategies_info)
