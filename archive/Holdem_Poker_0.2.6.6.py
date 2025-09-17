from enum import Enum, IntEnum
from functools import total_ordering
import random

class Suit(Enum):
    SPADES = '♠'
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'

    def __str__(self):
        return self.value

_face_cards = {
        10: 'T',
        11: 'J',
        12: 'Q',
        13: 'K',
        14: 'A'
    }

class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def __str__(self):
        return _face_cards.get(self.value, str(self.value))

class HandRank(IntEnum):
    STRAIGHTFLUSH = 9
    QUADS = 8
    FULLHOUSE = 7
    FLUSH = 6
    STRAIGHT = 5
    TRIPS = 4
    TWOPAIR= 3
    PAIR = 2
    HIGHCARD = 1

    def __str__(self):
        return self.name

@total_ordering
class Card:
    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"Card(Rank.{self.rank.name}, Suit.{self.suit.name})"

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __eq__(self, other):
        return (
                isinstance(other, Card)
                and self.rank == other.rank
                and self.suit == other.suit
        )

    def __lt__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank < other.rank

    def __hash__(self):
        return hash((self.rank, self.suit))

class Deck:
    def __init__(self):
        self.cards = [Card(r, s) for s in Suit for r in Rank]

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, n=1) -> list[Card]:
        if not self.cards:
            raise ValueError("Deck is empty.")
        if n <= 0:
            raise ValueError("Must draw at least one card.")
        elif n > len(self.cards):
            raise ValueError("Not enough cards left to draw.")
        drawn, self.cards = self.cards[-n:], self.cards[:-n]
        return drawn

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return "Deck()"

    def __str__(self):
        return ' '.join(str(c) for c in self.cards)

class Table:
    wait_list = []
    tables = []

    @classmethod
    def num_of_tables(cls) -> int:
        return len(cls.tables)

    def __init__(self, num_of_seats: int=9, small_blind_amt: int=2, big_blind_amt: int=3):
        if num_of_seats < 2:
            raise ValueError("A table must have at least 2 seats.")
        self.num_of_seats: int = num_of_seats
        self.small_blind_amt: int = small_blind_amt
        self.big_blind_amt: int = big_blind_amt

        self.seats: 'dict[int, Player | None]' = {s: None for s in range(1, self.num_of_seats + 1)}
        self.dealer_button: int | None = None
        self.big_blind_button: int | None = None
        self.small_blind_button: int | None = None
        self.pot_ante: int = 0

        Table.tables.append(self)
        self.table_number: int = Table.num_of_tables()

    def seat_player(self, player: 'Player'):
        if player.seat is not None:
            raise ValueError(f"Player {player.name} is already seated.")
        found_seat = False
        for seat, occupant in self.seats.items():
            if occupant is None:
                self.seats[seat] = player
                player.seat = seat
                player.table = self
                found_seat = True
                break
        if not found_seat:
            Table.wait_list.append(player)

    def leave_seat(self, seat_number: int, session_end: bool=False):
        self.seats[seat_number] = None
        if Table.wait_list and not session_end:
            next_player = Table.wait_list.pop(0)
            self.seat_player(next_player)

    def present(self, seat: int) -> bool:
        pl = self.seats[seat]
        return pl is not None and not pl.on_break

    def eligible(self, seat: int) -> bool:
        pl = self.seats[seat]
        return pl is not None and not pl.on_break and not pl.owes_bb and not pl.owes_sb

    def is_headsup(self) -> bool:
        n_present = sum(self.present(s) for s in self.seats)
        if n_present < 2:
            raise RuntimeError("Need ≥2 present players to move the button")
        elif n_present == 2:
            return True
        else:
            return False

    def post_small_blind(self, pl: 'Player', ante: bool=False, owed: bool=False, in_blinds: bool=True):
        if ante:
            self.pot_ante += pl.pip(self.small_blind_amt, ante=True)
        else:
            pl.pip(self.small_blind_amt)
        if in_blinds:
            pl.paid_sb = True
        pl.owes_sb = False
        print(f"{pl.name} posts {'owed' if owed else ''} small blind {'ante' if ante else ''} of {self.small_blind_amt}")

    def post_big_blind(self, pl: 'Player', owed: bool=False, in_blinds: bool=True):
        pl.pip(self.big_blind_amt)
        if in_blinds:
            pl.paid_bb = True
        pl.owes_bb = False
        pl.newly_joined = False
        print(f"{pl.name} posts {'owed' if owed else ''} big blind of {self.big_blind_amt}")

    def move_buttons_post_blinds(self) -> tuple[int, int, int]:
        """ This uses the Forward Moving Button rules for Cash Game """

        def _first_hand() -> tuple[int, int, int]:
            for pl in self.seats.values():
                if pl:
                    pl.owes_bb = False
                    pl.owes_sb = False
                    pl.newly_joined = False

            present_seats = [s for s in self.seats if self.present(s)]
            dealer_idx, dealer_button = len(present_seats) - 1, present_seats[-1]
            dealer_player = self.seats[dealer_button]

            if self.is_headsup():
                big_blind_button = present_seats[(dealer_idx + 1) % 2]
                bb_player = self.seats[big_blind_button]

                # Dealer posts Small Blind
                self.post_small_blind(dealer_player)
                dealer_player.paid_sb = False  # reset at dealer

                # Post Big Blind
                self.post_big_blind(bb_player)

                small_blind_button = dealer_button
                return dealer_button, small_blind_button, big_blind_button

            n = len(present_seats)
            small_blind_button = present_seats[(dealer_idx + 1) % n]
            big_blind_button = present_seats[(dealer_idx + 2) % n]
            sb_player, bb_player = self.seats[small_blind_button], self.seats[big_blind_button]

            # Post Blinds
            self.post_small_blind(sb_player)
            self.post_big_blind(bb_player)

            return dealer_button, small_blind_button, big_blind_button

        def _missed_dealer(pl: Player):
            if not pl.paid_bb:
                pl.owes_bb = True
            if not pl.paid_sb and not pl.newly_joined:
                pl.owes_sb = True
            pl.paid_bb = False  # reset at dealer
            pl.paid_sb = False  # reset at dealer

        def _missed_big_blind(pl: Player, headsup: bool=False):
            pl.owes_bb = True
            if headsup and not pl.newly_joined:
                pl.owes_sb = True

        def _missed_small_blind(pl: Player):
            if not pl.newly_joined:
                pl.owes_sb = True

        def _headsup(_next_dealer: int) -> tuple[int, int]:
            for step_bb_hu in range(1, self.num_of_seats):
                next_big_blind = ((_next_dealer - 1 + step_bb_hu) % self.num_of_seats) + 1
                nxt_bb_pl = self.seats[next_big_blind]
                nxt_deal_pl = self.seats[_next_dealer]

                # Skip the ineligible
                if nxt_bb_pl is None:
                    continue
                elif nxt_bb_pl.on_break:
                    _missed_big_blind(nxt_bb_pl, headsup=True)
                    continue

                # Dealer posts Small Blind
                if nxt_deal_pl.paid_bb:
                    self.post_small_blind(nxt_deal_pl)
                else:
                    self.post_small_blind(nxt_deal_pl, ante=True)
                    self.post_big_blind(nxt_deal_pl, owed=True)
                nxt_deal_pl.paid_sb = False # reset at dealer
                nxt_deal_pl.paid_bb = False # reset at dealer

                # Post Big Blind
                if nxt_bb_pl.owes_sb and not nxt_bb_pl.newly_joined:
                    self.post_small_blind(nxt_bb_pl, ante=True, owed=True)
                self.post_big_blind(nxt_bb_pl)

                next_small_blind = _next_dealer
                return next_small_blind, next_big_blind
            raise RuntimeError("No present players found for the big blind")

        def _find_small_blind(_next_dealer: int) -> int:
            for step_sb in range(1, self.num_of_seats):
                next_small_blind = ((_next_dealer - 1 + step_sb) % self.num_of_seats) + 1
                nxt_sb_pl = self.seats[next_small_blind]

                # Skip the ineligible
                if nxt_sb_pl is None:
                    continue
                elif nxt_sb_pl.on_break:
                    _missed_small_blind(nxt_sb_pl)
                    continue
                elif not nxt_sb_pl.paid_bb and nxt_sb_pl.waiting_for_big_blind:
                    # add input prompt to ask player to post or wait
                    _missed_small_blind(nxt_sb_pl)
                    continue

                # Post Small Blind
                if nxt_sb_pl.owes_bb:
                    self.post_small_blind(nxt_sb_pl, ante=True)
                    self.post_big_blind(nxt_sb_pl, owed=True)
                else:
                    self.post_small_blind(nxt_sb_pl)

                return next_small_blind
            raise RuntimeError("No present players found for the small blind")

        def _find_big_blind(_next_small_blind: int) -> int:
            for step_bb in range(1, self.num_of_seats):
                next_big_blind = ((_next_small_blind - 1 + step_bb) % self.num_of_seats) + 1
                nxt_bb_pl = self.seats[next_big_blind]

                # Skip the ineligible
                if nxt_bb_pl is None:
                    continue
                elif nxt_bb_pl.on_break:
                    _missed_big_blind(nxt_bb_pl)
                    continue

                # Post Big Blind
                if nxt_bb_pl.owes_sb and not nxt_bb_pl.newly_joined:
                    self.post_small_blind(nxt_bb_pl, ante=True, owed=True)
                self.post_big_blind(nxt_bb_pl)

                return next_big_blind
            raise RuntimeError("No present players found for the big blind")

        def _move_buttons() -> tuple[int, int, int]:
            for step in range(1, self.num_of_seats):
                next_dealer = ((self.dealer_button - 1 + step) % self.num_of_seats) + 1
                nxt_deal_pl = self.seats[next_dealer]

                # Skip the ineligible
                if nxt_deal_pl is None:
                    continue
                elif nxt_deal_pl.on_break or nxt_deal_pl.newly_joined:
                    _missed_dealer(nxt_deal_pl)
                    continue
                elif not (nxt_deal_pl.paid_bb and nxt_deal_pl.paid_sb) and nxt_deal_pl.waiting_for_big_blind:
                    _missed_dealer(nxt_deal_pl)
                    continue

                if self.is_headsup():
                    next_small_blind, next_big_blind = _headsup(next_dealer)
                    return next_dealer, next_small_blind, next_big_blind

                # Dealer posts any owed blinds
                if not nxt_deal_pl.paid_bb:
                    self.post_big_blind(nxt_deal_pl, owed=True, in_blinds=False)
                if not nxt_deal_pl.paid_sb:
                    self.post_small_blind(nxt_deal_pl, ante=True, owed=True, in_blinds=False)

                # blinds reset at dealer
                nxt_deal_pl.paid_bb = False
                nxt_deal_pl.paid_sb = False

                next_small_blind = _find_small_blind(next_dealer)
                next_big_blind = _find_big_blind(next_small_blind)

                return next_dealer, next_small_blind, next_big_blind
            raise RuntimeError("No present players found for the big blind")

        if self.dealer_button is None: # If first hand of the table session
            self.dealer_button, self.small_blind_button, self.big_blind_button = _first_hand()
        else:
            self.dealer_button, self.small_blind_button, self.big_blind_button = _move_buttons()

        buttons = (self.dealer_button, self.small_blind_button, self.big_blind_button)
        non_button_active_players = [
            pl for s, pl in self.seats.items()
            if s not in buttons
            and self.present(s)
            and not pl.waiting_for_big_blind
        ]

        for pl in non_button_active_players:
            if pl.owes_sb:
                self.post_small_blind(pl, ante=True, owed=True, in_blinds=False)
            if pl.owes_bb:
                self.post_big_blind(pl, owed=True, in_blinds=False)

        return buttons

    def consolidate_ante(self):
        total_ante = self.pot_ante
        self.pot_ante = 0
        return total_ante

    def end_session(self):
        end_session_players = []
        for pl in self.seats.values():
            end_session_players.append(pl.leave_game(session_end=True))
        self.dealer_button = None
        return end_session_players

    def print_table(self):

        def is_there(_seat: int) -> str:
            pl = self.seats[_seat]
            pl_there = pl is not None and not pl.on_break and not pl.owes_bb and not pl.owes_sb
            if pl_there:
                return f"{pl.position[-2:]}"
            elif pl.on_break:
                return "br"
            elif pl.owes_bb or pl.owes_sb:
                return "ob"
            else:
                return "**"

        print(f"   /=[{is_there(4)}]==[{is_there(5)}]==[{is_there(6)}]=\\")
        print(f" [{is_there(3)}]                 [{is_there(7)}]  ")
        print(f"||                      ||")
        print(f" [{is_there(2)}]                 [{is_there(8)}]")
        print(f"   \=[{is_there(1)}]==[de]==[{is_there(9)}]=/")

    def __repr__(self):
        return "Table()"

    def __str__(self):
        seated_occupants = ", ".join(f"{seat}: {player.name if player else 'Empty'}" for seat, player in self.seats.items())
        return f"Table {self.table_number}: {seated_occupants}"

class Player:
    num_of_players = 0

    def __init__(self, name: str, stack: int, strategy: str, waiting_for_big_blind: bool=False):
        self.name: str = name
        self.stack: int = stack
        self.strategy: str = strategy
        self.waiting_for_big_blind: bool = waiting_for_big_blind
        self.table: Table | None = None
        self.seat: int | None = None
        self.on_break: bool = False

        self.newly_joined: bool = True
        self.owes_bb: bool = True
        self.owes_sb: bool = False
        self.paid_bb: bool = False
        self.paid_sb: bool = False

        Player.num_of_players += 1

        # In the Hand
        self.position: str | None = None
        self.current_bet: int = 0
        self.hole_cards: list[Card] = []
        self.folded: bool = False
        self.all_in: bool = False

    def leave_game(self, session_end: bool=False) -> tuple[str, int, str]:
        if self.position is not None and not self.folded:
            self.fold()
        if self.table is not None and self.seat is not None:
            self.table.leave_seat(self.seat, session_end)
        self.seat = None
        self.table = None
        self.on_break = False

        self.newly_joined: bool = True
        self.owes_bb = True
        self.owes_sb = False
        self.paid_bb: bool = False
        self.paid_sb: bool = False

        return self.name, self.stack, self.strategy

    def take_break(self):
        self.on_break = True
        if self.position is not None and not self.folded:
            self.fold()

    def resume_play(self, table: Table):
        if self.stack > table.big_blind_amt:
            self.on_break = False
            print(f"{self.name} has resumed play")
            return
        print(f"{self.name} has {self.stack} chips and not enough to play")

    def pip(self, amount: int, ante: bool=False) -> int:
        """Put-money-In-Pot. Takes from stack and handles all-in if necessary"""
        if amount < 0:
            raise ValueError("Amount cannot be negative.")
        elif self.stack - amount > 0:
            self.stack -= amount
            if not ante:
                self.current_bet += amount
            return amount
        else:
            allin = self.stack
            self.stack = 0
            if not ante:
                self.current_bet += allin
            self.all_in = True
            return allin

    def draw(self, deck: Deck, n: int = 1):
        self.hole_cards.extend(deck.draw(n))

    def show_hand(self, board: list[Card] = None):
        hand, rank = self.get_player_hand(board)
        hand_string = ""
        for c in hand:
            hand_string += f"{c}"
        return hand_string

    def get_player_hand(self, board: list[Card] = None) -> tuple[list[Card], tuple[HandRank, tuple[int, ...]]]:
        """Return best 5-card hand, and HandRanking, using the two hole cards and the board"""
        cards = list(self.hole_cards)
        if board:
            cards.extend(board)

        cards.sort(reverse=True) # sorts cards high->low. Logic relies on this

        def _find_flush(_cards: list[Card], return_all_cards: bool = False) -> list[Card] | None:
            for s in Suit:
                suited_cards = [c for c in _cards if c.suit == s]
                if len(suited_cards) >= 5:
                    flush_cards = suited_cards if return_all_cards else suited_cards[:5]
                    return flush_cards
            return None

        def _find_straight(_cards: list[Card]) -> list[Card] | None:
            ranks = {c.rank.value for c in _cards}
            if Rank.ACE.value in ranks:
                ranks.add(1)  # Handles wheel straight

            s_vals = sorted(ranks, reverse=True)
            for v in s_vals:
                if all((v - offset) in ranks for offset in range(5)):  # if straight exists
                    straight_vals_w_wheel_handling = [14 if x == 1 else x for x in range(v, v - 5, -1)]

                    cards_by_rank = {c.rank.value: c for c in _cards}
                    straight_cards = [cards_by_rank[r] for r in straight_vals_w_wheel_handling]
                    return straight_cards
            return None

        def _find_straight_flush(_cards: list[Card]) -> list[Card] | None:
            if flush_cards := _find_flush(_cards, return_all_cards=True):
                if straight_flush_cards := _find_straight(flush_cards):
                    return straight_flush_cards
            return None

        def _tally_rank_groupings(_cards: list[Card]) -> dict[int, list[Rank]]:
            rank_tally = {}
            for c in _cards:
                rank_tally[c.rank] = rank_tally.get(c.rank, 0) + 1
            tally_groups = {4: [], 3: [], 2: [], 1: []}
            for r, n in rank_tally.items():
                tally_groups[n].append(r)
            for n in tally_groups:
                tally_groups[n].sort(reverse=True)
            return tally_groups

        def _find_quads(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
            if not _tally_groups.get(4):  # if not quads
                return None
            quad_rank = _tally_groups[4][0]
            kicker = next(c for c in _cards if c.rank != quad_rank)
            quad_cards = [c for c in _cards if c.rank == quad_rank] + [kicker]
            return quad_cards

        def _find_full_house(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
            if not _tally_groups.get(3):  # if not trips
                return None

            if len(_tally_groups.get(3)) > 1:
                full_of_rank = _tally_groups[3][1]
            elif _tally_groups.get(2):
                full_of_rank = _tally_groups[2][0]
            else:
                return None

            trips_rank = _tally_groups[3][0]
            trips = [c for c in _cards if c.rank == trips_rank]
            full_of = [c for c in _cards if c.rank == full_of_rank][:2]
            full_house_cards = trips + full_of
            return full_house_cards

        def _find_trips(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
            if not _tally_groups.get(3):  # if not trips
                return None
            trips_rank = _tally_groups[3][0]
            kickers = [c for c in _cards if c.rank != trips_rank][:2]
            trips_cards = [c for c in _cards if c.rank == trips_rank] + kickers
            return trips_cards

        def _find_two_pair(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
            if len(_tally_groups.get(2)) < 2:  # if not pair
                return None
            first_pair_rank, second_pair_rank = _tally_groups[2][0], _tally_groups[2][1]
            first_pair, second_pair = ([c for c in _cards if c.rank == first_pair_rank],
                                       [c for c in _cards if c.rank == second_pair_rank])
            kicker = next(c for c in _cards if c.rank not in (first_pair_rank, second_pair_rank))
            two_pair_cards = first_pair + second_pair + [kicker]
            return two_pair_cards

        def _find_pair(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> list[Card] | None:
            if not _tally_groups.get(2):  # if not pair
                return None
            pair_rank = _tally_groups[2][0]
            kickers = [c for c in _cards if c.rank != pair_rank][:3]
            pair_cards = [c for c in _cards if c.rank == pair_rank] + kickers
            return pair_cards

        def _determine_hand(_cards: list[Card], _tally_groups: dict[int, list[Rank]])\
                -> tuple[list[Card], tuple[HandRank, tuple[int, ...]]]:
            """ Since the output of _find_* helpers is passed into _get_ranks, then _get_ranks output is always in the
                        correct group rank order for the hand rank. ie a full-house is [T,T,T,P,P]. Therefore, a tuple of the
                        rank values of _hand_cards will have correctly placed kickers for determining a winning hand. """

            def _get_ranks(_hand_cards: list[Card]) -> tuple[int, ...]:
                return tuple(c.rank.value for c in _hand_cards)

            if sf := _find_straight_flush(_cards):
                return sf, (HandRank.STRAIGHTFLUSH, _get_ranks(sf))
            elif q := _find_quads(_cards, _tally_groups):
                return q, (HandRank.QUADS, _get_ranks(q))
            elif fh := _find_full_house(_cards, _tally_groups):
                return fh, (HandRank.FULLHOUSE, _get_ranks(fh))
            elif f := _find_flush(_cards):
                return f, (HandRank.FLUSH, _get_ranks(f))
            elif s := _find_straight(_cards):
                return s, (HandRank.STRAIGHT, _get_ranks(s))
            elif t := _find_trips(_cards, _tally_groups):
                return t, (HandRank.TRIPS, _get_ranks(t))
            elif tp := _find_two_pair(_cards, _tally_groups):
                return tp, (HandRank.TWOPAIR, _get_ranks(tp))
            elif p := _find_pair(_cards, _tally_groups):
                return p, (HandRank.PAIR, _get_ranks(p))
            else:
                return _cards[:5], (HandRank.HIGHCARD, _get_ranks(_cards[:5]))

        return _determine_hand(cards, _tally_rank_groupings(cards))

    def can_act(self) -> bool:
        return not self.folded and not self.all_in and self.seat is not None

    def check(self):
        action_check = ('CHECK', 0)
        print(f"{self.position} CHECKS. ({self.name})")
        return action_check

    # Make sure amount is "to_call"
    def call(self, amount: int):
        action_call = ('CALL', self.pip(amount))
        print(f"{self.position} CALLS {action_call[1]} more for a total of {self.current_bet}. ({self.name})")
        if self.all_in: print(f"{self.position} is All-In.")
        return action_call

    # Always first bet of round, ie can never be used preflop and never if another player has already bet
    # ie self.highest_bet must always be 0
    def bet(self, amount: int, x: float = 1.0):
        action_bet = ('BET', self.pip(round(x * amount)))
        if self.all_in:
            action_all_in = ('ALL-IN', action_bet[1])
            print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")
            return action_all_in
        else:
            print(f"{self.position} BETS {self.current_bet}. ({self.name})")
            return action_bet

    # amount should be total amount of raise, not "to_call"
    def raise_holdem(self, amount: int, x: float = 3.0):
        action_raise = ('RAISE', self.pip(round(x * amount) - self.current_bet))
        if self.all_in:
            action_all_in = ('ALL-IN', action_raise[1])
            print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")
            return action_all_in
        else:
            print(f"{self.position} RAISES to {self.current_bet}. ({self.name})")
            return action_raise

    def go_all_in(self):
        action_allin = ('ALL-IN', self.pip(self.stack))
        print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")
        return action_allin

    def fold(self):
        self.folded = True
        action_fold = ('FOLD', 0)
        print(f"{self.position} FOLDS. ({self.name})")
        return action_fold

    def action_pre_flop(self, pot, highest_bet, to_call, raise_amount, raised_pre, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_holdem(pot, 2.5)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_holdem(highest_bet, 5)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

    def action_flop(self, pot, highest_bet, to_call, raise_amount, raised_pre, raised_flop, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.bet(pot, 0.333)
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_holdem(pot, 0.333)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_holdem(pot, 1)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

    def action_turn(self, pot, highest_bet, to_call, raise_amount, raised_pre, raised_flop, raised_turn, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_holdem(pot, 2.5)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_holdem(highest_bet, 5)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

    def action_river(self, pot, highest_bet, to_call, raise_amount, raised_pre, raised_flop, raised_turn, raised_river, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_holdem(pot, 2.5)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_holdem(highest_bet, 5)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

    def __repr__(self):
        return f"Player('{self.name}', {self.stack}, '{self.strategy}')"

    def __str__(self):
        return f"{self.name}, stack: {self.stack}, {self.strategy}"

def seat_players(players: list[tuple[str,int,str]], table: Table) -> None:
    for name, stack, strategy in players:
        if stack > 0:
            table.seat_player(Player(name, stack, strategy))
            continue
        print(f"{name} has {stack} chips and cannot play")

class Hand:
    holdemPositions = [
        'BU',
        'CO',
        'HJ',
        'LJ',
        'UTG+2',
        'UTG+1',
        'UTG'
    ]
    num_of_hands = 0

    def __init__(self, table: Table):
        # Hand setup
        self.table = table
        self.hand_number = Hand.num_of_hands + 1
        self.small_blind_amt = self.table.small_blind_amt
        self.big_blind_amt = self.table.big_blind_amt
        self.dealer_button: int
        self.small_blind_button: int
        self.big_blind_button: int
        self.dealer_button, self.small_blind_button, self.big_blind_button  = self.table.move_buttons_post_blinds()
        self.pots = [self.Pot()]
        self.pots[0].pot += self.table.consolidate_ante()

        self.players_in_hand = self.get_players_in_hand()
        self.n_players_in_hand = len(self.players_in_hand)
        self.headsup: bool = self.table.is_headsup()
        self.positions = {}
        self.assign_position()
        self.table.print_table()
        print(f"Dealer Button seat number: {self.dealer_button}")
        print(f"BU position seat number: {self.positions['BU'].seat}")
        self.game_state = 'PREFLOP'
        self.post_blinds()
        self.highest_bet = self.big_blind_amt
        self.raise_amt = self.big_blind_amt
        self.n_raises = {'PREFLOP': 1, 'FLOP': 0, 'TURN': 0, 'RIVER': 0}  # Keep track of 3bet pot, 4bet pot etc.
        self.deck = Deck()
        self.deck.shuffle()
        self.deal_hole_cards()
        self.mucked_pile = set()
        self.community_board = []
        self.burn_cards = []
        self.end_hand = False

        # Begin hand
        self.run_hand()

        self.end_hand_reset()
        print(f"\n\n   END of HAND {self.hand_number}   \n\n")

    class Pot:
        num_of_pots = 0
        def __init__(self):
            self.pot_number = Hand.Pot.num_of_pots
            self.pot = 0
            self.eligible_players = set()
            self.capped = False # No more chips can be added

            Hand.Pot.num_of_pots += 1

        @classmethod
        def remove_pot(cls):
            cls.num_of_pots -= 1

        def __repr__(self):
            return "Pot()"

        def __str__(self):
            if self.pot_number == 0:
                return f"Main Pot: ${self.pot}"
            else:
                return f"Side Pot {self.pot_number}: ${self.pot}"

    def tot_value_pot(self):
        current_bets_val = sum([v.current_bet for v in self.players_in_hand])
        past_pots_val = sum([p.pot for p in self.pots])
        return current_bets_val + past_pots_val

    # def _compute_button_player(self, get_bb: bool=False):
    #     _eligible_seats = [s for s, pl in self.table.seats.items() if
    #                       pl is not None and not pl.on_break and not pl.owes_bb and not pl.owes_sb]
    #     _present_seats = [s for s, pl in self.table.seats.items() if pl is not None and not pl.on_break]
    #
    #     _bu_seat = self.table.dealer_button
    #     _bu_index = _eligible_seats.index(_bu_seat)
    #     _sb_seat = _eligible_seats[(_bu_index + 1) % len(_eligible_seats)]
    #
    #     _seats = list(self.table.seats.keys())
    #     idx = {s: i for i, s in enumerate(_seats)}
    #     _bu_i, _sb_i = idx[_bu_seat], idx[_sb_seat]
    #
    #     if _bu_i < _sb_i:
    #         _between_bu_and_sb_inclusive = _seats[_bu_i + 1:_sb_i + 1]
    #     elif _bu_i > _sb_i:
    #         _between_bu_and_sb_inclusive = _seats[:_sb_i + 1] + _seats[_bu_i + 1:]
    #     else:
    #         raise RuntimeError("Not enough eligible players")
    #
    #     if not get_bb:
    #         return _between_bu_and_sb_inclusive, _sb_seat, _present_seats
    #
    #     _bb_seat = _eligible_seats[(_bu_index + 2) % len(_eligible_seats)]
    #     _bb_i = idx[_bb_seat]
    #     if _sb_i < _bb_i:
    #         _between_sb_and_bb_inclusive = _seats[_sb_i + 1:_bb_i + 1]
    #     elif _sb_i > _bb_i:
    #         _between_sb_and_bb_inclusive = _seats[:_bb_i + 1] + _seats[_sb_i + 1:]
    #     else:
    #         raise RuntimeError("Not enough eligible players")
    #
    #     return _between_bu_and_sb_inclusive, _between_sb_and_bb_inclusive
    #
    # def post_table_entry(self):
    #     players_to_post = [pl for pl in self.table.seats.values() if pl is not None and not pl.on_break and (pl.owes_bb or pl.owes_sb)]
    #
    #     if players_to_post:
    #         between_bu_and_sb_inclusive, sb_seat, present_seats = self._compute_button_player()
    #
    #         for pl in players_to_post:
    #             if pl.seat not in between_bu_and_sb_inclusive:
    #                 sb_present_seats_index = present_seats.index(sb_seat)
    #                 if pl.seat == present_seats[(sb_present_seats_index + 1) % len(present_seats)]: # if in big blind seat
    #                     pl.owes_bb = False
    #                     pl.owes_sb = False
    #                 else:
    #                     while True:
    #                         answer = input(f"Does {pl.name} with {pl.stack} chips in seat {pl.seat} want to post blinds? (yes/no): ").strip().lower()
    #                         if answer in ("yes", "y", "true", "1"):
    #                             post_blinds = True
    #                             break
    #                         elif answer in ("no", "n", "false", "0"):
    #                             post_blinds = False
    #                             break
    #                         else:
    #                             print("Invalid input, please type yes or no.")
    #                     if post_blinds:
    #                         if pl.owes_bb:
    #                             pl.pip(self.big_blind_amt)
    #                             pl.owes_bb = False
    #                             if pl.owes_sb:
    #                                 self.pots[0].pot += pl.pip(self.small_blind_amt, ante=True)
    #                                 pl.owes_sb = False
    #                         if pl.owes_sb:
    #                             pl.pip(self.small_blind_amt)
    #                             pl.owes_sb = False

    def _get_seats_between_bu_and_blinds(self, get_bb: bool=False) -> list[int] | tuple[list[int], list[int]]:
        seats = list(self.table.seats.keys())
        bu_i, sb_i = seats.index(self.dealer_button), seats.index(self.small_blind_button)

        if bu_i < sb_i:
            _between_bu_and_sb_inclusive = seats[bu_i + 1:sb_i + 1]
        elif bu_i > sb_i:
            _between_bu_and_sb_inclusive = seats[:sb_i + 1] + seats[bu_i + 1:]
        else:
            raise RuntimeError("Not enough eligible players")

        if not get_bb:
            return _between_bu_and_sb_inclusive

        bb_i = seats.index(self.big_blind_button)
        if sb_i < bb_i:
            _between_sb_and_bb_inclusive = seats[sb_i + 1:bb_i + 1]
        elif sb_i > bb_i:
            _between_sb_and_bb_inclusive = seats[:bb_i + 1] + seats[sb_i + 1:]
        else:
            raise RuntimeError("Not enough eligible players")

        return _between_bu_and_sb_inclusive, _between_sb_and_bb_inclusive

    def post_table_entry(self):
        players_to_post = [pl for pl in self.table.seats.values() if pl is not None and not pl.on_break and (pl.owes_bb or pl.owes_sb)]

        if players_to_post:
            between_bu_and_sb_inclusive = self._get_seats_between_bu_and_blinds()

            for pl in players_to_post:
                if pl.seat in between_bu_and_sb_inclusive:
                    continue

                while True:
                    answer = input(f"Does {pl.name} with {pl.stack} chips in seat {pl.seat} want to post blinds? (yes/no): ").strip().lower()
                    if answer in ("yes", "y", "true", "1"):
                        post_blinds = True
                        break
                    elif answer in ("no", "n", "false", "0"):
                        post_blinds = False
                        break
                    else:
                        print("Invalid input, please type yes or no.")

                if not post_blinds:
                    continue

                if pl.owes_bb:
                    pl.pip(self.big_blind_amt)
                    pl.owes_bb = False
                    if pl.owes_sb:
                        self.pots[0].pot += pl.pip(self.small_blind_amt, ante=True)
                        pl.owes_sb = False
                elif pl.owes_sb:
                    self.pots[0].pot += pl.pip(self.small_blind_amt, ante=True)
                    pl.owes_sb = False

    def missed_blinds(self):
        players_on_break = [pl for pl in self.table.seats.values() if pl is not None and pl.on_break and not pl.owes_bb]

        if players_on_break:
            between_bu_and_sb_inclusive, between_sb_and_bb_inclusive = self._get_seats_between_bu_and_blinds(get_bb=True)

            for pl in players_on_break:
                if pl.seat in between_sb_and_bb_inclusive:
                    pl.owes_bb = True
                    pl.owes_sb = True
                    print(f"{pl} missed blinds")
                elif pl.seat in between_bu_and_sb_inclusive:
                    pl.owes_sb = True
                    print(f"{pl} missed small blind")

    def get_players_in_hand(self) -> list[Player]:
        _players_in_hand = []
        for seat, occupant in self.table.seats.items():
            if self.table.eligible(seat):
                _players_in_hand.append(occupant)
        return _players_in_hand

    # def assign_position(self):
    #     # Implement Hold'em rules for position ordering
    #     # There is always a Button and Big Blind. Additional positions add the Small Blind then add positions from the Button anti-clockwise.
    #     # Lastly, UTG+1 (and UTG+2) only appears when there is already a UTG (and UTG+1)
    #     m = self.n_players_in_hand
    #     if self.headsup:
    #         hand_positions = ['BB', 'BU']
    #     else:
    #         hand_positions = Hand.holdemPositions[:(m - 2)]
    #         hand_positions.extend(['BB', 'SB'])
    #         hand_positions.reverse()
    #         if m == 8:
    #             hand_positions[hand_positions.index('UTG+1')] = 'UTG'
    #             hand_positions[hand_positions.index('UTG+2')] = 'UTG+1'
    #         elif m == 7:
    #             hand_positions[hand_positions.index('UTG+2')] = 'UTG'
    #
    #     bu_index = next(i for i, pl in enumerate(self.players_in_hand) if pl.seat == self.dealer_button)
    #     for i, p in enumerate(hand_positions):
    #         self.positions[p] = self.players_in_hand[(bu_index + 1 + i) % m]
    #         self.positions[p].position = p

    def assign_position(self):
        # Implement Hold'em rules for position ordering
        # There is always a Button and Big Blind. Additional positions add the Small Blind then add positions from the Button anti-clockwise.
        # Lastly, UTG+1 (and UTG+2) only appears when there is already a UTG (and UTG+1)
        m = self.n_players_in_hand
        if self.headsup:
            hand_positions = ['BB', 'BU']
        else:
            hand_positions = Hand.holdemPositions[:(m - 2)]
            hand_positions.extend(['BB', 'SB'])
            hand_positions.reverse()
            if m == 8:
                hand_positions[hand_positions.index('UTG+1')] = 'UTG'
                hand_positions[hand_positions.index('UTG+2')] = 'UTG+1'
            elif m == 7:
                hand_positions[hand_positions.index('UTG+2')] = 'UTG'

        bu_index = next(i for i, pl in enumerate(self.players_in_hand) if pl.seat == self.dealer_button)
        for i, p in enumerate(hand_positions):
            self.positions[p] = self.players_in_hand[(bu_index + 1 + i) % m]
            self.positions[p].position = p

    def post_blinds(self):
        bb = self.positions['BB']
        if self.headsup:
            sb = self.positions['BU']
        else:
            sb = self.positions['SB']
        sb.pip(self.small_blind_amt)
        bb.pip(self.big_blind_amt)

    def deal_hole_cards(self):
        two_hole_cards = 0
        while two_hole_cards != 2:
            for person in self.positions:
                self.positions[person].draw(self.deck)
            two_hole_cards += 1

    def betting_round(self, players_in_round):

        # player_to_act index number start. Starts left of BB (2), and is updated to the last raiser.
        # in headsup, starts on the BU (1) (who also posts the small blind).
        # starts at index 0 for later streets
        if self.headsup and self.game_state == 'PREFLOP':
            start = 1
        elif self.game_state == 'PREFLOP':
            start = 2
        else:
            start = 0

        m = len(players_in_round)
        p = 0       # incrementor to loop through players. Resets when a raise occurs
        live_players = m
        while (p < m) and live_players > 1:
            player_to_act = players_in_round[(p + start) % m]

            if not player_to_act.can_act():
                p += 1
                continue

            to_call = self.highest_bet - player_to_act.current_bet
            open_action = False if to_call < self.raise_amt else True

            if self.game_state == 'PREFLOP':
                player_action, bet = player_to_act.action_pre_flop(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises['PREFLOP'],
                    open_action
                )
            elif self.game_state == 'FLOP':
                player_action, bet = player_to_act.action_flop(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises['PREFLOP'],
                    self.n_raises['FLOP'],
                    open_action
                )
            elif self.game_state == 'TURN':
                player_action, bet = player_to_act.action_turn(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises['PREFLOP'],
                    self.n_raises['FLOP'],
                    self.n_raises['TURN'],
                    open_action
                )
            elif self.game_state == 'RIVER':
                player_action, bet = player_to_act.action_river(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises['PREFLOP'],
                    self.n_raises['FLOP'],
                    self.n_raises['TURN'],
                    open_action
                )

            if player_action == 'FOLD':
                for pot in self.pots:
                    pot.eligible_players.discard(player_to_act)
                self.mucked_pile.update(player_to_act.hole_cards)
                player_to_act.hole_cards.clear()
                #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                p, live_players = p + 1, live_players - 1
            elif player_action in ('CHECK', 'CALL'):
                #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                p += 1
            elif player_action in ('RAISE', 'BET'):
                self.raise_amt = player_to_act.current_bet - self.highest_bet
                self.highest_bet = player_to_act.current_bet
                if player_action == 'RAISE':
                    self.n_raises[self.game_state] += 1
                #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                start = start + p
                p = 0
                p += 1
            elif player_action == 'ALL-IN':
                if player_to_act.current_bet - self.highest_bet >= self.raise_amt:
                    self.raise_amt = player_to_act.current_bet - self.highest_bet
                    self.n_raises[self.game_state] += 1
                if player_to_act.current_bet > self.highest_bet:
                    start = start + p
                    p = 0
                self.highest_bet = max(self.highest_bet, player_to_act.current_bet)
                #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                p += 1

        # check if any bets
        if self.highest_bet > 0:
            self.create_pots(players_in_round)
            for player in players_in_round:
                player.current_bet = 0
            self.highest_bet = 0
            self.raise_amt = 0

        # if one player remaining, award pots and end hand
        if sum(not pl.folded for pl in self.players_in_hand) == 1:
            winning_player = next(pl for pl in self.players_in_hand if not pl.folded)
            self.award_pots_without_showdown(winning_player)
            self.end_hand = True

    def create_pots(self, players_in_round):

        def _calculate_bets(players, index, previous=0, amt=0, looping=False):
            bets_value = 0
            live_players = []
            highest_bet = second_highest_bet = 0
            player_eligible_for_pot = self.pots[index].eligible_players.add
            for p in players:
                bets_value += (min(p.current_bet, amt) - previous) if looping else (p.current_bet - previous)
                if not p.folded:
                    player_eligible_for_pot(p)
                    live_players.append(p)
                # retrieve second highest bet
                if p.current_bet > highest_bet:
                    highest_bet, second_highest_bet = p.current_bet, highest_bet
                elif p.current_bet > second_highest_bet:
                    second_highest_bet = p.current_bet
            if len(live_players) == 1:
                live_players[0].stack += live_players[0].current_bet - second_highest_bet
                bets_value -= live_players[0].current_bet - second_highest_bet
                print(f"Returned bet of {live_players[0].current_bet - second_highest_bet} for player: {live_players[0]}")
            self.pots[index].pot += bets_value
            print(self.pots[index])

        active_pot_index = len(self.pots) - 1
        all_in_players = set(p.all_in for p in players_in_round)
        if any(all_in_players):
            all_in_bets = set(p.current_bet for p in players_in_round if p.all_in)
            max_bet, max_all_in_bet = max(p.current_bet for p in players_in_round), max(all_in_bets)
            bets_occurred_after_all_in = max_bet > max_all_in_bet
            levels = sorted(all_in_bets.union({max_bet}))
            remaining = [p for p in players_in_round]
            prev = 0
            for i, amount in enumerate(levels):
                is_last = (i == len(levels) - 1)
                if is_last and bets_occurred_after_all_in:
                    print("bets occurred after final all-in")
                _calculate_bets(remaining, active_pot_index, prev, amount, True)
                if is_last and not bets_occurred_after_all_in:
                    print("players remain who aren't all-in after calling all-in")
                    self.pots[active_pot_index].capped = True
                remaining = [p for p in remaining if (p.current_bet - amount) > 0]
                prev = amount
                if not is_last:
                    self.pots[active_pot_index].capped = True
                if len(remaining) > 1:
                    self.pots.append(self.Pot())
                    active_pot_index += 1
                elif len(remaining) == 1:
                    remaining[0].stack += remaining[0].current_bet - prev
                    print(f"Returned bet of {remaining[0].current_bet - prev} for player: {remaining[0]}")
                    break
        else:
            _calculate_bets(players_in_round, active_pot_index)

        while len(self.pots) > 0 and self.pots[-1].pot == 0:
            self.pots.pop()
            Hand.Pot.num_of_pots -= 1

    def award_pots_without_showdown(self, winner):
        for pot in self.pots:
            if pot.pot == 0:
                print(f"{pot} has no chips")
                continue
            winner.stack += pot.pot
            print(f"{pot} awarded to {winner}")

    def showdown(self):
        for pot in self.pots:
            if pot.pot == 0:
                print(f"{pot} has no chips")
                continue
            eligible_players = {ep: ep.get_player_hand(self.community_board) for ep in pot.eligible_players}
            winning_hand = max([hand[1] for hand in eligible_players.values()])
            winning_players = [ep for ep, gph in eligible_players.items() if gph[1] == winning_hand]
            print(f"{pot} winning hand: {winning_hand}")

            if len(winning_players) > 1:
                print(f"{pot} is split between {len(winning_players)} players: ",end="")
                pot_share, remaining_chips = divmod(pot.pot, len(winning_players))
                for i, wp in enumerate(winning_players):
                    if i < (len(winning_players) - 1):
                        wp.stack += pot_share
                        print(f"{wp} ", end="")
                        print(f"{wp.show_hand(self.community_board)}, ", end="")
                    else:
                        wp.stack += pot_share + remaining_chips
                        print(f"{wp} ", end="")
                        print(f"{wp.show_hand(self.community_board)}")
                        # Need to create dealer button tracker, award remainder to left of dealer
                        if remaining_chips > 0:
                            print(f"Uneven Split: {wp.name} awarded {remaining_chips} remaining chips")
            else:
                winning_players[0].stack += pot.pot
                print(f"{pot} is awarded to {winning_players[0]}, with hand: {winning_players[0].show_hand(self.community_board)}")

    def preflop(self):
        self.betting_round(self.players_in_hand)

    def deal_flop(self):
        self.burn_cards.extend(self.deck.draw())
        self.community_board.extend(self.deck.draw(3))

    def show_board(self):
        print("------ Community Cards ------")
        if not self.community_board:
            print(" PREFLOP; No community cards dealt yet\n-----------------------------")
        else:
            for c in self.community_board:
                print(f"   {c}",end="")
            print("\n-----------------------------")

    def flop(self):
        self.game_state = 'FLOP'
        flop_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_flop()
        self.show_board()
        if len(flop_players) > 1:
            self.betting_round(flop_players)

    def deal_street(self):
        # For dealing Turn and River cards (commonly referred to as "streets")
        self.burn_cards.extend(self.deck.draw())
        self.community_board.extend(self.deck.draw())

    def turn(self):
        self.game_state = 'TURN'
        turn_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        if len(turn_players) > 1:
            self.betting_round(turn_players)

    def river(self):
        self.game_state = 'RIVER'
        river_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        if len(river_players) > 1:
            self.betting_round(river_players)
            if self.end_hand: return

        self.game_state = 'SHOWDOWN'
        self.showdown()

    def run_hand(self):
        self.preflop()
        if self.end_hand: return

        self.flop()
        if self.end_hand: return

        self.turn()
        if self.end_hand: return

        self.river()
        self.end_hand = True

    def end_hand_reset(self):
        Hand.Pot.num_of_pots = 0
        Hand.num_of_hands += 1
        for p in self.players_in_hand:
            p.position = None
            p.current_bet = 0
            p.hole_cards.clear()
            p.folded = False
            p.all_in = False
            if p.stack <= 0 and p.seat is not None:
                p.on_break = True
                print(f"Player {p} has lost their stack")

    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return f"Hand {self.hand_number}"





player_list = [
    ('Young White TAG',500, 'calling station')
    ,('ME',500, 'calling station')
    ,('Young Asian LAG',800, 'calling station')
    ,('Young Asian TAG',100, 'aggro')
    ,('Old Asian Laggy',500, 'calling station')
    ,('Fat Old White Guy',1000, 'passive')
    ,('White Pro',500, 'passive')
    ,('Indian LAG',1000, 'calling station')
    ,('Villain LAG',137, 'aggro')
]


t1 = Table()
seat_players(player_list, t1)


h1 = Hand(t1)


h2 = Hand(t1)
h3 = Hand(t1)
t1.seats[3].take_break()
t1.seats[6].take_break()
h4 = Hand(t1)
t1.seats[1].take_break()
h5 = Hand(t1)
h6 = Hand(t1)
h7 = Hand(t1)
t1.seats[9].take_break()
h8 = Hand(t1)
t1.seats[9].resume_play(t1)
h9 = Hand(t1)
h10 = Hand(t1)
h11 = Hand(t1)
h12 = Hand(t1)
t1.seats[1].resume_play(t1)
h13 = Hand(t1)
t1.seats[3].resume_play(t1)
t1.seats[6].resume_play(t1)
h14 = Hand(t1)
t1.seats[7].take_break()
h15 = Hand(t1)
h16 = Hand(t1)
h17 = Hand(t1)
h18 = Hand(t1)
t1.seats[7].resume_play(t1)
h19 = Hand(t1)
h20 = Hand(t1)



print(Table.__dict__)
print(t1.__dict__)
print(t1)
print(Player.__dict__)
print(Hand.__dict__)
#print(h1.__dict__)
print(f'Hand 1: {h1.__dict__}')
# print(f'Hand 2: {h2.__dict__}')
# print(f'Hand 3: {h3.__dict__}')
# print(f'Hand 4: {h4.__dict__}')
# print(f'Hand 5: {h5.__dict__}')
# print(f'Hand 6: {h6.__dict__}')
# print(f'Hand 7: {h7.__dict__}')
# print(f'Hand 8: {h8.__dict__}')
# print(f'Hand 9: {h9.__dict__}')

# print(h1.players)
# print(h1.players_in_hand)
# print(h1.positions)
#
# print(h3.players_in_hand)
# print(h3.players_in_hand[1])
# print(h3.players_in_hand[1].player)
# print(h3.players_in_hand[1].starting_stack)
# print(h3.players_in_hand[1].player.stack)
#
#
#
#
# print(h4.players_in_hand[0])
# print(h4.players_in_hand[0].player)
# print(h4.players_in_hand[0].starting_stack)
# print(h4.players_in_hand[0].player.stack)


print(h1.players_in_hand)
print(h1.positions)
print(h1.players_in_hand[1])

print(h1.players_in_hand[1].stack)
# print(h1.players_in_hand[4])
# print(h1.players_in_hand[4].current_bet)
print(h1.pots)

print(h1.players_in_hand[7].hole_cards)

print(h1.positions['CO'].hole_cards)

for p in h1.pots:
    print(f"{p}    Eligible players: {p.eligible_players}")

print(h1.n_raises)
print(h1.community_board)
h1.show_board()


print(Card.__dict__)

print(h1.deck)

print(t1)

# print(h3.positionsInt)
# print(h3.positionsInt[1])
# print(h3.positionsInt[1].player)
# print(h3.positionsInt[1].starting_stack)
# print(h3.positionsInt[1].player.stack)



# print(h6.positions['BB'].__dict__)
# print(h6.positions['BB'].holeCards)
# print(h6.positions)

# print(p0.__dict__)
# print(p1.__dict__)

# h1.positions['SB'].bet(3)
# print(p0.__dict__)
# print(h1.__dict__)

# deck = Deck()
# deck.shuffle()
# deck.show()
# print('\n')
# p1.draw(deck).draw(deck)
# p1.show_holeCards()
#
# print(p1.pip(35))
#
# print(p1.show_stack())