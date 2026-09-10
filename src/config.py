"""
Configuration for the LPDG Ranking API.

The data directory is resolved in this order:
  1. The DATA_DIR environment variable (if set)
  2. ./data relative to the project root (default)

This means a reviewer can point the app at any directory without touching code:
    DATA_DIR=/path/to/other/data uvicorn src.main:app --reload
"""

from __future__ import annotations

import os
import pathlib

# Project root = one level above this file (src/ -> project root)
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Resolve data directory: env var → default ./data
_env_data = os.environ.get("DATA_DIR")
DATA_DIR: pathlib.Path = pathlib.Path(_env_data) if _env_data else _PROJECT_ROOT / "data"

# The telemetry subfolder (Parquet partitioned dataset)
TELEMETRY_DIR: pathlib.Path = DATA_DIR / "telemetry"
