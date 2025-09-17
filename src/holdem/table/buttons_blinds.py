# src/holdem/table/buttons_blinds.py
"""
This uses the Forward Moving Button rules for Cash Game:
1- The button always moves forward to the next active player.
2- The two players to the left of the button will always post a blind. They post a SB if they posted a BB last hand.
They post a BB if not, and post a SB the following hand.
3- The button and (all) players to the right also post a blind if they have not yet paid both their BB and SB in
this round of blinds. If they owe both, then they post a BB and a SB ante.
"""

from __future__ import annotations
from typing import Protocol, NamedTuple
from dataclasses import dataclass

from ..utils.errors import TableStateError

__all__ = ["advance_buttons_post_blinds", "Buttons"]

@dataclass(frozen=True, slots=True)
class Buttons:
    dealer_button: int
    small_blind_button: int
    big_blind_button: int

@dataclass(slots=True)
class Ante:
    amount: int = 0

class ButtonsAnte(NamedTuple):
    buttons: Buttons
    ante: Ante

class PlayerLike(Protocol):
    name: str
    on_break: bool
    newly_joined: bool
    waiting_for_big_blind: bool
    paid_sb: bool
    paid_bb: bool
    owes_sb: bool
    owes_bb: bool
    all_in: bool
    def pip(self, amount: int, ante: bool = False) -> int: ...

class TableLike(Protocol):
    num_of_seats: int
    small_blind_amt: int
    big_blind_amt: int
    seats: dict[int, PlayerLike | None]
    buttons: Buttons | None
    def present(self, seat: int) -> bool: ...

def is_headsup(tbl: TableLike) -> bool:
    n_present = sum(tbl.present(s) for s in tbl.seats)
    if n_present < 2:
        raise TableStateError("Need ≥2 present players to move the button")
    elif n_present == 2:
        return True
    else:
        return False

def _post_small_blind(tbl: TableLike,
                      pl: PlayerLike,
                      ante: bool = False,
                      owed: bool = False,
                      in_blinds: bool = True,
                      hand_ante: Ante = None):
    if ante:
        if hand_ante is None:
            raise TableStateError("No ante provided")
        sb = pl.pip(tbl.small_blind_amt, ante=True)
        hand_ante.amount += sb
    else:
        sb = pl.pip(tbl.small_blind_amt)
    if in_blinds:
        pl.paid_sb = True
    pl.owes_sb = False
    # Replace print statements with logging
    print(f"{pl.name} posts{' owed ' if owed else ' '}small blind {'ante' if ante else ''} of {sb}")
    if pl.all_in: print(f"{pl.name} is all in")

def _post_big_blind(tbl: TableLike,
                    pl: PlayerLike,
                    owed: bool = False,
                    in_blinds: bool = True):
    bb = pl.pip(tbl.big_blind_amt)
    if in_blinds:
        pl.paid_bb = True
    pl.owes_bb = False
    pl.newly_joined = False
    # Replace print statements with logging
    print(f"{pl.name} posts{' owed ' if owed else ' '}big blind of {bb}")
    if pl.all_in: print(f"{pl.name} is all in")

# def _ask_player_to_post(pl: PlayerLike, pos: str) -> bool:
#     if pos.strip().upper() == 'BU':
#         question = f"BU: {pl.name} to post owed:{'' if pl.paid_sb else '-Small Blind-'}{'' if pl.paid_bb else '-Big Blind-'}? (y/n):"
#     elif pos.strip().upper() == 'SB':
#         question = f"SB: {pl.name} to post owed:-Big Blind-? (y/n):"
#     else:
#         raise ValueError("Invalid String")
#
#     while True:
#         answer = input(question).strip().lower()
#         if answer in ("yes", "y", "true", "1"):
#             will_post = True
#             break
#         elif answer in ("no", "n", "false", "0"):
#             will_post = False
#             break
#         else:
#             print("Invalid input, please type yes or no.")
#
#     return will_post

def integrity_check(tbl: TableLike):
    n_present = sum(1 for s, pl in tbl.seats.items() if pl and not pl.on_break)
    if n_present < 2:
        raise TableStateError("Need ≥2 present players to proceed with hand")
    if set(tbl.seats.keys()) != set(range(1, tbl.num_of_seats + 1)):
        raise TableStateError("Seats must be 1..N")

def _dealer_blinds_reset(dealer_pl: PlayerLike):
    dealer_pl.paid_sb = False
    dealer_pl.paid_bb = False

def _first_hand(tbl: TableLike) -> Buttons:
    for pl in tbl.seats.values():
        if pl:
            pl.owes_sb = pl.paid_sb = pl.paid_bb = False  # Enforcement guardrails
            if not pl.on_break:
                pl.owes_bb = pl.newly_joined = False

    present_seats = [s for s in range(1, tbl.num_of_seats + 1) if tbl.present(s)]
    dealer_idx, dealer_button = len(present_seats) - 1, present_seats[-1]

    if is_headsup(tbl):
        big_blind_button = present_seats[(dealer_idx + 1) % 2]
        bb_player = tbl.seats[big_blind_button]
        dealer_player = tbl.seats[dealer_button]

        # Dealer posts Small Blind
        _post_small_blind(tbl, dealer_player)
        _dealer_blinds_reset(dealer_player)

        # Post Big Blind
        _post_big_blind(tbl, bb_player)

        small_blind_button = dealer_button
        return Buttons(
            dealer_button=dealer_button,
            small_blind_button=small_blind_button,
            big_blind_button=big_blind_button
        )

    n = len(present_seats)
    small_blind_button = present_seats[(dealer_idx + 1) % n]
    big_blind_button = present_seats[(dealer_idx + 2) % n]
    sb_player, bb_player = tbl.seats[small_blind_button], tbl.seats[big_blind_button]

    # Post Blinds
    _post_small_blind(tbl, sb_player)
    _post_big_blind(tbl, bb_player)

    sb_player.paid_bb = True  # First-hand setting to not falsely trigger an owed BB on 2nd hand

    return Buttons(
        dealer_button=dealer_button,
        small_blind_button=small_blind_button,
        big_blind_button=big_blind_button
    )

def _missed_dealer(pl: PlayerLike):
    pl.owes_bb = not pl.paid_bb
    pl.owes_sb = not pl.paid_sb and not pl.newly_joined
    _dealer_blinds_reset(pl)

def _missed_big_blind(pl: PlayerLike, headsup: bool = False):
    pl.owes_bb = True
    if headsup and not pl.newly_joined:
        pl.owes_sb = True

def _missed_small_blind(pl: PlayerLike):
    if not pl.newly_joined:
        pl.owes_sb = True

def _headsup(tbl: TableLike, _next_dealer: int, hand_ante: Ante) -> tuple[int, int]:
    for step_bb_hu in range(1, tbl.num_of_seats):
        next_big_blind = ((_next_dealer - 1 + step_bb_hu) % tbl.num_of_seats) + 1
        nxt_bb_pl = tbl.seats[next_big_blind]
        nxt_deal_pl = tbl.seats[_next_dealer]

        # Skip the ineligible
        if nxt_bb_pl is None:
            continue
        elif nxt_bb_pl.on_break:
            _missed_big_blind(nxt_bb_pl, headsup=True)
            continue

        # Dealer posts Small Blind
        if nxt_deal_pl.paid_bb:
            _post_small_blind(tbl, nxt_deal_pl)
        else:
            _post_big_blind(tbl, nxt_deal_pl, owed=True)
            _post_small_blind(tbl, nxt_deal_pl, ante=True, hand_ante=hand_ante)
        _dealer_blinds_reset(nxt_deal_pl)

        # Post Big Blind
        _post_big_blind(tbl, nxt_bb_pl)
        if nxt_bb_pl.owes_sb and not nxt_bb_pl.newly_joined:
            _post_small_blind(tbl, nxt_bb_pl, ante=True, owed=True, hand_ante=hand_ante)

        next_small_blind = _next_dealer
        return next_small_blind, next_big_blind
    raise TableStateError("No present players found for the big blind")


def _find_small_blind(tbl: TableLike, _next_dealer: int, hand_ante: Ante) -> int:
    for step_sb in range(1, tbl.num_of_seats):
        next_small_blind = ((_next_dealer - 1 + step_sb) % tbl.num_of_seats) + 1
        nxt_sb_pl = tbl.seats[next_small_blind]

        # Skip the ineligible
        if nxt_sb_pl is None:
            continue
        elif nxt_sb_pl.on_break:
            _missed_small_blind(nxt_sb_pl)
            continue
        # elif not nxt_sb_pl.paid_bb and nxt_sb_pl.waiting_for_big_blind:
        #     will_post = _ask_player_to_post(nxt_sb_pl, pos='SB')
        #     if not will_post:
        #         _missed_small_blind(nxt_sb_pl)
        #         continue

        # Post Small Blind
        if not nxt_sb_pl.paid_bb:
            _post_big_blind(tbl, nxt_sb_pl, owed=True)
            _post_small_blind(tbl, nxt_sb_pl, ante=True, hand_ante=hand_ante)
        else:
            _post_small_blind(tbl, nxt_sb_pl)

        return next_small_blind
    raise TableStateError("No present players found for the small blind")


def _find_big_blind(tbl: TableLike, _next_small_blind: int, hand_ante: Ante) -> int:
    for step_bb in range(1, tbl.num_of_seats):
        next_big_blind = ((_next_small_blind - 1 + step_bb) % tbl.num_of_seats) + 1
        nxt_bb_pl = tbl.seats[next_big_blind]

        # Skip the ineligible
        if nxt_bb_pl is None:
            continue
        elif nxt_bb_pl.on_break:
            _missed_big_blind(nxt_bb_pl)
            continue

        # Post Big Blind
        _post_big_blind(tbl, nxt_bb_pl)
        if nxt_bb_pl.owes_sb and not nxt_bb_pl.newly_joined:
            _post_small_blind(tbl, nxt_bb_pl, ante=True, owed=True, hand_ante=hand_ante)

        return next_big_blind
    raise TableStateError("No present players found for the big blind")


def _move_buttons(tbl: TableLike, hand_ante: Ante) -> Buttons:
    for step in range(1, tbl.num_of_seats):
        next_dealer = ((tbl.buttons.dealer_button - 1 + step) % tbl.num_of_seats) + 1
        nxt_deal_pl = tbl.seats[next_dealer]

        # Skip the ineligible
        if nxt_deal_pl is None:
            continue
        elif nxt_deal_pl.on_break or nxt_deal_pl.newly_joined:
            _missed_dealer(nxt_deal_pl)
            continue
        # elif not (nxt_deal_pl.paid_bb and nxt_deal_pl.paid_sb) and nxt_deal_pl.waiting_for_big_blind:
        #     will_post = _ask_player_to_post(nxt_deal_pl, pos='BU')
        #     if not will_post:
        #         _missed_dealer(nxt_deal_pl)
        #         continue

        if is_headsup(tbl):
            next_small_blind, next_big_blind = _headsup(tbl, next_dealer, hand_ante=hand_ante)
            return Buttons(
                dealer_button=next_dealer,
                small_blind_button=next_small_blind,
                big_blind_button=next_big_blind
            )

        # Dealer posts any owed blinds
        if not nxt_deal_pl.paid_bb:
            _post_big_blind(tbl, nxt_deal_pl, owed=True, in_blinds=False)
        if not nxt_deal_pl.paid_sb:
            _post_small_blind(tbl, nxt_deal_pl, ante=True, owed=True, in_blinds=False, hand_ante=hand_ante)

        _dealer_blinds_reset(nxt_deal_pl)

        next_small_blind = _find_small_blind(tbl, next_dealer, hand_ante=hand_ante)
        next_big_blind = _find_big_blind(tbl, next_small_blind, hand_ante=hand_ante)

        return Buttons(
            dealer_button=next_dealer,
            small_blind_button=next_small_blind,
            big_blind_button=next_big_blind
        )
    raise TableStateError("No present players found for the dealer")

def _post_additional_owed_blinds(tbl: TableLike, btns: Buttons, hand_ante: Ante) -> None:
    non_button_active_players = [
        pl for s, pl in tbl.seats.items()
        if pl
           and s not in {btns.dealer_button, btns.small_blind_button, btns.big_blind_button}
           and tbl.present(s)
           and not pl.waiting_for_big_blind
    ]

    for pl in non_button_active_players:
        if pl.owes_bb:
            _post_big_blind(tbl, pl, owed=True, in_blinds=False)
        if pl.owes_sb:
            _post_small_blind(tbl, pl, ante=True, owed=True, in_blinds=False, hand_ante=hand_ante)

def advance_buttons_post_blinds(tbl: TableLike) -> ButtonsAnte:
    # Guardrails
    integrity_check(tbl)

    hand_ante: Ante = Ante()

    if tbl.buttons is None:  # If first hand of the table session
        next_buttons = _first_hand(tbl)
    else:
        next_buttons = _move_buttons(tbl, hand_ante)

    tbl.buttons = next_buttons # Advance table buttons
    _post_additional_owed_blinds(tbl, next_buttons, hand_ante)

    buttons_ante = ButtonsAnte(buttons=next_buttons, ante=hand_ante)
    return buttons_ante