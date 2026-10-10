"""Cards are plain strings: rank + suit, e.g. "Ah", "Td", "2c".

Ranks: 2 3 4 5 6 7 8 9 T J Q K A
Suits: c (clubs) d (diamonds) h (hearts) s (spades)
"""

from __future__ import annotations

import secrets
from typing import Sequence

from treys import Card as _TreysCard
from treys import Evaluator as _TreysEvaluator

RANKS = "23456789TJQKA"
SUITS = "cdhs"
FULL_DECK: tuple[str, ...] = tuple(r + s for r in RANKS for s in SUITS)

_rng = secrets.SystemRandom()
_evaluator = _TreysEvaluator()


def shuffled_deck() -> list[str]:
    deck = list(FULL_DECK)
    _rng.shuffle(deck)
    return deck


def is_card(value: str) -> bool:
    return len(value) == 2 and value[0] in RANKS and value[1] in SUITS


def evaluate(hole: Sequence[str], board: Sequence[str]) -> int:
    """Hand strength of the best 5 of hole+board. Lower is better (1 = royal flush)."""
    return _evaluator.evaluate(
        [_TreysCard.new(c) for c in board], [_TreysCard.new(c) for c in hole]
    )


def hand_name(score: int) -> str:
    """Human readable class of a score, e.g. 'Two Pair'."""
    return _evaluator.class_to_string(_evaluator.get_rank_class(score))
