# LPDG Innovation Hub Selection Challenge 2026

## Challenge Overview

The LPDG operations team can perform a maximum of **15 field visits per week**. The goal is to build a system that ranks gateways based on their telemetry behaviour and recommends the 15 highest-priority gateways to visit each week, with a human-readable reason for each recommendation.

The challenge has two parts:

| Part | Description | Weight |
|---|---|---|
| **Part 1** | Gateway ranking: produce `predictions.csv` with 15 gateways × 8 weeks | 40% |
| **Part 2** | Selected technical area: **Software Development** | 60% |

---

## Part 1 — Gateway Ranking

### Approach

Part 1 uses the **provided 3-sigma baseline** (`baseline_3sigma.py`) unchanged. For each scored Monday, it:

1. Takes the trailing 28 days of telemetry for each gateway
2. Computes the mean and standard deviation of `offline_duration_sec`, `disconnection_cnt`, and `reboot_cnt`
3. Flags any hour in the trailing 7 days where any metric exceeds 3 standard deviations above that gateway's own baseline
4. Ranks gateways by flagged-hour count and selects the top 15

The baseline was selected for Part 1 because:
- The challenge permits it for Software Development candidates
- It is transparent, explainable, and reproducible
- The focus of this submission is Part 2 (see `DECISIONS.md` — Decision 2)

### Scored Weeks

Weeks 1–8: `2026-02-02` to `2026-03-23` (consecutive Mondays)

### Input Data

Data must be placed in the `data/` directory at the project root (not committed to git):

```
data/
├── telemetry/          ← Parquet partitioned dataset (required)
├── gateway_master.csv  ← Gateway metadata
├── field_visits.csv    ← Historical visits
└── ...
```

The `data/` directory is intentionally excluded from version control (see `.gitignore`). A reviewer must supply it separately.

### How to Run Part 1

```bash
# Install dependencies
pip install -r requirements.txt

# Run the baseline (outputs predictions_baseline.csv by default)
python baseline_3sigma.py --data data

# The repository ships with predictions.csv already generated
# If you want to regenerate it:
python baseline_3sigma.py --data data --out predictions.csv

# Validate the output
python validate_submission.py predictions.csv
```

### Validation Result

```
predictions.csv: OK
  15 ranked gateways for each of 8 weeks, 2026-02-02 to 2026-03-23
```

**Output:** 120 rows — 15 gateways × 8 weeks ✅

---

## Part 2 — Software Development

A simple, offline-capable Web API that lets an operations team query the gateway ranking system.

### What the API Does

| Endpoint | Description |
|---|---|
| `GET /rankings?week=YYYY-MM-DD` | Get the 15 recommended gateways for a given week |
| `GET /gateways/{gateway_id}?week=YYYY-MM-DD` | Get the rank and explanation for a specific gateway |
| `POST /rankings/run` | Re-run the ranking pipeline (e.g., after new data arrives) |
| `GET /rankings/weeks` | List all valid scored Mondays |
| `GET /strategies` | List available ranking algorithms |

### Architecture

```
src/
├── main.py              ← FastAPI application entry point
├── config.py            ← Data directory configuration
├── ranking/
│   ├── base.py          ← RankingStrategy abstract interface
│   ├── three_sigma.py   ← ThreeSigmaRanker implementation
│   └── registry.py      ← Strategy registry (swap rankers without editing routes)
├── services/
│   └── ranking_service.py  ← Business logic layer
└── api/
    ├── models.py        ← Pydantic request/response schemas
    └── routes.py        ← FastAPI route handlers (thin — no business logic)
```

**Key design principle:** The API routes depend on the `RankingStrategy` interface, not the concrete implementation. Adding a new ranking algorithm requires only creating a new class — no changes to routes.

### How to Run the API

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API (uses data/ by default)
uvicorn src.main:app --reload

# Use a different data directory
DATA_DIR=/path/to/other/data uvicorn src.main:app --reload

# API docs available at:
# http://127.0.0.1:8000/docs
```

### Example API Calls

```bash
# Get week's 15 recommendations
curl http://localhost:8000/rankings?week=2026-02-02

# Explain a gateway's ranking (why is it at rank 1?)
curl http://localhost:8000/gateways/0A2778A31BE3?week=2026-02-02

# Run the ranking pipeline again (picks up new data from disk without restart)
curl -X POST http://localhost:8000/rankings/run

# List all valid scored weeks
curl http://localhost:8000/rankings/weeks

# List available ranking strategies
curl http://localhost:8000/strategies
```

### How to Run Tests

```bash
pytest tests/ -v
```

This runs **59 tests** (no real dataset required):
- `test_ranking.py` — ranking algorithm unit tests
- `test_service.py` — service layer unit tests
- `test_api.py` — all API endpoint tests
- `test_e2e.py` — end-to-end pipeline tests and regression tests
- `test_new_data.py` — new-data-without-restart tests (writes real parquet to disk)

### Alternate Data Directory

```bash
# CLI approach (baseline script)
python baseline_3sigma.py --data /other/path

# API approach (environment variable)
DATA_DIR=/other/path uvicorn src.main:app --reload
```

---

## Project Structure

```
LPDG-Innovation-Hub/
├── README.md                  ← This file
├── DECISIONS.md               ← 5 engineering decisions
├── AI-USAGE.md                ← AI tool usage disclosure
├── requirements.txt           ← Python dependencies
├── .gitignore                 ← data/ excluded
├── 23091A05T2.pdf             ← Participant resume (Registration ID: 23091A05T2)
│
├── predictions.csv            ← Part 1 output (120 rows)
├── baseline_3sigma.py         ← Challenge-provided baseline (unchanged)
├── validate_submission.py     ← Challenge-provided validator (unchanged)
│
├── src/                       ← Part 2 Software Development source
│   ├── main.py
│   ├── config.py
│   ├── ranking/
│   ├── services/
│   └── api/
│
├── tests/                     ← Test suite (59 tests)
│
└── docs/
    ├── RECORDING_SCRIPT.md
    └── FINAL_CHECKLIST.md
```

---

## Limitations

- The ranking algorithm is the provided 3-sigma baseline; no ML improvement was made
- `POST /rankings/run` is synchronous — on very large datasets it may take up to 60 seconds
- The API does not auto-detect new data files; `POST /rankings/run` must be called manually after new data arrives
- No authentication — intended as an internal operations tool only

## New-Data-Without-Restart (Live Session Scenario)

The API supports picking up new telemetry data **without restarting the process**:

```bash
# 1. Start the API
uvicorn src.main:app --reload

# 2. Keep it running — add a new parquet file to data/telemetry/
#    (e.g., the unseen month from the live session)

# 3. Call /run — no restart required
curl -X POST http://localhost:8000/rankings/run
# Response: { "status": "success", "rows_loaded": ..., "gateways_count": ... }

# 4. Query the updated rankings
curl http://localhost:8000/rankings?week=2026-04-06
```

This is tested in `tests/test_new_data.py` with real parquet I/O.

## What Another Two Weeks of Work Could Improve

1. **Improved ranking algorithm:** A gradient boosting or LSTM model trained on the `engineer_review_2026-02.xlsx` expert labels, with proper temporal cross-validation
2. **Weighted multi-metric scoring:** Combine `reboot_importance` and `no_conn_importance` fields from the dataset as supplementary signals
3. **File-system watcher:** Auto-trigger reranking when new parquet files appear in `data/telemetry/`
4. **Authentication:** Simple API key middleware to control access
5. **Caching layer:** Cache ranking results per week to avoid re-running for identical data

---

## Resume

**Registration ID:** 23091A05T2

Resume file: [`23091A05T2.pdf`](./23091A05T2.pdf) (included in repository root as required by participant instructions)

Online resume: [View Resume](https://portfolio-azure-theta-94.vercel.app/Siva_Resume_SDE_1%20(1).pdf)

---

## Submission Notes

- **Deadline:** Wednesday, 16 September 2026, 20:59 IST
- **Submission:** via official Google Form (to be completed manually)
- **Repository must be PUBLIC** before submitting the Google Form
- **Registration ID:** 23091A05T2
- **Resume:** `23091A05T2.pdf` in repository root ✅
- **Dataset:** not committed (see `.gitignore`) ✅
- **Recording:** `[Add final 6–8 minute recording link before submission]`
- See `docs/RECORDING_SCRIPT.md` for the demo script and `docs/FINAL_CHECKLIST.md` for the pre-submission checklist

---

*Challenge: LPDG Innovation Hub Selection Challenge 2026*  
*Part 2 track: Software Development*  
*Registration ID: 23091A05T2*