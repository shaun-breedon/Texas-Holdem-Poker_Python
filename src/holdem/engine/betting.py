# src/holdem/engine/betting.py

from __future__ import annotations
from typing import TYPE_CHECKING, FrozenSet
from collections import deque # Betting round

from ..core import Action, GameState
from ..table.pots import Pot
from ..strategies.base import View, Decision
from ..strategies.features import evaluate_hand_features
from ..utils.errors import EngineStateError

if TYPE_CHECKING:
    from ..table.player import Player
    from .game import Hand

__all__ = ["run_betting_round"]

NO_BET: FrozenSet[Action]            = frozenset({Action.CHECK, Action.BET, Action.FOLD, Action.ALL_IN})
FACING_BET_OPEN: FrozenSet[Action]   = frozenset({Action.CALL, Action.RAISE, Action.FOLD, Action.ALL_IN})
FACING_BET_CLOSED: FrozenSet[Action] = frozenset({Action.CALL, Action.FOLD}) # can go all-in if it's below the call amt

def _get_starting_player(hand: Hand, players_in_round: list[Player]) -> int:
    # in headsup, starts on the dealer button (who also posts the small blind).
    # else, if pre-flop, starts left of Big Blind
    # starts left of dealer button on later streets
    idx_map = hand.get_index_map(players_in_round)
    if hand.headsup and hand.game_state == GameState.PRE_FLOP:
        start = idx_map[hand.buttons.dealer_button]
    elif hand.game_state == GameState.PRE_FLOP:
        start = hand.next_left_player_index(hand.buttons.big_blind_button, players_in_round, idx_map)
    else:
        start = hand.next_left_player_index(hand.buttons.dealer_button, players_in_round, idx_map)
    return start

def _apply_forced_folds(hand: Hand, order: deque[Player], active: set[Player], live: set[Player], pending: set[Player]):
    while hand.forced_folds:
        pl = hand.forced_folds.pop()
        active.discard(pl)
        live.discard(pl)
        pending.discard(pl)
        try:
            order.remove(pl)
        except ValueError:
            pass

def _get_hand_betting_info(hand: Hand, pl: Player, to_call: int, open_action: bool, legal_actions: set[Action]) -> View:
    pl_hand = pl.get_player_hand(hand.community_board)
    hand_properties = evaluate_hand_features(
        street=hand.game_state,
        hole_cards=tuple(pl.hole_cards),
        board=tuple(hand.community_board),
        hand_rank=pl_hand.hand_rank
    )
    betting_info = View(
        street=hand.game_state,
        pot=hand.tot_value_pot(),
        highest_bet=hand.highest_bet,
        to_call=to_call,
        raise_amount=hand.raise_amt,
        n_raises=hand.n_raises,
        open_action=open_action,
        board=tuple(hand.community_board),
        legal=frozenset(legal_actions),
        position=pl.position,
        stack=pl.stack,
        current_bet=pl.current_bet,
        hole_cards=tuple(pl.hole_cards),
        hand_rank=pl_hand.hand_rank,
        hand_cards=pl_hand.hand_cards,
        fx=hand_properties
    )
    return betting_info

def _check_if_all_in(pl: Player, pl_decision: Decision, to_call: int) -> Decision:
    if pl_decision.action == Action.CALL and pl.stack < to_call:
        pl_decision = Decision(Action.ALL_IN)

    if pl_decision.action in {Action.RAISE, Action.BET} and pl.stack < pl_decision.amount:
        pl_decision = Decision(Action.ALL_IN)

    return pl_decision

def _folded(pl: Player, hand: Hand, order: deque[Player], active: set[Player], live: set[Player], pending: set[Player]):
    pl.fold()
    for pot in hand.pots:
        pot.eligible_players.discard(pl)
    hand.mucked_pile.update(pl.hole_cards)
    pl.hole_cards.clear()
    active.remove(pl)
    live.remove(pl)
    pending.remove(pl)
    order.popleft()

def _check_call(pl: Player, dec: Decision, to_call: int, order: deque[Player], pending: set[Player]):
    if dec.action == Action.CHECK:
        if to_call != 0:
            raise EngineStateError(f"Cannot CHECK when facing a bet. to_call={to_call}")
        pl.check()
    else:
        pl.call(to_call)
    pending.remove(pl)
    order.rotate(-1)

def _bet_raise(pl: Player,
               dec: Decision,
               hand: Hand,
               to_call: int,
               order: deque[Player],
               active: set[Player],
               pending: set[Player],
               legal_actions: set[Action]):
    if dec.action == Action.RAISE:
        if to_call == 0:
            raise EngineStateError("Cannot RAISE when no bet; use BET.")
        pl.raise_to(dec.amount)
        full_raise = (pl.current_bet - hand.highest_bet) >= hand.raise_amt
        if not full_raise:
            msg = f"{pl.name} bet of {pl.current_bet} below minimum raise of {hand.raise_amt} on top of the highest bet of {hand.highest_bet}"
            raise EngineStateError(msg)
        hand.n_raises[hand.game_state] += 1
    else:
        if to_call != 0:
            raise EngineStateError(f"Cannot BET when facing a bet; use RAISE. to_call={to_call}")
        if dec.amount < hand.big_blind_amt:
            raise EngineStateError(f"{pl} bet of {dec.amount} must be greater than the big blind: {hand.big_blind_amt}")
        pl.bet(dec.amount)
    hand.raise_amt = pl.current_bet - hand.highest_bet
    hand.highest_bet = pl.current_bet
    pending.clear()
    pending.update(active - {pl})
    order.rotate(-1)
    legal_actions.clear()
    legal_actions.update(set(FACING_BET_OPEN))

def _all_in(pl: Player,
            hand: Hand,
            order: deque[Player],
            active: set[Player],
            pending: set[Player],
            legal_actions: set[Action]):
    pl.go_all_in()
    bet_increased = pl.current_bet > hand.highest_bet
    full_raise = (pl.current_bet - hand.highest_bet) >= hand.raise_amt
    if bet_increased:
        if full_raise:
            hand.raise_amt = pl.current_bet - hand.highest_bet
            hand.n_raises[hand.game_state] += 1
            legal_actions.clear()
            legal_actions.update(set(FACING_BET_OPEN))
        hand.highest_bet = pl.current_bet
        pending.clear()
        pending.update(active - {pl})
    else:
        pending.remove(pl)
    active.remove(pl)
    order.popleft()

def _orchestrate_betting_round(hand: Hand, players_in_round: list[Player]):
    start_idx = _get_starting_player(hand, players_in_round)

    order: deque[Player] = deque(players_in_round) # create a player queue from collections import
    order.rotate(-start_idx)        # rotate queue to start from starting player
    active = set(players_in_round)  # not folded, not all-in
    live = set(players_in_round)    # not folded
    pending = set(players_in_round) # yet to act

    legal_actions: set[Action] = set(FACING_BET_OPEN) if hand.game_state == GameState.PRE_FLOP else set(NO_BET)

    while len(live) > 1 and pending:

        _apply_forced_folds(hand, order, active, live, pending)
        if len(live) <= 1 or not pending:
            break

        player_to_act = order[0]

        to_call: int = hand.highest_bet - player_to_act.current_bet
        if to_call < 0:
            msg = f"to_call < 0: highest_bet={hand.highest_bet}-{player_to_act}current_bet={player_to_act.current_bet}"
            raise EngineStateError(msg)

        open_action: bool = to_call >= hand.raise_amt
        if not open_action:
            legal_actions = set(FACING_BET_CLOSED)

        betting_info = _get_hand_betting_info(hand=hand,
                                              pl=player_to_act,
                                              to_call=to_call,
                                              open_action=open_action,
                                              legal_actions=legal_actions)

        pl_decision = player_to_act.strategy.decide(betting_info)
        pl_decision = _check_if_all_in(player_to_act, pl_decision, to_call)

        if pl_decision.action == Action.FOLD:
            _folded(player_to_act, hand, order, active, live, pending)
            continue

        if pl_decision.action in {Action.CHECK, Action.CALL}:
            _check_call(player_to_act, pl_decision, to_call, order, pending)
            continue

        if pl_decision.action in {Action.RAISE, Action.BET}:
            _bet_raise(player_to_act, pl_decision, hand, to_call, order, active, pending, legal_actions)
            continue

        if pl_decision.action == Action.ALL_IN:
            _all_in(player_to_act, hand, order, active, pending, legal_actions)
            continue

# ------------------------------ Pot Handling -------------------------------------------------------
def _calculate_bets(hand: Hand, players: list[Player], index: int, previous: int=0, amt: int=0, looping: bool=False):
    bets_value = 0
    live_players = []
    highest_bet = second_highest_bet = 0
    pot = hand.pots[index]

    def _pl_contribution(pl: Player) -> int:
        return (min(pl.current_bet, amt) - previous) if looping else (pl.current_bet - previous)

    for pl in players:
        bets_value += _pl_contribution(pl)
        if not pl.folded:
            pot.eligible_players.add(pl)
            live_players.append(pl)

        # retrieve second highest bet
        if pl.current_bet > highest_bet:
            highest_bet, second_highest_bet = pl.current_bet, highest_bet
        elif pl.current_bet > second_highest_bet:
            second_highest_bet = pl.current_bet

    if len(live_players) == 1:
        lone_pl = live_players[0]
        lone_pl.stack += lone_pl.current_bet - second_highest_bet       # return uncalled bet
        bets_value -= lone_pl.current_bet - second_highest_bet
        print(
            f"Returned bet of {lone_pl.current_bet - second_highest_bet} for player: {lone_pl}")

    pot.add(bets_value)
    print(hand.pots[index])

def _handle_side_pots(hand: Hand, players_in_round: list[Player], active_pot_index: int):
    all_in_bets = set(p.current_bet for p in players_in_round if p.all_in)
    max_bet, max_all_in_bet = max(p.current_bet for p in players_in_round), max(all_in_bets)
    bets_occurred_after_all_in = max_bet > max_all_in_bet
    levels = sorted(all_in_bets.union({max_bet}))
    remaining: list[Player] = players_in_round
    prev = 0

    for i, amount in enumerate(levels):
        is_last = (i == len(levels) - 1)

        if is_last and bets_occurred_after_all_in:
            print("bets occurred after final all-in")
        _calculate_bets(hand, remaining, active_pot_index, prev, amount, True)

        if is_last and not bets_occurred_after_all_in:
            print("players remain who aren't all-in after calling all-in")
            hand.pots[active_pot_index].capped = True

        remaining = [p for p in remaining if (p.current_bet - amount) > 0]
        prev = amount
        if not is_last:
            hand.pots[active_pot_index].capped = True
        if len(remaining) > 1:
            hand.pots.append(Pot(hand=hand))
            active_pot_index += 1
        elif len(remaining) == 1:
            lone_pl = remaining[0]
            lone_pl.stack += lone_pl.current_bet - prev
            print(f"Returned bet of {lone_pl.current_bet - prev} for player: {lone_pl}")
            break

def _allocate_pots(hand: Hand, players_in_round: list[Player]):
    active_pot_index = len(hand.pots) - 1
    all_in_players = set(p.all_in for p in players_in_round)
    if any(all_in_players):
        _handle_side_pots(hand, players_in_round, active_pot_index)
    else:
        _calculate_bets(hand, players_in_round, active_pot_index)

    while hand.pots and hand.pots[-1].amount == 0:
        # Rethink deletion of pots, now tht you have ID's
        hand.pots[-1].discard = True
        hand.pots.pop()
        # hand._num_of_pots -= 1
# ------------------------------------ End Pot Handling ------------------------------------------------------------

def run_betting_round(hand: Hand, players_in_round: list[Player]):
    _orchestrate_betting_round(hand, players_in_round)

    # check if any bets
    if hand.highest_bet > 0:
        _allocate_pots(hand, players_in_round)
    hand.reset_for_next_street(players_in_round)

    # if one player remaining, award pots and end hand
    if sum(not pl.folded for pl in hand.players_in_hand) == 1:
        winning_player = next(pl for pl in hand.players_in_hand if not pl.folded)
        hand.award_pots_without_showdown(winning_player)
        hand.end_hand = True