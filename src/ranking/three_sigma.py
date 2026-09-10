"""
ThreeSigmaRanker — concrete implementation of RankingStrategy
==============================================================

This wraps the algorithm from the challenge-provided `baseline_3sigma.py`.

Why wrap instead of duplicate?
    - `baseline_3sigma.py` is the challenge-provided file. We keep it
      completely intact (a rule from the challenge brief).
    - We import its core functions rather than copy-pasting them.
    - This means any bugfix to the baseline is automatically picked up here.

Algorithm (from the baseline docstring):
    For a given Monday:
    1. Take the trailing 28 days of telemetry, strictly before that Monday.
    2. Per gateway, compute mean and std of offline_duration_sec,
       disconnection_cnt, and reboot_cnt.
    3. Flag any hour in the trailing 7 days where any metric exceeds the
       gateway's own mean by more than 3 standard deviations.
    4. Rank gateways by flagged-hour count (descending).
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from src.ranking.base import RankingStrategy

# Import the core ranking function from the provided baseline.
# We do NOT copy-paste the logic — we reuse it directly.
# baseline_3sigma.rank_week is a pure function: (DataFrame, date) -> DataFrame
# It returns columns: gateway_id, flagged_hours, worst_metric
import sys
import pathlib

# Ensure the project root is on sys.path so `import baseline_3sigma` works
# regardless of where uvicorn is launched from.
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from baseline_3sigma import rank_week as _baseline_rank_week  # noqa: E402

VISITS_PER_WEEK = 15
_MAX_REASON_CHARS = 300


def _build_reason(flagged_hours: int, worst_metric: str) -> str:
    """Build the human-readable reason string.

    Matches the format used by the baseline so predictions.csv and the
    API give identical explanations for the same data.
    """
    metric = worst_metric or "no metric over 3 sigma"
    reason = (
        f"{flagged_hours} hour(s) beyond 3 sigma of this gateway's own "
        f"28-day baseline in the last 7 days; first breach on {metric}"
    )
    # Truncate just in case (validate_submission.py enforces 300 chars)
    return reason[:_MAX_REASON_CHARS]


class ThreeSigmaRanker(RankingStrategy):
    """Gateway ranker using the 3-sigma anomaly detection method.

    This is the default (and currently only) ranking strategy. It
    delegates to the core algorithm in baseline_3sigma.py.

    To add another ranker, create a new class inheriting from
    RankingStrategy in this directory and register it in registry.py.
    """

    def rank_week(self, frame: pd.DataFrame, monday: dt.date) -> pd.DataFrame:
        """Return ranked gateways for the week starting `monday`.

        Args:
            frame:  Full telemetry DataFrame.
            monday: The Monday (UTC date) that starts the scored week.

        Returns:
            DataFrame with columns: gateway_id, rank, score, reason
            Ordered by rank ascending (1 = most anomalous).

        Raises:
            ValueError: if the window contains no usable data.
        """
        # Delegate to the baseline's pure function
        ranked = _baseline_rank_week(frame, monday)

        if ranked.empty:
            raise ValueError(
                f"No telemetry data available for the 28-day window before {monday}. "
                "Cannot produce rankings."
            )

        # The baseline returns as many gateways as it can find.
        # We take the top VISITS_PER_WEEK and assign ranks.
        top = ranked.head(VISITS_PER_WEEK).reset_index(drop=True)

        result_rows = []
        for rank_idx, row in enumerate(top.itertuples(index=False), start=1):
            result_rows.append(
                {
                    "gateway_id": row.gateway_id,
                    "rank": rank_idx,
                    "score": float(row.flagged_hours),
                    "reason": _build_reason(int(row.flagged_hours), row.worst_metric),
                }
            )

        result = pd.DataFrame(result_rows)
        return result
