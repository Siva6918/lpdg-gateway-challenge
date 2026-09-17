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

import pathlib
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from src.api.routes import router

_STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="LPDG Innovation Hub — Gateway Ranking API",
    description=(
        "Ranks IoT gateways by anomaly severity and recommends the top 15 "
        "for field visits each week. Part 2 of the LPDG Innovation Hub "
        "Selection Challenge 2026."
    ),
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.include_router(router)


@app.get("/docs", include_in_schema=False)
def swagger_ui_html():
    """Offline Swagger UI served entirely from local static assets."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
        swagger_ui_parameters={"validatorUrl": None},
    )


@app.get("/", tags=["health"])
def health_check() -> dict:
    """Simple health check — confirms the API is running."""
    return {"status": "ok", "service": "LPDG Gateway Ranking API"}
