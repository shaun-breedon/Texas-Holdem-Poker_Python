# src/holdem/engine/showdown.py

from __future__ import annotations
from typing import TYPE_CHECKING

from ..core.enums import GameState
from ..utils.errors import EngineStateError

if TYPE_CHECKING:
    from .game import Hand
    from ..table.player import Player
    from ..core.evaluator import HandEval
    from ..table.pots import Pot

__all__ = ["showdown"]

def _determine_winners(hand: Hand, pot: Pot) -> dict[Player, HandEval]:
    eligible_players: dict[Player, HandEval] = {ep: ep.get_player_hand(hand.community_board)
                                                for ep in pot.eligible_players if not ep.folded}
    if not eligible_players:
        raise EngineStateError(f"{pot} has no eligible players")
    winning_key = max(eligible_players.values(), key=lambda gph: (gph.hand_rank, gph.tie_key))
    winners_info: dict[Player, HandEval] = {
        ep: gph
        for ep, gph in eligible_players.items()
        if (gph.hand_rank, gph.tie_key) == winning_key
    }
    print(f"{pot} winning key: {winning_key}")
    return winners_info

def _split_pot(hand: Hand, pot: Pot, winners_info: dict[Player, HandEval]):
    def _seats_left_of_dealer(pl: Player) -> int:
        left = (pl.seat - hand.buttons.dealer_button) % hand.table.num_of_seats
        return hand.table.num_of_seats if left == 0 else left

    winners = sorted(winners_info.keys(), key=_seats_left_of_dealer)
    pot_share, remaining_chips = divmod(pot.amount, len(winners))
    print(f"{pot} is split between {len(winners)} players: ")

    for i, wp in enumerate(winners):
        extra = 1 if i < remaining_chips else 0  # odd chips go left of dealer first
        wp.stack += pot_share + extra
        pot.winning_players.add(wp)
        wh = winners_info[wp]
        print(f"   {wp} wins {pot_share + extra} with: {wh.hand_rank}: {' '.join(map(str, wh.hand_cards))}")
        if extra == 1:
            print(f"      (Uneven Split: {wp.name} awarded 1 remaining chip)")

def _award_pot(hand: Hand, pot: Pot):
    winners_info = _determine_winners(hand, pot)

    if len(winners_info) <= 0:
        raise EngineStateError(f"{pot} with {pot.amount} chips has no winning players: eligible:{pot.eligible_players}")

    if len(winners_info) == 1:
        wp, wh = next(iter(winners_info.items()))
        wp.stack += pot.amount
        pot.winning_players.add(wp)
        print(f"{pot} is awarded to {wp}, with: {wh.hand_rank}: {' '.join(map(str, wh.hand_cards))}")
        return
    _split_pot(hand, pot, winners_info)

def showdown(hand: Hand):
    hand.game_state = GameState.SHOWDOWN
    for pot in hand.pots:
        if pot.amount == 0:
            pot.discard = True
            print(f"{pot} has no chips")
            continue
        _award_pot(hand, pot)
