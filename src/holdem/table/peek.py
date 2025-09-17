# src/holdem/table/peek.py
"""
This peeks ahead and finds the next buttons and headsup, while not posting blinds or changing any states
buttons_blinds actually advances the table buttons, posts blinds and changes states.

This uses the Forward Moving Button rules for Cash Game:
1- The button always moves forward to the next active player.
2- The two players to the left of the button will always post a blind. They post a SB if they posted a BB last hand.
They post a BB if not, and post a SB the following hand.
3- The button and (all) players to the right also post a blind if they have not yet paid both their BB and SB in
this round of blinds. If they owe both, then they post a BB and a SB ante.
"""

from __future__ import annotations
from typing import NamedTuple

from .buttons_blinds import Buttons, TableLike, is_headsup, integrity_check
from ..utils.errors import TableStateError

__all__ = ["peek_buttons"]

class PeekResult(NamedTuple):
    buttons: Buttons
    is_heads_up: bool

def _peek_first_hand(tbl: TableLike) -> PeekResult:
    present_seats = [s for s in range(1, tbl.num_of_seats + 1) if tbl.present(s)]
    dealer_idx, dealer_button = len(present_seats) - 1, present_seats[-1]

    if is_headsup(tbl):
        big_blind_button = present_seats[(dealer_idx + 1) % 2]
        small_blind_button = dealer_button
        is_heads_up = True
    else:
        n = len(present_seats)
        small_blind_button = present_seats[(dealer_idx + 1) % n]
        big_blind_button = present_seats[(dealer_idx + 2) % n]
        is_heads_up = False

    buttons = Buttons(
        dealer_button=dealer_button,
        small_blind_button=small_blind_button,
        big_blind_button=big_blind_button
    )
    return PeekResult(buttons=buttons, is_heads_up=is_heads_up)

def _peek_headsup(tbl: TableLike, _next_dealer: int) -> tuple[int, int]:
    for step_bb_hu in range(1, tbl.num_of_seats):
        next_big_blind = ((_next_dealer - 1 + step_bb_hu) % tbl.num_of_seats) + 1
        if not tbl.present(next_big_blind):
            continue
        next_small_blind = _next_dealer

        return next_small_blind, next_big_blind
    raise TableStateError("No present players found for the big blind")

def _peek_small_blind(tbl: TableLike, _next_dealer: int) -> int:
    for step_sb in range(1, tbl.num_of_seats):
        next_small_blind = ((_next_dealer - 1 + step_sb) % tbl.num_of_seats) + 1
        if not tbl.present(next_small_blind):
            continue

        return next_small_blind
    raise TableStateError("No present players found for the small blind")

def _peek_big_blind(tbl: TableLike, _next_small_blind: int) -> int:
    for step_bb in range(1, tbl.num_of_seats):
        next_big_blind = ((_next_small_blind - 1 + step_bb) % tbl.num_of_seats) + 1
        if not tbl.present(next_big_blind):
            continue

        return next_big_blind
    raise TableStateError("No present players found for the big blind")

def _peek_next_buttons(tbl: TableLike) -> PeekResult:
    for step in range(1, tbl.num_of_seats):
        next_dealer = ((tbl.buttons.dealer_button - 1 + step) % tbl.num_of_seats) + 1
        nxt_deal_pl = tbl.seats[next_dealer]

        if not tbl.present(next_dealer) or nxt_deal_pl.newly_joined:
            continue

        if is_headsup(tbl):
            next_small_blind, next_big_blind = _peek_headsup(tbl, next_dealer)
            is_heads_up = True
        else:
            next_small_blind = _peek_small_blind(tbl, next_dealer)
            next_big_blind = _peek_big_blind(tbl, next_small_blind)
            is_heads_up = False

        buttons = Buttons(
            dealer_button=next_dealer,
            small_blind_button=next_small_blind,
            big_blind_button=next_big_blind
        )
        return PeekResult(buttons=buttons, is_heads_up=is_heads_up)
    raise TableStateError("No present players found for the dealer")

def peek_buttons(tbl: TableLike) -> PeekResult:
    # Guardrails
    integrity_check(tbl)

    if tbl.buttons is None:  # If first hand of the table session
        peeked_results = _peek_first_hand(tbl)
    else:
        peeked_results = _peek_next_buttons(tbl)

    return peeked_results
