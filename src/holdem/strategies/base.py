# src/holdem/strategies/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import FrozenSet, TYPE_CHECKING

from ..core.enums import GameState, Position

if TYPE_CHECKING:
    from ..core.enums import Action, HandRank, Position
    from ..core.cards import Card
    from .features import Features

__all__ = ["Decision", "View", "Strategy"]

@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    amount: int | None = None

@dataclass(frozen=True, slots=True)
class View:
    street: GameState
    pot: int
    highest_bet: int
    to_call: int
    raise_amount: int
    n_raises: dict[GameState, int]
    open_action: bool
    board: tuple[Card, ...]
    legal: FrozenSet[Action]
    big_blind: int

    position: Position
    stack: int
    current_bet: int
    hole_cards: tuple[Card, Card]
    hand_rank: HandRank
    hand_cards: tuple[Card, ...]
    fx: Features

    @property
    def min_raise_to(self) -> int | None:
        """Target amount for the minimum legal raise (total bet)"""
        return self.highest_bet + self.raise_amount

    @property
    def chips_to_min_raise(self) -> int | None:
        mr = self.min_raise_to
        return max(0, mr - self.current_bet)

    @property
    def limp_fold_to_bb(self) -> bool:
        return True if (self.street == GameState.PRE_FLOP
                        and self.position == Position.BIG_BLIND
                        and self.highest_bet - self.current_bet == 0
                        ) else False

class Strategy(ABC):
    """
    Abstract base class for strategies.
    Concrete strategy classes will subclass this and implement decide().
    """
    @abstractmethod
    def decide(self, view: View) -> Decision: ...

    @classmethod
    def _bet(cls, amount: float, view: View) -> int:
        return max(round(amount), view.big_blind)

    @classmethod
    def _raise_to(cls, amount: float, view: View) -> int:
        return max(round(amount), view.min_raise_to)

    def __repr__(self):
        return f"Strategy()"
