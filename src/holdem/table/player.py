# src/holdem/table/player.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar, NewType, TYPE_CHECKING
from uuid import UUID
from uuid6 import uuid7

from ..core.enums import Action, Position
from ..core.evaluator import evaluate_player_hand

if TYPE_CHECKING:
    from ..core.cards import Card, Deck
    from ..core.evaluator import HandEval
    from .table import Table
    from ..strategies.base import Strategy, View, Decision

__all__ = ["Player", "PlayerID"]

# Strongly-typed ID (static typing aid; runtime is UUID)
PlayerID = NewType("PlayerID", UUID)

def _new_player_id() -> PlayerID:
    return PlayerID(uuid7())

@dataclass(slots=True, eq=False)
class Player:
    """ Equality and hashing are based only on player_id. player_id is treated as immutable after init (guarded in __setattr__). """

    # --- Class Vars ---
    num_of_players: ClassVar[int] = 0
    players: ClassVar[list[Player]] = []

    # --- Input Vars ---
    name: str
    stack: int
    strategy: Strategy

    # --- ID ---
    player_id: PlayerID = field(default_factory=_new_player_id)

    # --- optional input var ---
    waiting_for_big_blind: bool = False

    # --- runtime ---
    table: Table | None = None
    seat: int | None = None

    # session state vars
    on_break: bool = False
    newly_joined: bool = True
    owes_bb: bool = True
    owes_sb: bool = False
    paid_bb: bool = False
    paid_sb: bool = False

    # hand state vars
    position: Position | None = None
    current_bet: int = 0
    hole_cards: list[Card, Card] = field(default_factory=list)
    folded: bool = False
    all_in: bool = False

    def __post_init__(self) -> None:
        type(self).num_of_players += 1
        type(self).players.append(self)

    def newly_seated(self):
        self.newly_joined = self.owes_bb = True  # Enforcement guardrails
        self.owes_sb = self.paid_sb = self.paid_bb = False  # Enforcement guardrails

    def leave_game(self, session_end: bool = False) -> tuple[str, int, Strategy]:
        if self.position is not None and not self.folded:
            self.fold()
        if self.table is not None and self.seat is not None:
            self.table.leave_seat(self.seat, session_end)

        self.on_break = False
        self.newly_joined = True
        self.owes_bb = True
        self.owes_sb = False
        self.paid_bb = False
        self.paid_sb = False

        return self.name, self.stack, self.strategy

    def take_break(self):
        self.on_break = True
        if self.position is not None and not self.folded:
            self.fold()

    def resume_play(self):
        if self.stack > 0:
            self.on_break = False
            print(f"{self.name} has resumed play")
        else:
            print(f"{self.name} has {self.stack} chips and not enough to play")

    def pip(self, amount: int, ante: bool = False) -> int:
        """Put-money-In-Pot. Takes from stack and handles all-in if necessary"""
        if amount < 0:
            raise ValueError("pip amount cannot be negative.")

        pay = min(amount, self.stack)
        self.stack -= pay
        if not ante:
            self.current_bet += pay
        if self.stack == 0:
            self.all_in = True
        return pay

    def draw(self, deck: Deck, n: int = 1):
        self.hole_cards.extend(deck.draw(n))

    def get_player_hand(self, board: list[Card] | None = None) -> HandEval:
        return evaluate_player_hand(self.hole_cards, board)

    def show_hand(self, board: list[Card] = None) -> str:
        hand= self.get_player_hand(board)
        hand_string = f"{hand.hand_rank}: "
        for c in hand.hand_cards:
            hand_string += f"{c} "
        return hand_string

    def can_act(self) -> bool:
        return not self.folded and not self.all_in and not self.on_break and self.seat is not None

    def check(self):
        print(f"{self.position} CHECKS. ({self.name})")

    # Make sure amount is "to_call"
    def call(self, amount: int):
        self.pip(amount)
        print(f"{self.position} CALLS {amount} more for a total of {self.current_bet}. ({self.name})")

    # Always first bet of round, ie can never be used preflop and never if another player has already bet
    # ie self.highest_bet must always be 0
    def bet(self, amount: int):
        self.pip(amount)
        print(f"{self.position} BETS {self.current_bet}. ({self.name})")

    # amount should be total amount of raise, not "to_call"
    def raise_to(self, amount: int):
        add = amount - self.current_bet
        self.pip(add)
        print(f"{self.position} RAISES to {self.current_bet}. ({self.name})")

    def go_all_in(self):
        self.pip(self.stack)
        print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")

    def fold(self):
        self.folded = True
        print(f"{self.position} FOLDS. ({self.name})")

    def player_action(self, view: View) -> Decision:
        return self.strategy.decide(view)

    def reset_for_new_street(self):
        self.current_bet = 0

    def reset_for_new_hand(self):
        self.position = None
        self.current_bet = 0
        self.hole_cards.clear()
        self.folded = False
        self.all_in = False
        if self.stack <= 0 and self.seat is not None:
            self.on_break = True
            print(f"Player {self} has lost their stack")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            return NotImplemented
        return self.player_id == other.player_id

    def __hash__(self) -> int:
        return hash(self.player_id)

    # player_id is immutable
    def __setattr__(self, name: str, value) -> None:
        if name == "player_id" and hasattr(self, "player_id"):
            raise AttributeError("player_id is immutable once set")
        object.__setattr__(self,name, value)

    def __repr__(self):
        return f"Player(name='{self.name}', stack={self.stack}, strategy='{self.strategy}') id={self.player_id}"

    def __str__(self):
        return f"{self.name}, stack: {self.stack}, {self.strategy}"
