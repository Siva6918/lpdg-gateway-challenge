"""
tests/test_ranking.py — Unit tests for the ranking abstraction and ThreeSigmaRanker.

These tests verify:
  A. The RankingStrategy ABC correctly refuses instantiation without rank_week
  B. ThreeSigmaRanker implements the interface
  C. ThreeSigmaRanker produces correct output columns
  D. The most anomalous gateway gets rank 1
  E. Scores are non-negative floats
  F. Reasons are non-empty strings under 300 characters
  G. Registry returns the right class
  H. Registry raises KeyError for unknown strategy names
"""

from __future__ import annotations

import datetime as dt
import pytest
import pandas as pd

from tests.conftest import MONDAY, GATEWAY_ANOMALOUS, GATEWAY_NORMAL
from src.ranking.base import RankingStrategy
from src.ranking.three_sigma import ThreeSigmaRanker
from src.ranking.registry import get_ranker, available_strategies


# ---------------------------------------------------------------------------
# A. Abstract base class cannot be instantiated directly
# ---------------------------------------------------------------------------
class TestRankingStrategyABC:
    def test_cannot_instantiate_abc_directly(self):
        """RankingStrategy is abstract — instantiating it must raise TypeError."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            RankingStrategy()  # type: ignore[abstract]

    def test_subclass_without_rank_week_cannot_be_instantiated(self):
        """A subclass that forgets to implement rank_week must also fail."""
        class IncompleteRanker(RankingStrategy):
            pass  # deliberately missing rank_week

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteRanker()  # type: ignore[abstract]

    def test_subclass_with_rank_week_can_be_instantiated(self):
        """A complete concrete subclass must be instantiable."""
        class MinimalRanker(RankingStrategy):
            def rank_week(self, frame: pd.DataFrame, monday: dt.date) -> pd.DataFrame:
                return pd.DataFrame()

        ranker = MinimalRanker()
        assert ranker is not None


# ---------------------------------------------------------------------------
# B. ThreeSigmaRanker: interface compliance
# ---------------------------------------------------------------------------
class TestThreeSigmaRankerInterface:
    def test_is_a_ranking_strategy(self):
        """ThreeSigmaRanker must be an instance of RankingStrategy."""
        ranker = ThreeSigmaRanker()
        assert isinstance(ranker, RankingStrategy)

    def test_has_rank_week_method(self):
        """rank_week must be callable."""
        ranker = ThreeSigmaRanker()
        assert callable(ranker.rank_week)


# ---------------------------------------------------------------------------
# C. ThreeSigmaRanker: output columns
# ---------------------------------------------------------------------------
class TestThreeSigmaRankerOutput:
    def test_returns_required_columns(self, minimal_frame: pd.DataFrame):
        """rank_week must return exactly: gateway_id, rank, score, reason."""
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        required = {"gateway_id", "rank", "score", "reason"}
        assert required.issubset(set(result.columns)), (
            f"Missing columns: {required - set(result.columns)}"
        )

    def test_returns_dataframe(self, minimal_frame: pd.DataFrame):
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        assert isinstance(result, pd.DataFrame)

    def test_rank_column_is_integer(self, minimal_frame: pd.DataFrame):
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        assert pd.api.types.is_integer_dtype(result["rank"]), (
            "rank column must be integer"
        )

    def test_score_column_is_numeric(self, minimal_frame: pd.DataFrame):
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        assert pd.api.types.is_numeric_dtype(result["score"]), (
            "score column must be numeric"
        )

    def test_reasons_are_non_empty_strings(self, minimal_frame: pd.DataFrame):
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        for _, row in result.iterrows():
            assert isinstance(row["reason"], str), "reason must be a string"
            assert len(row["reason"].strip()) > 0, "reason must not be empty"

    def test_reasons_under_300_chars(self, minimal_frame: pd.DataFrame):
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        too_long = result[result["reason"].str.len() > 300]
        assert too_long.empty, (
            f"{len(too_long)} reason(s) exceed 300 characters"
        )


# ---------------------------------------------------------------------------
# D. ThreeSigmaRanker: correct ordering
# ---------------------------------------------------------------------------
class TestThreeSigmaRankerOrdering:
    def test_anomalous_gateway_gets_rank_1(self, minimal_frame: pd.DataFrame):
        """The gateway with the most anomalous hours must be ranked first."""
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        rank_1_gw = result[result["rank"] == 1]["gateway_id"].iloc[0]
        assert rank_1_gw == GATEWAY_ANOMALOUS, (
            f"Expected {GATEWAY_ANOMALOUS} at rank 1, got {rank_1_gw}"
        )

    def test_ranks_are_sequential_from_1(self, minimal_frame: pd.DataFrame):
        """Ranks must be 1, 2, 3, ... with no gaps or repeats."""
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        ranks = sorted(result["rank"].tolist())
        expected = list(range(1, len(result) + 1))
        assert ranks == expected, f"Expected ranks {expected}, got {ranks}"

    def test_scores_non_negative(self, minimal_frame: pd.DataFrame):
        """All scores (flagged hour counts) must be >= 0."""
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        assert (result["score"] >= 0).all(), "All scores must be non-negative"

    def test_rank_1_has_highest_score(self, minimal_frame: pd.DataFrame):
        """The gateway at rank 1 must have a score >= all others."""
        ranker = ThreeSigmaRanker()
        result = ranker.rank_week(minimal_frame, MONDAY)
        max_score = result["score"].max()
        rank_1_score = result[result["rank"] == 1]["score"].iloc[0]
        assert rank_1_score == max_score, (
            "Rank 1 gateway must have the highest score"
        )


# ---------------------------------------------------------------------------
# E. ThreeSigmaRanker: error handling
# ---------------------------------------------------------------------------
class TestThreeSigmaRankerErrors:
    def test_raises_on_empty_frame(self):
        """rank_week must raise ValueError when given an empty DataFrame."""
        ranker = ThreeSigmaRanker()
        empty_frame = pd.DataFrame(
            columns=["gateway_id", "ts_utc", "ts", "offline_duration_sec",
                     "disconnection_cnt", "reboot_cnt"]
        )
        with pytest.raises(ValueError, match="No telemetry data"):
            ranker.rank_week(empty_frame, MONDAY)


# ---------------------------------------------------------------------------
# F. Registry tests
# ---------------------------------------------------------------------------
class TestRegistry:
    def test_get_ranker_returns_three_sigma_by_default(self):
        ranker = get_ranker()
        assert isinstance(ranker, ThreeSigmaRanker)

    def test_get_ranker_by_explicit_name(self):
        ranker = get_ranker("three_sigma")
        assert isinstance(ranker, ThreeSigmaRanker)

    def test_get_ranker_raises_for_unknown_name(self):
        with pytest.raises(ValueError, match="Unknown ranking strategy"):
            get_ranker("nonexistent_strategy")

    def test_available_strategies_includes_three_sigma(self):
        strategies = available_strategies()
        assert "three_sigma" in strategies, (
            "three_sigma must always be registered"
        )

    def test_each_registered_strategy_can_be_instantiated(self):
        """Every registered strategy must be instantiable (no broken imports)."""
        for name in available_strategies():
            ranker = get_ranker(name)
            assert isinstance(ranker, RankingStrategy)
