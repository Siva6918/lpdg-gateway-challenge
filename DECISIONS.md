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
The core problem is an operational tool that a dispatcher uses every Monday. A clean, well-tested Web API is the most natural and practical solution — it directly serves the business need (query this week's gateways, ask why a gateway is ranked where it is, trigger a rerun when new data arrives). This track allows demonstrating clean code architecture (abstraction, separation of concerns, testability) while delivering something genuinely useful. The live session requirement — "drop in a new month of data and run it" — aligns directly with the filesystem-based design and configurable `DATA_DIR`, allowing the reviewer to point the application to the appropriate data directory without modifying the ranking code.

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
The challenge explicitly requires that "adding another ranking implementation should not require editing the API handler." An ABC enforces this contract at the class level — any new ranker must implement the required methods, and the existing API code need not change. This is the classic Strategy pattern. `ABC` was preferred over `Protocol` because it provides explicit enforcement at the class level: a concrete ranking strategy must implement the required abstract methods before it can be instantiated (instantiating an incomplete subclass raises `TypeError`). It also makes the intended Strategy pattern clear and is familiar to developers coming from Java/C# backgrounds.

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

**Decision:** The API reads telemetry data from a local `data/` directory (configurable via the `DATA_DIR` environment variable). Users do not upload data through HTTP.

**Alternatives considered:**
- HTTP file upload endpoint where a user posts a Parquet file
- Reading data from a cloud object store (S3, GCS)
- Accepting data as a JSON payload in the request body

**Why filesystem was chosen:**
The challenge brief specifies that "new data will be placed in the mounted `data/` directory." This is explicitly the data delivery mechanism. The challenge also requires offline execution with no internet dependency. Therefore, the design must assume data arrives via filesystem, not network. An HTTP upload would add complexity (multipart form handling, server-side storage) without matching the described operational workflow. The configurable `DATA_DIR` environment variable (defaulting to `./data`) allows a reviewer to point the application at any directory on their machine without modifying code.

**Trade-offs:**
- The service does not automatically detect new files. After new data arrives, the operator must explicitly trigger `POST /rankings/run` to reload the data and recompute the rankings. A process restart is not required.

---

## Decision 6: Deterministic Tie-Breaking and Strict Telemetry Validation

**Decision:** When gateways have identical anomaly scores, ties are resolved deterministically using `gateway_id` ascending. In addition, invalid or missing telemetry triggers explicit typed errors rather than silent failure or synthetic ranking generation.

**Alternatives considered:**
- Leaving tie resolution to internal DataFrame/library grouping order
- Using arbitrary or random tie-breaking
- Silently filling missing windows with zero-score default rankings

**Why deterministic tie-breaking and strict validation were chosen:**
Field-visit dispatching requires absolute reproducibility and accountability. A dispatcher querying rankings on Monday morning must receive the exact same 15 recommended gateways regardless of row ordering in the underlying Parquet files or library sort stability. Secondary sorting by `gateway_id` guarantees bit-for-bit determinism across all environments.
Furthermore, the service deliberately distinguishes between missing storage directories (`DataNotFoundError`), corrupt or empty datasets (`CorruptDataError`), and datasets lacking records for the specific evaluation window (`NoDataInWindowError`). Silently manufacturing empty or default rankings from corrupt inputs would obscure upstream telemetry failures.

**Trade-offs:**
- Requires secondary key evaluation during sorting (negligible runtime overhead).
- Calls with corrupted or missing data fail immediately with clear HTTP status codes (400/422/503) rather than returning partial guesses.

---

## System Limitations — "What It Cannot Do"

1. **Subtle Degradation Detection:** The ranking algorithm is the provided 3-sigma anomaly detector. It cannot detect gradual, non-spiking degradation (e.g., progressive memory leaks or slow signal loss) where telemetry drifts slowly without breaching 3 standard deviations from its own rolling mean.
2. **Autonomous Background Polling:** The API does not run an active filesystem watcher daemon; it will not autonomously detect new Parquet files placed in `data/telemetry/`. The operator or upstream orchestration must explicitly trigger `POST /rankings/run` to reload telemetry from disk without restarting the process.
3. **Multi-User Authentication & Rate Limiting:** The API is unauthenticated and without rate limits, designed strictly as a lightweight, local/internal operations tool for the gateway dispatch team.
4. **Asynchronous Long-Running Job Queue:** Reranking via `POST /rankings/run` runs synchronously. While it finishes in under 30 seconds for 1.4M rows on standard laptop hardware, scaling to hundreds of millions of rows would require an asynchronous worker queue (e.g., Celery/Redis).

---

## What Another Two Weeks of Work Would Improve

If allocated an additional two weeks of development time and access to subsequent operational data, the following enhancements would be prioritized:

1. **Supervised ML Model Calibration:** Investigate a supervised ML approach using the available engineer-review signals, with temporal validation and calibration against the challenge business cost model (weighing field visit costs against failure penalties). Candidate models could include XGBoost or LightGBM.
2. **Multi-Metric Weighted Scoring:** Incorporate supplementary signals from the dataset (such as `reboot_importance`, `no_conn_importance`, and signal strength metrics) to refine priority ordering when breach counts tie.
3. **Filesystem Watcher / Ingestion Webhook:** Implement an automated file-system watcher (e.g. `watchdog`) or ingestion webhook to trigger cache invalidation and reranking automatically as soon as a new Parquet partition lands in `data/telemetry/`.
4. **Persistent Result Caching & Storage:** After establishing correctness, persistent caching in an embedded database (e.g., SQLite or DuckDB) could reduce repeated computation for previously processed weeks while still allowing explicit invalidation when new telemetry arrives.
5. **Role-Based Access & Security:** Add lightweight API key authentication and CORS configuration to secure the dispatch API in enterprise deployments.

---

*Last updated: 2026-09-17*
