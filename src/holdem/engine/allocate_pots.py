# src/holdem/engine/allocate_pots.py

from __future__ import annotations
from typing import TYPE_CHECKING

from ..core import GameState
from ..table.pots import Pot

if TYPE_CHECKING:
    from ..table.player import Player
    from .game import Hand

__all__ = ["chips_to_pots"]

def _return_uncalled_bet(lone_pl: Player, _second_highest_bet: int) -> int:
    uncalled_portion = lone_pl.current_bet - _second_highest_bet
    lone_pl.stack += uncalled_portion
    print(f"Returned bet of {uncalled_portion} for player: {lone_pl}")
    return uncalled_portion

def _retrieve_bets(players: list[Player],
                   pot: Pot,
                   *,
                   prev_level: int=0,
                   level: int=0,
                   side: bool=False) -> tuple[int, int, bool, Player | None]:

    def _pl_contribution(pl: Player) -> int:
        return (min(pl.current_bet, level) - prev_level) if side else pl.current_bet

    bets_contributions: int = 0
    live_players: list[Player] = []
    highest_bet = second_highest_bet = 0

    for pl in players:
        bets_contributions += _pl_contribution(pl)
        if not pl.folded:
            pot.eligible_players.add(pl)
            live_players.append(pl)

        # retrieve second highest bet
        if pl.current_bet > highest_bet:
            highest_bet, second_highest_bet = pl.current_bet, highest_bet
        elif pl.current_bet > second_highest_bet:
            second_highest_bet = pl.current_bet

    folded_to_winner: bool = len(live_players) == 1
    winner: Player | None = live_players[0] if folded_to_winner else None
    return bets_contributions, second_highest_bet, folded_to_winner, winner

def _handle_side_pots(hand: Hand, players_in_round: list[Player], active_pot_index: int):
    all_in_bets = set(pl.current_bet for pl in players_in_round if pl.all_in)
    max_bet, max_all_in_bet = max(pl.current_bet for pl in players_in_round), max(all_in_bets)
    bets_occurred_after_all_in = max_bet > max_all_in_bet
    levels = sorted(all_in_bets.union({max_bet}))
    remaining: list[Player] = players_in_round
    prev_level = 0

    for i, level in enumerate(levels):
        is_last: bool = (i == len(levels) - 1)
        pot: Pot = hand.pots[active_pot_index]

        if is_last and bets_occurred_after_all_in:
            print("bets occurred after final all-in")

        total_bets, shb, folded_to_winner, winner = _retrieve_bets(remaining,
                                                                   pot,
                                                                   prev_level=prev_level,
                                                                   level=level,
                                                                   side=True)
        if is_last and folded_to_winner:
            total_bets -= _return_uncalled_bet(winner, shb)

        pot.add(total_bets)
        print(pot)

        if is_last and not bets_occurred_after_all_in:
            pot.capped = True
            if hand.game_state != GameState.RIVER:
                to_showdown = sum(not pl.all_in for pl in remaining if not pl.folded) < 2
                if to_showdown:
                    print("All-in called")
                    print(f"From the {hand.game_state}, run out the board and advance to showdown")
                else:
                    print("players remain who aren't all-in after calling all-in")
                    hand.pots.append(Pot(hand=hand))
                    active_pot_index += 1

        remaining = [pl for pl in remaining if (pl.current_bet - level) > 0]

        if not is_last:
            pot.capped = True

        if len(remaining) > 1:
            hand.pots.append(Pot(hand=hand))
            active_pot_index += 1
        elif len(remaining) == 1: # skip the last level if it only contains one player, return uncalled bet
            _return_uncalled_bet(remaining[0], level)
            return

        prev_level = level

def chips_to_pots(hand: Hand, players_in_round: list[Player]):
    active_pot_index = len(hand.pots) - 1

    all_in_players_exist: bool = any(p.all_in for p in players_in_round)
    if all_in_players_exist:
        _handle_side_pots(hand, players_in_round, active_pot_index)
    else:
        pot: Pot = hand.pots[active_pot_index]
        total_bets, second_highest_bet, folded_to_winner, winner = _retrieve_bets(players_in_round, pot)

        if folded_to_winner:
            total_bets -= _return_uncalled_bet(winner, second_highest_bet)

        pot.add(total_bets)
        print(pot)
