# Engineering Decisions — LPDG Innovation Hub Selection Challenge 2026

This document records the key engineering decisions made during development, the alternatives considered, and the reasoning behind each choice.

---

## Decision 1: Use the Provided 3-Sigma Baseline for Part 1

**Decision:** The provided `baseline_3sigma.py` is used unchanged to generate `predictions.csv` for Part 1. No custom ranking algorithm was developed for Part 1.

**Alternatives considered:**
- Developing a custom ML model (e.g., gradient boosting, anomaly detection neural network)
- Building a weighted composite score using additional telemetry columns (e.g., `reboot_importance`, `no_conn_importance`)
- Using the `engineer_review_2026-02-15.xlsx` expert audit file as supplementary signal

**Why the baseline was chosen:**
The challenge brief explicitly states that Software Development, DevOps, and Data Engineering candidates are *permitted to use `baseline_3sigma.py` unchanged* for Part 1 and focus their energy on Part 2. The baseline is described as "close to what our production notificator actually does" — it is not a toy; it is the operational bar. Attempting to improve it without a rigorous ML evaluation framework (temporal validation, leakage checks, business cost model calibration) would risk over-engineering Part 1 at the expense of Part 2 quality. Given the 60% weight on Part 2, the correct trade-off is a clean, correct baseline for Part 1 and a well-engineered Software Development solution for Part 2.

**Trade-offs:**
- The baseline may miss gateways that have subtler patterns (e.g., gradual CPU degradation). A ML model could potentially detect these.
- However, the baseline is transparent, explainable, and reproducible — properties that are valuable for an operational dispatcher who needs to understand why a visit was recommended.

---

## Decision 2: Select Software Development as the Part 2 Technical Track

**Decision:** Software Development was selected as the Part 2 track over Data Engineering, DevOps, Data Science, Machine Learning, and MLOps.

**Alternatives considered:**
- **Data Engineering:** Strong fit for building a robust ETL pipeline; however, the data is already provided in a clean Parquet format, limiting the scope of interesting pipeline challenges.
- **Machine Learning:** Would require outperforming the baseline on the cost model, which demands rigorous temporal validation and is high-risk without a clear performance advantage.
- **DevOps:** Valuable, but containerisation and CI/CD are infrastructure concerns that don't directly serve the operational use case.

**Why Software Development was chosen:**
The core problem is an operational tool that a dispatcher uses every Monday. A clean, well-tested Web API is the most natural and practical solution — it directly serves the business need (query this week's gateways, ask why a gateway is ranked where it is, trigger a rerun when new data arrives). This track allows demonstrating clean code architecture (abstraction, separation of concerns, testability) while delivering something genuinely useful. The live session requirement — "drop in a new month of data and run it" — aligns perfectly with an API that accepts a `--data` override.

**Trade-offs:**
- Does not improve ranking accuracy beyond the baseline.
- Requires more upfront architectural work (service layer, abstraction, API design) compared to a simpler script.

---

## Decision 3: Ranking Logic Placed Behind an Abstract Interface

**Decision:** The ranking algorithm is defined as an Abstract Base Class (`RankingStrategy`) with a concrete `ThreeSigmaRanker` implementation. The FastAPI routes depend only on the abstract interface, not the concrete class.

**Alternatives considered:**
- Placing the ranking logic directly inside the service layer
- Using a simple function rather than a class hierarchy
- Using Python `Protocol` (structural subtyping) instead of `ABC`

**Why an ABC was chosen:**
The challenge explicitly requires that "adding another ranking implementation should not require editing the API handler." An ABC enforces this contract at the class level — any new ranker must implement the required methods, and the existing API code need not change. This is the classic Strategy pattern. `ABC` was preferred over `Protocol` because it gives explicit enforcement (calling an unimplemented method raises `NotImplementedError`) and is more familiar to developers coming from Java/C# backgrounds, making the intent clearer.

**Trade-offs:**
- Adds a small amount of indirection compared to calling the function directly.
- The `ThreeSigmaRanker` is effectively a thin wrapper around the baseline logic, but this wrapper cost is justified by the architectural benefit.

---

## Decision 4: "Run Again" Implemented as Synchronous HTTP POST

**Decision:** `POST /rankings/run` re-runs the full ranking pipeline synchronously and returns the results immediately.

**Alternatives considered:**
- **Async job queue (Celery + Redis):** The "gold standard" for long-running jobs in production, but far over-engineered for this use case.
- **Background task in FastAPI:** FastAPI supports background tasks, but this would require polling for results, adding complexity with no benefit.
- **File-system watcher:** Automatically trigger a rerun when files appear in `data/`. Clever, but adds a daemon process and makes testing harder.

**Why synchronous was chosen:**
The challenge explicitly says "the expected workload is small." The full pipeline processes ~1.4M rows and completes in under 30 seconds on a normal laptop. A synchronous POST is the simplest design that satisfies the requirement. It is easy to test, easy to understand, and easy to demonstrate in the live session (one HTTP request, one response). If the system scaled to millions of gateways or needed to run continuously, an async queue would be justified — but that is out of scope for this challenge.

**Trade-offs:**
- A slow network client (e.g., 60 second timeout) could drop the connection before the pipeline completes if the data directory is very large. This is an acceptable limitation documented under "Limitations" in the README.

---

## Decision 5: Data is Loaded from the Filesystem, Not Uploaded via HTTP

**Decision:** The API reads telemetry data from a local `data/` directory (configurable via environment variable or startup flag). Users do not upload data through HTTP.

**Alternatives considered:**
- HTTP file upload endpoint where a user posts a Parquet file
- Reading data from a cloud object store (S3, GCS)
- Accepting data as a JSON payload in the request body

**Why filesystem was chosen:**
The challenge brief specifies that "new data will be placed in the mounted `data/` directory." This is explicitly the data delivery mechanism. The challenge also requires offline execution with no internet dependency. Therefore, the design must assume data arrives via filesystem, not network. An HTTP upload would add complexity (multipart form handling, server-side storage) without matching the described operational workflow. The `--data` flag (and `DATA_DIR` environment variable) allows a reviewer to point the application at any directory on their machine without modifying code.

**Trade-offs:**
- The service must be restarted (or `POST /rankings/run` must be called) after new data arrives — it does not auto-detect new files. This is a known and acceptable limitation for a v1 internal tool.

---

*Last updated: 2026-09-11*
