# LPDG Innovation Hub Selection Challenge 2026

## Problem Statement

> Monitor gateway telemetry data and rank/select the top 15 gateways each week for field visits based on abnormal behavior and operational risk.

The LPDG operations team can perform a maximum of **15 field visits per week**. The goal is to build a system that analyzes gateway telemetry behaviour, identifies operational anomalies, and recommends the 15 highest-priority gateways to visit each week along with concise, human-readable explanations for each recommendation.

The challenge consists of two parts:

| Part | Description | Weight |
|---|---|---|
| **Part 1** | Gateway ranking: produce `predictions.csv` with 15 gateways × 8 weeks | 40% |
| **Part 2** | **Software Development** — Build a web API to provide weekly top-15 gateway rankings, explain why a gateway was selected, and rerun the ranking when new telemetry data arrives. | 60% |

---

## Demo Video

LPDG Innovation Hub Selection Challenge 2026 — Software Development

FastAPI-based gateway ranking and diagnostic system featuring explainable weekly rankings, automated testing, API-based reruns, and support for newly added telemetry data.

[Watch the Demo Video](https://portfolio-azure-theta-94.vercel.app/workspace/work/lpdg_submission-mp4)

Portfolio:  
https://portfolio-azure-theta-94.vercel.app/workspace/work/lpdg_submission-mp4

---

## Evaluator Setup & Reproducibility

### 1. Data Directory Setup (Required for Telemetry Processing)
The official LPDG challenge dataset must **not** be committed to version control and is strictly excluded via `.gitignore` (`git status` and `git ls-files data/` confirm it is untracked).

To evaluate telemetry processing or run the baseline:
1. **Required Directory:** The official evaluator-provided `data/` directory is required.
2. **Placement:** Place the evaluator-provided `data/` directory directly at the repository root after cloning:
   ```
   ./data/
   ```
3. **Expected Directory Structure:**
   ```
   data/
   ├── telemetry/              ← Partitioned Parquet dataset (e.g. year=YYYY/month=MM/...)
   ├── gateway_master.csv      ← Gateway metadata
   ├── field_visits.csv        ← Historical field visits
   └── ...
   ```
4. **Default Path:** The application and baseline scripts read `./data` by default.
5. **Alternate Data Directory:** If your evaluation dataset is located elsewhere, point the application to it without modifying code:
   - **Windows PowerShell:**
     ```powershell
     $env:DATA_DIR = "C:\path\to\custom\data"
     uvicorn src.main:app --reload
     ```
   - **Linux / macOS / Git Bash:**
     ```bash
     DATA_DIR=/path/to/custom/data uvicorn src.main:app --reload
     ```
   - **Windows Command Prompt (CMD):**
     ```cmd
     set DATA_DIR=C:\path\to\custom\data && uvicorn src.main:app --reload
     ```
   - **Baseline Script (All Platforms):**
     ```bash
     python baseline_3sigma.py --data /path/to/custom/data
     ```

### 2. Zero External Runtime Dependencies (100% Offline)
- **No Internet Access Required:** The entire application, API endpoints, interactive Swagger documentation (`/docs`), OpenAPI schema (`/openapi.json`), and test suite operate completely offline. All Swagger UI assets are bundled and served locally from `src/static/`.
- **No API Keys Required:** No external services, proprietary tokens, or cloud APIs.
- **No GPU Required:** Runs comfortably on standard CPU / laptop hardware (8–16 GB RAM).
- **No Model Downloads:** Anomaly detection uses statistical 3-sigma thresholds; zero runtime weights or external assets are downloaded.

### 3. Exact Commands Summary

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run automated test suite (63 tests including offline docs regression tests)
pytest -q

# 3. Validate submission predictions file
python validate_submission.py predictions.csv

# 4. Start the Web API (reads ./data by default)
uvicorn src.main:app --reload

# 5. (Optional) Start with an alternate data directory:
# On Windows PowerShell:
$env:DATA_DIR="C:\path\to\custom\data"; uvicorn src.main:app --reload
# On Linux / macOS / Git Bash:
DATA_DIR=/path/to/custom/data uvicorn src.main:app --reload
```

---

## Part 1 — Gateway Ranking

### Approach

Part 1 uses the **provided 3-sigma baseline** (`baseline_3sigma.py`) unchanged. For each scored Monday, it:

1. Takes the trailing 28 days of telemetry for each gateway strictly prior to that Monday.
2. Computes the mean ($\mu$) and standard deviation ($\sigma$) of `offline_duration_sec`, `disconnection_cnt`, and `reboot_cnt`.
3. Flags any hour in the trailing 7 days where any metric exceeds $\mu + 3\sigma$ for that gateway.
4. Ranks gateways by total flagged-hour count across the 7-day window and selects the top 15.

The baseline was selected for Part 1 because:
- The challenge explicitly permits Software Development candidates to use the provided baseline unchanged and focus on Part 2.
- It provides a transparent, explainable, and reproducible operational standard.
- The rationale is formally documented in [`DECISIONS.md`](./DECISIONS.md) (Decision 1 & Decision 2).

### Scored Weeks

Weeks 1–8: `2026-02-02` to `2026-03-23` (consecutive Mondays):
- `2026-02-02`
- `2026-02-09`
- `2026-02-16`
- `2026-02-23`
- `2026-03-02`
- `2026-03-09`
- `2026-03-16`
- `2026-03-23`

### Input Data

Telemetry data is read from the `data/` directory at the project root (or custom `DATA_DIR`):

```
data/
├── telemetry/          ← Parquet partitioned dataset (required)
├── gateway_master.csv  ← Gateway metadata
├── field_visits.csv    ← Historical visits
└── ...
```

### How to Run Part 1

```bash
# Install dependencies
pip install -r requirements.txt

# Run the baseline (outputs predictions_baseline.csv by default)
python baseline_3sigma.py --data data

# The repository ships with predictions.csv already generated
# To regenerate predictions.csv directly:
python baseline_3sigma.py --data data --out predictions.csv

# Validate the output
python validate_submission.py predictions.csv
```

### Validation Result

```
predictions.csv: OK
  15 ranked gateways for each of 8 weeks, 2026-02-02 to 2026-03-23
```

- **Output:** Exactly 120 rows — 15 gateways × 8 weeks ✅
- **Columns:** `week_start`, `rank`, `gateway_id`, `score`, `reason` ✅
- **Constraints:** Ranks 1–15 per week, no duplicates, valid non-empty reasons under character limit ✅

---

## Part 2 — Software Development

Software Development — Build a web API to provide weekly top-15 gateway rankings, explain why a gateway was selected, and rerun the ranking when new telemetry data arrives.

### Web API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check — confirms the service is operational |
| `GET` | `/rankings?week=YYYY-MM-DD` | Retrieve top 15 ranked gateways for a given week Monday |
| `GET` | `/rankings?week=YYYY-MM-DD&limit=N` | Retrieve top $N$ ranked gateways ($1 \le N \le 100$) |
| `GET` | `/rankings?week=YYYY-MM-DD&strategy=three_sigma` | Retrieve rankings using a specified algorithm |
| `GET` | `/rankings/weeks` | List all 8 valid scored Mondays |
| `GET` | `/gateways/{gateway_id}?week=YYYY-MM-DD` | Diagnostic explanation: 28-day baseline, 7-day stats, breach counts |
| `POST` | `/rankings/run` | Reload telemetry from disk and refresh in-memory cache without restart |
| `GET` | `/strategies` | List registered ranking strategy algorithms |
| `GET` | `/docs` | Interactive Swagger OpenAPI documentation and testing sandbox |

### Architecture

```
src/
├── main.py              ← FastAPI application entry point & health check
├── config.py            ← Data directory path configuration (DATA_DIR support)
├── ranking/
│   ├── base.py          ← Abstract RankingStrategy interface (Strategy pattern)
│   ├── three_sigma.py   ← Concrete ThreeSigmaRanker implementation
│   └── registry.py      ← Strategy registry (swap rankers without editing routes)
├── services/
│   └── ranking_service.py  ← Business logic layer (caching, data loading, diagnostics)
└── api/
    ├── models.py        ← Pydantic request/response schemas
    └── routes.py        ← Thin FastAPI route handlers with error mapping
```

**Replaceable Strategy Architecture:**
The API layer depends strictly on the `RankingStrategy` abstraction (`src/ranking/base.py`). Introducing a new ranking strategy (e.g., machine learning or gradient boosted trees) only requires creating a subclass and registering it in `src/ranking/registry.py`. No changes to API routes or handlers are needed.

### How to Run the API

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server (default data directory: data/)
uvicorn src.main:app --reload

# Start with a custom data directory:
# On Windows PowerShell:
$env:DATA_DIR="C:\path\to\data"; uvicorn src.main:app --reload
# On Linux / macOS / Git Bash:
DATA_DIR=/path/to/data uvicorn src.main:app --reload
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.

### Example API Calls

```bash
# 1. Health check
curl http://localhost:8000/

# 2. Get top 15 recommendations for a week
curl "http://localhost:8000/rankings?week=2026-02-02"

# 3. Get top 5 recommendations
curl "http://localhost:8000/rankings?week=2026-02-02&limit=5"

# 4. Request rankings using a specific strategy
curl "http://localhost:8000/rankings?week=2026-02-02&strategy=three_sigma"

# 5. Explain why a gateway was selected (diagnostic breakdown)
curl "http://localhost:8000/gateways/0A2778A31BE3?week=2026-02-02"

# 6. Re-run ranking pipeline when new telemetry arrives (no process restart)
curl -X POST http://localhost:8000/rankings/run

# 7. List available scored Mondays
curl http://localhost:8000/rankings/weeks

# 8. List registered ranking strategies
curl http://localhost:8000/strategies
```

### Error Handling

The API implements strict input validation and returns clear, structured HTTP responses:

| HTTP Status | Condition | Example Request |
|---|---|---|
| `400 Bad Request` | Invalid date format | `GET /rankings?week=not-a-date` |
| `400 Bad Request` | Week out of range or no telemetry | `GET /rankings?week=2020-01-06` |
| `400 Bad Request` | Unknown ranking strategy | `GET /rankings?week=2026-02-02&strategy=unknown_algo` |
| `404 Not Found` | Gateway ID not found in dataset | `GET /gateways/FFFFFFFFFFFF?week=2026-02-02` |
| `503 Service Unavailable` | Telemetry directory missing or unreadable | When `DATA_DIR/telemetry` is not found on disk |
| `500 Internal Server Error` | Unhandled pipeline exception | Unexpected file format or system failure |

### New Data Without Process Restart (Live Session Scenario)

The application fully supports dropping new telemetry Parquet files into `data/telemetry/` while the service is running:

1. The service boots and caches current telemetry in memory.
2. New telemetry files (e.g., an unseen evaluation month) are added to `data/telemetry/`.
3. Calling `POST /rankings/run` invalidates the cached DataFrame, reads all files from disk, and reports updated row and gateway counts.
4. Subsequent calls to `GET /rankings?week=YYYY-MM-DD` immediately utilize the newly ingested telemetry data.
5. The system accommodates newly appearing gateway IDs as well as quiet/inactive gateways without crashing.

This capability is verified by end-to-end tests in `tests/test_new_data.py`.

### Memory & Data Handling

- **Selective Column Loading:** Only the necessary columns (`gateway_id`, `ts_utc`, `offline_duration_sec`, `disconnection_cnt`, `reboot_cnt`) are loaded from Parquet, keeping memory usage minimal.
- **Single In-Memory Copy:** A single cached DataFrame serves read requests without redundant copying.
- **Laptop-Friendly:** Designed to run comfortably within standard 8–16 GB RAM developer machines.

### How to Run Tests

```bash
# Run the complete test suite
pytest -v
```

The test suite contains **63 automated tests** using isolated synthetic fixtures (runs 100% offline with zero external data or network calls required):
- `tests/test_ranking.py` — unit tests for ranking logic and baseline conformity
- `tests/test_service.py` — service layer caching, data orchestration, and exception handling
- `tests/test_api.py` — API endpoints, query parameters, error status codes, and offline Swagger UI regression tests
- `tests/test_e2e.py` — full pipeline integration and regression tests (including `std = 0` edge-case handling)
- `tests/test_new_data.py` — live new-data-without-restart tests with temporary disk Parquet fixtures

---

## Repository Structure

```
LPDG-Innovation-Hub/
├── README.md                  ← Comprehensive project documentation
├── DECISIONS.md               ← 5 engineering decisions, limitations, and future roadmap
├── AI-USAGE.md                ← Transparent AI tool usage disclosure and corrections
├── requirements.txt           ← Pinned Python dependencies
├── .gitignore                 ← Excludes data/, .venv/, cache, and .env
├── 23091A05T2.pdf             ← Participant resume (Registration ID: 23091A05T2)
│
├── predictions.csv            ← Official Part 1 submission output (120 rows)
├── baseline_3sigma.py         ← Challenge-provided baseline script (unmodified)
├── validate_submission.py     ← Challenge-provided validator script
│
├── src/                       ← Part 2 Software Development source code
│   ├── main.py                ← FastAPI entry point (offline /docs & local static mount)
│   ├── config.py              ← Environment configuration & paths (DATA_DIR support)
│   ├── static/                ← Bundled local Swagger UI assets (100% offline operation)
│   │   ├── swagger-ui-bundle.js
│   │   ├── swagger-ui.css
│   │   └── favicon.png
│   ├── ranking/               ← Ranking strategies & registry
│   │   ├── base.py            ← Strategy abstract interface
│   │   ├── three_sigma.py     ← 3-sigma ranker implementation
│   │   └── registry.py        ← Algorithm registry
│   ├── services/
│   │   └── ranking_service.py ← Service layer: caching, loading, diagnostics
│   └── api/
│       ├── models.py          ← Pydantic schemas
│       └── routes.py          ← Route handlers with error handling
│
├── tests/                     ← Automated test suite (63 tests)
│   ├── conftest.py            ← Synthetic test data fixtures
│   ├── test_ranking.py        ← Algorithm unit tests
│   ├── test_service.py        ← Service unit tests
│   ├── test_api.py            ← Route, error handling, and offline docs regression tests
│   ├── test_e2e.py            ← End-to-end and regression tests
│   └── test_new_data.py       ← New-data-without-restart tests
│
└── docs/
    ├── RECORDING_SCRIPT.md    ← Video demonstration script
    └── FINAL_CHECKLIST.md     ← Pre-submission verification checklist
```

---

## Limitations

1. **Anomaly Detection Scope:** The current implementation uses the 3-sigma anomaly baseline; it detects sudden statistical spikes in offline duration, reboots, and disconnections, but does not capture gradual linear degradation.
2. **Synchronous Reranking:** `POST /rankings/run` executes synchronously. For the challenge dataset (~1.4M rows), it completes in under 30 seconds on a laptop, but enterprise-scale datasets would benefit from an asynchronous job queue (e.g., Celery/Redis).
3. **Manual Trigger for Reload:** Telemetry reload is triggered via `POST /rankings/run`; automated filesystem event polling is not running in the background.
4. **Internal Operational Tool:** No authentication or rate limiting is enabled; intended strictly for trusted internal dispatch environments.

---

## What Another Two Weeks Would Improve

1. **Supervised ML Model:** Train an XGBoost or LightGBM model utilizing `engineer_review_2026-02-15.xlsx` expert labels with strict temporal validation against the business cost function.
2. **Multi-Metric Composite Scoring:** Incorporate supplementary signals (`reboot_importance`, `no_conn_importance`) into ranking tie-breaking.
3. **Automated Filesystem Watcher:** Ingest new Parquet partitions automatically via a background watcher daemon.
4. **Embedded Results Store:** Cache precomputed weekly rankings in DuckDB or SQLite for zero-latency retrieval.
5. **Security & Authentication:** Add lightweight API key authentication and CORS configuration.

---

## Participant & Submission Information

- **Registration ID:** `23091A05T2`
- **Official Email:** `23091a05t2@rgmcet.edu.in`
- **Resume File:** [`23091A05T2.pdf`](./23091A05T2.pdf) (located at repository root)
- **Online Resume:** [View Resume](https://portfolio-azure-theta-94.vercel.app/Siva_Resume_SDE_1%20(1).pdf)
- **Submission Form:** [Google Form](https://forms.gle/qHZqsrRPGWf8ja5S6)
- **Submission Deadline:** **Wednesday, 16 September 2026, 20:00 IST**
- **Evaluation:** **18 September 2026, 9:30 AM onwards at RGMCET campus** (venue arrival by 9:00 AM)
- **GitHub Repository Visibility:** Must be set to **PUBLIC** prior to form submission.
- **Dataset Policy:** The raw `data/` directory is not committed (see `.gitignore`).

---

*Challenge: LPDG Innovation Hub Selection Challenge 2026*  
*Track: Software Development*  
*Candidate: 23091A05T2*