# src/holdem/table/table.py

from __future__ import annotations
from collections import deque # Table waitlist
from typing import TYPE_CHECKING, ClassVar, NewType
from uuid import UUID, uuid7 # type: ignore[attr-defined]

from ..utils.errors import TableStateError

if TYPE_CHECKING:
    from .player import Player
    from .buttons_blinds import Buttons
    from ..strategies.base import Strategy

__all__ = ["Table", "TableID"]

# Strongly-typed ID (static typing aid; runtime is UUID)
TableID = NewType("TableID", UUID)

def _new_table_id() -> TableID:
    return TableID(uuid7())

class Table:

    # class variables
    wait_list: ClassVar[deque[Player]] = deque()
    tables: ClassVar[list[Table]] = []

    # bounds
    min_seats: ClassVar[int] = 2
    max_seats: ClassVar[int] = 9

    @classmethod
    def num_of_tables(cls) -> int:
        return len(cls.tables)

    def __init__(self, num_of_seats: int = 9, small_blind_amt: int = 2, big_blind_amt: int = 3):
        if not (self.min_seats <= num_of_seats <= self.max_seats):
            raise TableStateError(
                f"num_of_seats must be in [{self.min_seats}, {self.max_seats}]"
            )
        if small_blind_amt < 0:
            raise TableStateError("small blind must be >= 0")
        if big_blind_amt < 0:
            raise TableStateError("big blind must be >= 0")
        if big_blind_amt < small_blind_amt:
            raise TableStateError("big blind must be >= small blind")

        self.table_id: TableID = _new_table_id()

        self.num_of_seats: int = num_of_seats
        self.small_blind_amt: int = small_blind_amt
        self.big_blind_amt: int = big_blind_amt

        self.seats: dict[int, Player | None] = {s: None for s in range(1, self.num_of_seats + 1)}

        self.buttons: Buttons | None = None

        Table.tables.append(self)
        self.table_number: int = Table.num_of_tables()

    def seat_player(self, player: Player):
        if player.seat is not None:
            raise TableStateError(f"Player {player.name} is already seated.")
        for seat, occupant in self.seats.items():
            if occupant is None:
                self.seats[seat] = player
                player.seat = seat
                player.table = self
                player.newly_seated() # enforcement guardrails
                return
        Table.wait_list.append(player)

    def leave_seat(self, seat_number: int, session_end: bool = False):
        pl = self.seats[seat_number]
        self.seats[seat_number] = None
        if pl is not None:
            pl.seat = None
            pl.table = None

        if Table.wait_list and not session_end:
            next_player = Table.wait_list.popleft()
            self.seat_player(next_player)

    # Add change seat method

    def present(self, seat: int) -> bool:
        pl = self.seats[seat]
        return bool(pl and not pl.on_break)

    def eligible(self, seat: int) -> bool:
        pl = self.seats[seat]
        return bool(pl and not pl.on_break and not pl.owes_bb and not pl.owes_sb)

    def end_session(self) -> list[tuple[str, int, Strategy]]:
        end_session_players: list[tuple[str, int, Strategy]] = []
        for s, pl in list(self.seats.items()):
            if pl:
                end_session_players.append(pl.leave_game(session_end=True))
                pl.seat = None
                pl.table = None
            self.seats[s] = None
        self.buttons = None
        return end_session_players

    def print_table(self) -> str:

        def is_there(_seat: int) -> str:
            if self.seats.get(_seat, "No Seat") == "No Seat":
                return "XX"
            pl = self.seats[_seat]
            if pl is None:
                return "**"
            elif pl.on_break:
                return "br"
            elif pl.owes_bb or pl.owes_sb:
                return "ob"
            elif not pl.position.label:  # old code, should delete
                return "--"
            return f"{pl.position.label[-2:]}"

        lines = [
            f" ------- Table {self.table_number} ------- ",
            f"   /=[{is_there(4)}]==[{is_there(5)}]==[{is_there(6)}]=\\",
            f" [{is_there(3)}]                 [{is_there(7)}]  ",
            f"||                      ||",
            f" [{is_there(2)}]                 [{is_there(8)}]",
            f"   \\=[{is_there(1)}]==[de]==[{is_there(9)}]=/"
        ]

        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Table):
            return NotImplemented
        return self.table_id == other.table_id

    def __hash__(self) -> int:
        return hash(self.table_id)

    # table_id is immutable
    def __setattr__(self, name: str, value) -> None:
        if name == "table_id" and hasattr(self, "table_id"):
            raise AttributeError("table_id is immutable once set")
        object.__setattr__(self,name, value)

    def __repr__(self):
        return (f"Table(seats={self.num_of_seats}, SB={self.small_blind_amt}, \
        BB={self.big_blind_amt}, button={self.buttons.dealer_button})")

    def __str__(self):
        seated_occupants = ", ".join(
            f"{seat}: {player.name if player else 'Empty'}" for seat, player in self.seats.items())
        return f"Table {self.table_number}: {seated_occupants}"
