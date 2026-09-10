"""
Ranking Strategy Registry
==========================

This module maps string names to RankingStrategy instances.

Why this exists:
    The API and service layer ask for a strategy by name (e.g., "three_sigma").
    This registry is the only place that knows about concrete implementations.
    Adding a new ranker requires only:
      1. Creating the class in a new file
      2. Adding one line to the `_REGISTRY` dict below
    No other file needs to change.

Usage:
    from src.ranking.registry import get_ranker

    ranker = get_ranker("three_sigma")  # returns ThreeSigmaRanker()
    ranker = get_ranker()               # returns the default ranker
"""

from __future__ import annotations

from src.ranking.base import RankingStrategy
from src.ranking.three_sigma import ThreeSigmaRanker

# Maps strategy names to their class (not instances — instantiated on demand)
_REGISTRY: dict[str, type[RankingStrategy]] = {
    "three_sigma": ThreeSigmaRanker,
    # To add a new ranker:
    # "my_ranker": MyRanker,
}

DEFAULT_STRATEGY = "three_sigma"


def get_ranker(name: str = DEFAULT_STRATEGY) -> RankingStrategy:
    """Return an instance of the named ranking strategy.

    Args:
        name: Strategy name (must be a key in the registry).

    Returns:
        An instance of the requested RankingStrategy.

    Raises:
        KeyError: if `name` is not registered.
    """
    cls = _REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(
            f"Unknown ranking strategy {name!r}. "
            f"Available strategies: {available}"
        )
    return cls()


def available_strategies() -> list[str]:
    """Return the names of all registered ranking strategies."""
    return sorted(_REGISTRY)
