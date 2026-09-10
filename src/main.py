"""
LPDG Innovation Hub — Software Development API
===============================================

This is the entry point for the FastAPI web application.

Architecture overview (for newcomers):
  - src/config.py           → where data/ lives, read once at startup
  - src/ranking/base.py     → abstract RankingStrategy interface
  - src/ranking/three_sigma.py → ThreeSigmaRanker (wraps baseline logic)
  - src/services/ranking_service.py → business logic (load data, rank, explain)
  - src/api/routes.py       → FastAPI routes (thin HTTP layer, no business logic)
  - src/api/models.py       → Pydantic request/response models

To start the server:
    uvicorn src.main:app --reload

To use a different data directory:
    DATA_DIR=/other/path uvicorn src.main:app --reload
"""

from fastapi import FastAPI

from src.api.routes import router

app = FastAPI(
    title="LPDG Innovation Hub — Gateway Ranking API",
    description=(
        "Ranks IoT gateways by anomaly severity and recommends the top 15 "
        "for field visits each week. Part 2 of the LPDG Innovation Hub "
        "Selection Challenge 2026."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.get("/", tags=["health"])
def health_check() -> dict:
    """Simple health check — confirms the API is running."""
    return {"status": "ok", "service": "LPDG Gateway Ranking API"}
