# src/holdem/engine/game.py

from __future__ import annotations
from typing import ClassVar, NewType, TYPE_CHECKING
from bisect import bisect_right # next_left_player_index
from uuid import UUID, uuid7 # type: ignore[attr-defined]

from ..core.enums import GameState, Position
from ..core.cards import Card, Deck
from ..table.buttons_blinds import advance_buttons_post_blinds
from ..table.peek import peek_buttons
from ..table.pots import Pot
from .betting import orchestrate_betting_round
from .allocate_pots import chips_to_pots
from .showdown import showdown

if TYPE_CHECKING:
    from ..table.table import Table
    from ..table.player import Player
    from ..table.buttons_blinds import Buttons

__all__ = ["Hand", "HandID"]

HandID = NewType("HandID", UUID)

def _new_hand_id() -> HandID:
    return HandID(uuid7())

class Hand:
    __slots__ = (
        "_hand_id",
        "table", "hand_number", "game_state",
        "small_blind_amt", "big_blind_amt",
        "buttons", "headsup",
        "_num_of_pots", "pots",
        "players_in_hand", "n_players_in_hand", "positions",
        "forced_folds",
        "highest_bet", "raise_amt", "n_raises",
        "deck", "mucked_pile", "community_board", "burn_cards", "end_hand",
    )
    HOLDEM_POSITIONS: ClassVar[tuple[Position, ...]] = (
        Position.BUTTON,
        Position.CUTOFF,
        Position.HIJACK,
        Position.LOJACK,
        Position.UNDER_THE_GUN_2,
        Position.UNDER_THE_GUN_1,
        Position.UNDER_THE_GUN
    )
    num_of_hands: ClassVar[int] = 0

    def __init__(self, table: Table):
        # Hand setup
        self._hand_id: HandID = _new_hand_id()

        self.table: Table = table
        self.hand_number: int = Hand.num_of_hands + 1
        self.game_state: GameState = GameState.SETUP

        self.small_blind_amt: int = self.table.small_blind_amt
        self.big_blind_amt: int = self.table.big_blind_amt

        peek_result = peek_buttons(tbl=self.table)
        self.buttons: Buttons = peek_result.buttons
        self.headsup: bool = peek_result.is_heads_up

        self._num_of_pots: int = 0
        self.pots: list[Pot] = []

        self.players_in_hand: list[Player] = []
        self.n_players_in_hand: int = 0
        self.positions: dict[Position, Player] = {}

        self.forced_folds: set[Player] = set()

        self.highest_bet: int = 0
        self.raise_amt: int = 0
        self.n_raises: dict[GameState, int] = { # Keep track of 3bet pot, 4bet pot etc.
            GameState.PRE_FLOP: 0,
            GameState.FLOP: 0,
            GameState.TURN: 0,
            GameState.RIVER: 0
        }

        self.deck: Deck = Deck()
        self.mucked_pile: set[Card] = set()
        self.community_board: list[Card] = []
        self.burn_cards: list[Card] = []
        self.end_hand: bool = False

    @property
    def hand_id(self) -> HandID:
        return self._hand_id          # read-only

    def allocate_pot_number(self) -> int:
        n = self._num_of_pots
        self._num_of_pots += 1
        return n

    def _add_ante_to_pot(self, amount: int) -> None:
        self.pots[0].add(amount)

    def tot_value_pot(self) -> int:
        current_bets_val = sum(pl.current_bet for pl in self.players_in_hand)
        past_pots_val = sum(p.amount for p in self.pots)
        return current_bets_val + past_pots_val

    def get_players_in_hand(self) -> list[Player]:
        return [occupant for seat, occupant in self.table.seats.items() if self.table.eligible(seat)]

    @staticmethod
    def get_index_map(_players_list: list[Player]) -> dict[int, int]:
        return {pl.seat: index for index, pl in enumerate(_players_list)}

    def next_left_player_index(self, seat: int, _players_list: list[Player], index_map: dict[int, int] | None = None) -> int:
        pl_seats = sorted(pl.seat for pl in _players_list)
        j = bisect_right(pl_seats, seat)
        next_seat = pl_seats[0] if j == len(pl_seats) else pl_seats[j]
        idx_map = index_map or self.get_index_map(_players_list)
        return idx_map[next_seat]

    def assign_position(self) -> dict[Position, Player]:
        # Implement Hold'em rules for position ordering
        # There is always a Button and Big Blind. Additional positions add the Small Blind then add positions from the Button anti-clockwise.
        # Lastly, UTG+1 (and UTG+2) only appears when there is already a UTG (and UTG+1)
        m = self.n_players_in_hand
        if self.headsup:
            hand_positions = [Position.BIG_BLIND, Position.BUTTON]
        else:
            hand_positions = list(Hand.HOLDEM_POSITIONS[:(m - 2)])
            hand_positions.extend([Position.BIG_BLIND, Position.SMALL_BLIND])
            hand_positions.reverse()
            if m == 8:
                hand_positions[hand_positions.index(Position.UNDER_THE_GUN_1)] = Position.UNDER_THE_GUN
                hand_positions[hand_positions.index(Position.UNDER_THE_GUN_2)] = Position.UNDER_THE_GUN_1
            elif m == 7:
                hand_positions[hand_positions.index(Position.UNDER_THE_GUN_2)] = Position.UNDER_THE_GUN

        positions: dict[Position, Player] = {}
        idx_map = self.get_index_map(self.players_in_hand)
        bu_index = idx_map[self.buttons.dealer_button]
        for i, pos in enumerate(hand_positions):
            pl = self.players_in_hand[(bu_index + 1 + i) % m]
            positions[pos] = pl
            pl.position = pos
        return positions

    def deal_hole_cards(self):
        for _ in range(2):
            for pl in self.positions.values():
                pl.draw(self.deck)

    def forced_fold(self, pl: Player):
        """Force a player to fold immediately (out-of-turn fold or leave/disconnect)."""
        if not pl.folded:
            pl.fold()
        if pl.hole_cards:
            self.mucked_pile.update(pl.hole_cards)
            pl.hole_cards.clear()
        for pot in self.pots:
            pot.eligible_players.discard(pl)
        # self.pots[-1].add(pl.current_bet)
        # pl.current_bet = 0
        self.forced_folds.add(pl)

    def reset_for_next_street(self, _players_in_round: list[Player]):
        for pl in _players_in_round:
            pl.reset_for_new_street()
        self.highest_bet = 0
        self.raise_amt = 0

    def discard_empty_pots(self):
        i = 0
        while self.pots and self.pots[-1 - i].amount == 0:
            self.pots[-1].discard = True
            print(f"{self.pots[-1]} discarded")
            if len(self.pots) == 1:
                break
            else:
                i += 1

    def award_pots_without_showdown(self, winner):
        self.discard_empty_pots()
        for pot in self.pots:
            if pot.discard:
                continue
            winner.stack += pot.amount
            print(f"{pot} awarded to {winner} on the {self.game_state} without showdown")

    def betting_round(self, players_in_round: list[Player]):
        orchestrate_betting_round(self, players_in_round)

        # check if any bets
        if self.highest_bet > 0:
            chips_to_pots(self, players_in_round)
        self.reset_for_next_street(players_in_round)

        # if one player remaining, award pots and end hand
        if sum(not pl.folded for pl in self.players_in_hand) == 1:
            winning_player = next(pl for pl in self.players_in_hand if not pl.folded)
            self.award_pots_without_showdown(winning_player)
            self.end_hand = True

    def pre_flop_betting_round_check(self) -> bool:
        """
        Return True if a pre-flop betting round should occur.
        This method is to handle edge cases where no betting round occurs pre-flop, due to the blinds putting player(s)
        all-in. E.g. the small blind has 1 chip and posting the SB puts them all-in.
        No betting round occurs if:
         A) It is Heads-up and;
         B) 1) the small blind is all-in, or
            2) the big blind is all-in for an amount lower or equal to the small blind.
        Or
         C) It is multi-way but non-all-in players are < 2, and if 1 is non-all-in, their current bet is >= highest bet.
        In these cases, no decision can be made. The all-ins is automatically called by the blinds. The board cards are
        dealt and the hand goes to showdown, with the pot being what the blind all-ins were.
        """
        if self.headsup:
            bb = self.positions[Position.BIG_BLIND]
            sb = self.positions[Position.BUTTON]

            if sb.all_in:
                return False
            elif bb.all_in and bb.current_bet <= sb.current_bet:
                return False
            else:
                return True

        non_all_in = [pl for pl in self.players_in_hand if not pl.all_in]
        if len(non_all_in) == 0:
            return False
        elif len(non_all_in) == 1:
            active_pl = non_all_in[0]
            return active_pl.current_bet < self.highest_bet
        else:
            return True

    def pre_flop(self):
        self.game_state = GameState.PRE_FLOP
        if self.pre_flop_betting_round_check():
            self.betting_round(self.players_in_hand)
        else:
            chips_to_pots(self, self.players_in_hand)
            self.reset_for_next_street(self.players_in_hand)
            print(f"No Pre-Flop betting round, as posted blinds put players all-in")

    def deal_flop(self):
        self.burn_cards.extend(self.deck.draw())
        self.community_board.extend(self.deck.draw(3))

    def show_board(self) -> str:
        msg: str = "------ Community Cards ------\n"
        if not self.community_board:
            msg += " PREFLOP; No community cards dealt yet\n"
        else:
            msg += "".join(f"   {c}" for c in self.community_board) + "\n"
        msg += "-----------------------------"
        return msg

    def flop(self):
        self.game_state = GameState.FLOP
        flop_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_flop()
        print(self.show_board())
        if len(flop_players) > 1:
            self.betting_round(flop_players)

    def deal_street(self):
        # For dealing Turn and River cards (commonly referred to as "streets")
        self.burn_cards.extend(self.deck.draw())
        self.community_board.extend(self.deck.draw())

    def turn(self):
        self.game_state = GameState.TURN
        turn_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        print(self.show_board())
        if len(turn_players) > 1:
            self.betting_round(turn_players)

    def river(self):
        self.game_state = GameState.RIVER
        river_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        print(self.show_board())
        if len(river_players) > 1:
            self.betting_round(river_players)

    def run_hand(self):
        self.pre_flop()
        if self.end_hand: return

        self.flop()
        if self.end_hand: return

        self.turn()
        if self.end_hand: return

        self.river()
        if self.end_hand: return

        showdown(self)

    def end_hand_reset(self):
        self.game_state = GameState.END_HAND
        for p in self.players_in_hand:
            p.reset_for_new_hand()
        self.forced_folds.clear()
        self.end_hand = True
        Hand.num_of_hands += 1
        print(f"\n\n   END of HAND {self.hand_number}   \n\n")

    def start(self):
        bu_ante = advance_buttons_post_blinds(tbl=self.table)
        assert bu_ante.buttons == self.buttons                   # Remove later

        self.pots = [Pot(hand=self)]
        self.pots[0].add(bu_ante.ante.amount)                    # add ante to the pot

        self.players_in_hand = self.get_players_in_hand()
        self.n_players_in_hand = len(self.players_in_hand)
        self.positions = self.assign_position()

        self.highest_bet = max(pl.current_bet for pl in self.players_in_hand)
        self.raise_amt = self.big_blind_amt
        self.n_raises[GameState.PRE_FLOP] = 1

        self.deck.shuffle()
        self.deal_hole_cards()

        print(self.table.print_table())  # Can remove later

        # Begin hand
        self.run_hand()
        self.end_hand_reset()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hand):
            return NotImplemented
        return self.hand_id == other.hand_id

    def __hash__(self) -> int:
        return hash(self.hand_id)

    # _hand_id is immutable
    def __setattr__(self, name: str, value) -> None:
        if name == "_hand_id" and hasattr(self, "_hand_id"):
            raise AttributeError("_hand_id / hand_id is immutable once set")
        object.__setattr__(self,name, value)

    def __repr__(self):
        return f"Hand: {self.hand_id}"

    def __str__(self):
        return f"Hand {self.hand_number}"