"""
Pydantic Data Models for the LPDG Ranking API.
===============================================

These define the request and response schemas for all API endpoints,
ensuring strict validation and automatic OpenAPI documentation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GatewayRankItem(BaseModel):
    """A single ranked gateway entry."""

    gateway_id: str = Field(..., description="12-character hex gateway identifier")
    rank: int = Field(..., description="1-based ranking index (1 = highest priority)")
    score: float = Field(..., description="Anomaly score (number of flagged breach hours)")
    reason: str = Field(
        ...,
        description=(
            "Human-readable explanation of why this gateway is flagged. "
            "Example: '42 hour(s) beyond 3 sigma of this gateway's own 28-day baseline "
            "in the last 7 days; first breach on disconnection_cnt'"
        ),
    )


class RankingResponse(BaseModel):
    """Response schema for GET /rankings."""

    week_start: str = Field(..., description="ISO Monday starting the scored week (e.g. '2026-02-02')")
    strategy: str = Field(..., description="Name of the ranking strategy used (e.g. 'three_sigma')")
    count: int = Field(..., description="Number of gateways returned in this batch")
    rankings: List[GatewayRankItem] = Field(..., description="List of ranked gateway recommendations")


class GatewayExplanationResponse(BaseModel):
    """Response schema for GET /gateways/{gateway_id}."""

    gateway_id: str = Field(..., description="12-character hex gateway identifier")
    week_start: str = Field(..., description="ISO Monday starting the evaluation window")
    rank: Optional[int] = Field(None, description="Ranking index within the evaluated week, if in scored list")
    is_top_15: bool = Field(..., description="Whether this gateway is recommended for a technician visit")
    score: float = Field(..., description="Total anomaly score (flagged hours)")
    reason: str = Field(..., description="Explanation summary")
    baseline_stats_28d: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Per-metric mean and std calculated over the 28-day baseline window",
    )
    recent_metrics_7d: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Per-metric 7-day sum and 1-hour maximum in recent evaluation window",
    )
    breach_hours_by_metric: Dict[str, int] = Field(
        ...,
        description="Number of breach hours flagged for each metric",
    )


class RunResponse(BaseModel):
    """Response schema for POST /rankings/run."""

    status: str = Field(..., description="Execution status (e.g. 'success')")
    message: str = Field(..., description="Summary message")
    rows_loaded: int = Field(..., description="Number of telemetry rows in memory")
    gateways_count: int = Field(..., description="Number of unique gateways in dataset")
    min_timestamp: Optional[str] = Field(None, description="Earliest telemetry timestamp loaded")
    max_timestamp: Optional[str] = Field(None, description="Latest telemetry timestamp loaded")


class StrategyItem(BaseModel):
    """Information about an available ranking algorithm."""

    name: str = Field(..., description="Strategy identifier name used in API calls")
    description: str = Field(..., description="High-level description of the ranking algorithm")
    is_default: bool = Field(..., description="Whether this is the default ranking strategy")


class StrategyListResponse(BaseModel):
    """Response schema for GET /strategies."""

    strategies: List[StrategyItem] = Field(..., description="List of registered ranking strategies")


class WeeksListResponse(BaseModel):
    """Response schema for GET /rankings/weeks."""

    weeks: List[str] = Field(..., description="List of valid Monday dates for scored weeks")
