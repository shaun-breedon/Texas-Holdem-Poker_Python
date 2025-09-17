# src/holdem/__main__.py

from __future__ import annotations
from typing import TypeAlias
# from .cli import main

from .table.player import Player
from .strategies.base import Strategy
from .strategies.simple import Tag, Lag, Nit, CallingStation
from .engine.game import Hand
from .table.table import Table

PlayerSpec: TypeAlias = tuple[str, int, Strategy]

def seat_players(pl_list: list[PlayerSpec], table: Table):
    for name, stack, strategy in pl_list:
        if stack >= table.big_blind_amt:
            pl = Player(name=name, stack=stack, strategy=strategy)
            table.seat_player(pl)
        else:
            print(f"{name} has {stack} chips and cannot play (BB={table.big_blind_amt}")

def run_game(*,n_times: int, pl_list: list[PlayerSpec]) -> list[Hand]:
    t1 = Table()
    seat_players(pl_list, t1)

    hands: list[Hand] = list()
    for _ in range(n_times):
        h = Hand(t1)
        h.start()
        hands.append(h)
    return hands

player_list: list[PlayerSpec] = [('Young TAG', 700, Tag()),
                                 ('ME', 1000, Tag()),
                                 ('Young LAG', 600, Lag()),
                                 ('Middle-Aged Regular', 700, CallingStation()),
                                 ('Recreational Punter', 500, CallingStation()),
                                 ('Old Man Coffee', 1000, Nit()),
                                 ('Pro', 800, Tag()),
                                 ('Middle-Aged LAG', 500, Lag()),
                                 ('Villain LAG', 500, Lag())
                                 ]

def main() -> int:
    hands = run_game(n_times=5, pl_list=player_list)
    print(f"\nDealt {len(hands)} hands.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
