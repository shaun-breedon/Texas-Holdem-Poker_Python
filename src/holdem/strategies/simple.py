# src/holdem/strategies/simple.py

from __future__ import annotations
from typing import TYPE_CHECKING

from ..core.enums import Rank, GameState, HandRank, Action
from .base import View, Decision

if TYPE_CHECKING:
    from ..core.cards import Card
    from .features import Features

__all__ = ["CallingStation", "Nit", "Tag", "Lag"]

class CallingStation:
    __slots__ = ()

    @staticmethod
    def _good_hand(hole: tuple[Card, Card], hand_rank: HandRank) -> bool:
        a, b = hole
        pair_or_better: bool = hand_rank >= HandRank.PAIR
        high_card: bool = max(a.rank, b.rank) > Rank.TEN
        suited: bool = a.suit == b.suit
        connected_vals: set[int] = {a.rank + r for r in range(-3, 4) if r != 0 and 1 <= a.rank + r <= 14}
        connected: bool = b.rank in connected_vals
        good = pair_or_better or high_card or suited or connected
        return good

    def decide(self, view: View) -> Decision:
        good = self._good_hand(view.hole_cards, view.hand_rank)

        if view.street == GameState.PRE_FLOP:
            if view.limp_fold_to_bb:
                return Decision(Action.CHECK)
            if view.n_raises[GameState.PRE_FLOP] >= 4:
                return Decision(Action.CALL) if good else Decision(Action.FOLD)
            if view.n_raises[GameState.PRE_FLOP] == 1 and good and Action.RAISE in view.legal:
                return Decision(Action.RAISE, round(view.pot*3))
            return Decision(Action.CALL)

        if Action.CHECK in view.legal:
            return Decision(Action.CHECK)
        return Decision(Action.CALL)

class Nit:
    __slots__ = ()

    @staticmethod
    def _good_hand(hole: tuple[Card, Card], hand_rank: HandRank) -> bool:
        a, b = hole
        pair_or_better: bool = hand_rank >= HandRank.PAIR
        ace: bool = Rank.ACE in (a.rank, b.rank)
        suited: bool = a.suit == b.suit and max(a.rank, b.rank) >= Rank.QUEEN
        connected_vals: set[int] = {a.rank + r for r in range(-1, 2) if r != 0 and 1 <= a.rank + r <= 14}
        connected: bool = b.rank in connected_vals and max(a.rank, b.rank) >= Rank.NINE
        good = pair_or_better or ace or suited or connected
        return good

    def decide(self, view: View) -> Decision:
        good = self._good_hand(view.hole_cards, view.hand_rank)

        if view.street == GameState.PRE_FLOP:
            if view.limp_fold_to_bb:
                return Decision(Action.CHECK)
            return Decision(Action.CALL) if good and view.n_raises[GameState.PRE_FLOP] <= 3 else Decision(Action.FOLD)

        if Action.CHECK in view.legal:
            return Decision(Action.CHECK)
        return Decision(Action.CALL) if good else Decision(Action.FOLD)

class Tag:
    __slots__ = ()

    @staticmethod
    def _good_hand(hole: tuple[Card, Card], hand_rank: HandRank) -> bool:
        a, b = hole
        pair_or_better: bool = hand_rank >= HandRank.PAIR
        ace: bool = Rank.ACE in (a.rank, b.rank)
        suited: bool = a.suit == b.suit and max(a.rank, b.rank) >= Rank.QUEEN
        connected_vals: set[int] = {a.rank + r for r in range(-1, 2) if r != 0 and 1 <= a.rank + r <= 14}
        connected: bool = b.rank in connected_vals and max(a.rank, b.rank) >= Rank.SIX
        good: bool = pair_or_better or ace or suited or connected
        return good

    def decide(self, view: View) -> Decision:
        good = self._good_hand(view.hole_cards, view.hand_rank)

        if view.street == GameState.PRE_FLOP:
            if view.limp_fold_to_bb:
                return Decision(Action.RAISE, round(view.pot * 3)) if good else Decision(Action.CHECK)
            if not good:
                return Decision(Action.FOLD)
            if not view.open_action:
                return Decision(Action.CALL)
            elif view.chips_to_min_raise > view.stack:
                return Decision(Action.ALL_IN, view.stack)
            else:
                return Decision(Action.RAISE, round(view.highest_bet * 5))

        if not view.open_action:
            return Decision(Action.CALL)
        if Action.BET in view.legal:
            return Decision(Action.BET, round(view.pot * 0.666))
        elif view.chips_to_min_raise > view.stack:
            return Decision(Action.ALL_IN, view.stack)
        else:
            return Decision(Action.RAISE, view.pot)

class Lag:
    __slots__ = ()

    @staticmethod
    def _good_hand(hole: tuple[Card, Card], hand_rank: HandRank) -> bool:
        a, b = hole
        pair_or_better: bool = hand_rank >= HandRank.PAIR
        high_card: bool = max(a.rank, b.rank) > Rank.TEN
        suited: bool = a.suit == b.suit
        connected_vals: set[int] = {a.rank + r for r in range(-3, 4) if r != 0 and 1 <= a.rank + r <= 14}
        connected: bool = b.rank in connected_vals
        good = pair_or_better or high_card or suited or connected
        return good

    def decide(self, view: View) -> Decision:
        good = self._good_hand(view.hole_cards, view.hand_rank)

        if view.street == GameState.PRE_FLOP:
            if view.limp_fold_to_bb:
                return Decision(Action.CHECK)
            if not good:
                return Decision(Action.CALL)
            if not view.open_action:
                return Decision(Action.CALL)
            elif view.chips_to_min_raise > view.stack:
                return Decision(Action.ALL_IN, view.stack)
            else:
                return Decision(Action.RAISE, round(view.highest_bet * 5))

        if not view.open_action:
            return Decision(Action.CALL)
        if Action.BET in view.legal:
            return Decision(Action.BET, round(view.pot * 0.333))
        elif view.chips_to_min_raise > view.stack:
            return Decision(Action.ALL_IN, view.stack)
        else:
            return Decision(Action.RAISE, view.pot)