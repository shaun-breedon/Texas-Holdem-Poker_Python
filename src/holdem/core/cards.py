# src/holdem/core/cards.py

from __future__ import annotations
from dataclasses import dataclass # Card
from typing import ClassVar # Suit
from functools import total_ordering # Card

from .enums import Suit, Rank
from ..utils.rng import RNG, default_rng

__all__ = ["Card", "Deck"]

@total_ordering
@dataclass(frozen=True, slots=True)
class Card:
    rank: Rank
    suit: Suit

    __SUIT_SORT: ClassVar[dict[Suit, int]] = {
        Suit.SPADES: 3,
        Suit.HEARTS: 2,
        Suit.DIAMONDS: 1,
        Suit.CLUBS: 0
    }

    def __repr__(self):
        return f"Card(Rank.{self.rank.name}, Suit.{self.suit.name})"

    def __str__(self):
        return f"{self.rank}{self.suit.symbol}"

    def __lt__(self, other: object):
        """ (rank, suit) < (other.rank, other.suit)
        Uses a deterministic suit_sort dict to sort by suit when rank is equal.
        Doesn't affect poker hand evaluation. """

        if not isinstance(other, Card):
            return NotImplemented
        return (int(self.rank), type(self).__SUIT_SORT[self.suit]) < (int(other.rank), type(self).__SUIT_SORT[other.suit])

class Deck:
    __slots__ = ("cards",)
    _DECK_TEMPLATE: ClassVar[tuple[Card, ...]] = tuple(Card(r, s) for s in Suit for r in Rank)

    def __init__(self, *, shuffle_on_init: bool=False):
        self.cards: list[Card] = list(self._DECK_TEMPLATE)
        if shuffle_on_init:
            self.shuffle()

    def reset(self, *, shuffle_on_reset: bool=False) -> None:
        self.cards = list(self._DECK_TEMPLATE)
        if shuffle_on_reset:
            self.shuffle()

    def shuffle(self, *, seed: int | None = None, prng: RNG | None = None):
        """
                Shuffle the deck in place.

                Args:
                    seed: if provided, shuffle deterministically for this call only.
                    prng: optional RNG instance; defaults to the project-wide rng.default_rng.
                """
        _rng = prng or default_rng
        if seed is None:
            _rng.shuffle(self.cards)
        else:
            # temporary deterministic shuffle without polluting global state
            with _rng.temp_seed(seed):
                _rng.shuffle(self.cards)

    def draw(self, n: int=1) -> list[Card]:
        """Draw n cards and return them as a list. Raises ValueError on invalid n or insufficient cards."""
        if n <= 0: raise ValueError("Must draw at least one card.")
        if n > len(self.cards): raise ValueError("Not enough cards left to draw.")
        drawn: list[Card] = [self.cards.pop() for _ in range(n)]
        return drawn

    def draw_one(self) -> Card:
        """Convenience to draw a single card and return a Card object (not a list)."""
        return self.draw()[0]

    def deal(self, num_players: int, cards_each: int) -> list[list[Card]]:
        """Deal cards_each to num_players, returning list of hands (each a list of Cards)."""
        if num_players <= 0 or cards_each < 0:
            raise ValueError("num_players must be > 0 and cards_each >= 0")
        total = num_players * cards_each
        if total > len(self.cards):
            raise ValueError("Not enough cards to deal.")
        hands = [[] for _ in range(num_players)]
        for _ in range(cards_each):
            for hand in hands:
                hand.append(self.draw_one())
        return hands

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def __repr__(self):
        return f"Deck({len(self.cards)} cards)"

    def __str__(self):
        return ' '.join(str(c) for c in self.cards)