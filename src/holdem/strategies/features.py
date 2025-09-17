# src/holdem/strategies/features.py
""" For the Flop, Turn, and River, evaluates the properties of a players hand to the board. """

from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass
from collections import Counter

from ..core.enums import Suit, Rank, GameState, HandRank

if TYPE_CHECKING:
    from ..core.cards import Card

__all__ = ["Features", "evaluate_hand_features"]

@dataclass(frozen=True, slots=True)
class Features:
    has_fd: bool                                 # flush draw (4 to a suit)
    has_bdfd: bool                               # backdoor flush draw (flop only)
    has_oesd: bool                               # open-ended straight draw (>= 2 distinct completing ranks)
    has_gutshot: bool                            # inside straight draw (exactly 1 completing rank)
    overcards: int                               # 0/1/2 over the highest board rank

def _eval_fd(
        street: GameState,
        hole_cards: tuple[Card, Card],
        board: tuple[Card, ...],
        hand_rank: HandRank
) -> tuple[bool, bool]:
    """ Returns (has_fd, has_bdfd).
        Flush draw: 3 on board + 1 in hand, OR 2 on board + 2 in hand (same suit);
        Backdoor Flush Draw: flop only; 2 on board + 1 in hand, OR 1 on board + 2 in hand (same suit). """

    if street is GameState.RIVER or hand_rank in {HandRank.FLUSH, HandRank.STRAIGHT_FLUSH, HandRank.ROYAL_FLUSH}:
        return False, False

    s0, s1 = hole_cards[0].suit, hole_cards[1].suit
    board_counts = Counter(c.suit for c in board)  # board-only

    def total_of(s):
        return board_counts.get(s, 0) + (s0 == s) + (s1 == s)

    # Flush draw
    if any(total_of(s) == 4 for s in Suit):
        return True, False

    # Backdoor Flush Draw
    if street is GameState.FLOP and any(total_of(s) == 3 for s in Suit):
        return False, True

    return False, False


def _eval_sd(
        street: GameState,
        hole_cards: tuple[Card, Card],
        board: tuple[Card, ...],
        hand_rank: HandRank
) -> tuple[bool, bool]:
    """ Returns (has_oesd, has_gutshot).
        Open-Ended Straight Draw means 2 distinct card ranks complete a straight (8+ outs);
        Gutshot means exactly 1 such rank completes a straight (4 outs). """

    if street is GameState.RIVER or hand_rank in {HandRank.STRAIGHT, HandRank.STRAIGHT_FLUSH, HandRank.ROYAL_FLUSH}:
        return False, False

    ranks: set[int] = {c.rank.value for c in (*hole_cards, *board)}
    if Rank.ACE.value in ranks:
        ranks.add(1)  # Handles wheel straight

    missing: set[int] = set()
    for low in range(1, 11):
        window = {low + i for i in range(5)}
        present = window & ranks
        if len(present) == 4:
            (m,) = tuple(window - present)
            missing.add(14 if m == 1 else m)     # normalize Ace-low back to 14
            if len(missing) >= 2:
                return True, False                # OESD
    if len(missing) == 1:
        return False, True                       # Gutshot
    return False, False

def _eval_overs(hole_cards: tuple[Card, Card], board: tuple[Card, ...]) -> int:
    high_board = max(c.rank for c in board)
    return int(hole_cards[0].rank > high_board) + int(hole_cards[1].rank > high_board)

def evaluate_hand_features(street: GameState,
                           hole_cards: tuple[Card, Card],
                           board: tuple[Card, ...],
                           hand_rank: HandRank
                           ) -> Features:

    if street == GameState.PRE_FLOP:
        return Features(has_fd=False, has_bdfd=False, has_oesd=False, has_gutshot=False, overcards=0)

    fd, bdfd = _eval_fd(street, hole_cards, board, hand_rank)
    oesd, gutshot = _eval_sd(street, hole_cards, board, hand_rank)
    overs = _eval_overs(hole_cards, board)
    return Features(has_fd=fd, has_bdfd=bdfd, has_oesd=oesd, has_gutshot=gutshot, overcards=overs)