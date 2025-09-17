# src/holdem/table/pots.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from ..utils.errors import PotsStateError

if TYPE_CHECKING:
    from .player import Player
    from ..engine.game import Hand

__all__ = ["Pot", "PotID"]

@dataclass(frozen=True, slots=True)
class PotID:
    hand_id: UUID
    pot_number: int

    def __str__(self) -> str:
        return f"{self.hand_id}:{self.pot_number}"

@dataclass(slots=True, eq=False)
class Pot:
    hand: Hand
    eligible_players: set[Player] = field(default_factory=set)
    winning_players: set[Player] = field(default_factory=set)
    amount: int = 0
    capped: bool = False  # No more chips can be added
    discard: bool = False  # Pot not used

    pot_number: int = field(init=False)

    def __post_init__(self):
        self.pot_number = self.hand.allocate_pot_number()  # pot numbers for the given Hand instance
        self.eligible_players = set(self.eligible_players) # safe copy

    @property
    def pot_id(self) -> PotID:
        return PotID(self.hand.hand_id, self.pot_number)

    @property
    def is_main(self) -> bool:
        return self.pot_number == 0

    def add(self, chips: int) -> None:
        if chips < 0:
            raise PotsStateError(f"chips = {chips} added to {self} must be non-negative")
        if self.capped and chips:
            raise PotsStateError(f"{self} is capped; cannot add more chips")
        self.amount += chips

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pot):
            return NotImplemented
        return self.pot_id == other.pot_id

    def __hash__(self) -> int:
        return hash(self.pot_id)

    def __setattr__(self, name: str, value) -> None:
        if name == "pot_number" and hasattr(self, "pot_number"):
            raise AttributeError("pot_number is immutable once set")
        if name == "hand" and hasattr(self, "hand"):
            raise AttributeError("hand is immutable once set")
        object.__setattr__(self,name, value)

    def __repr__(self):
        return f"Pot#{self.pot_number}(amount={self.amount}, capped={self.capped}, hand#{self.pot_id.hand_id})"

    def __str__(self):
        return f"{'Main Pot' if self.is_main else f'Side Pot {self.pot_number}'}: ${self.amount}"