from enum import IntEnum, StrEnum, unique, auto # Suit, Rank, HandRank, GameState
from typing import ClassVar # Suit, Rank
from functools import total_ordering # Card
import random # shuffle
from collections import deque # Table waitlist, Betting round
from bisect import bisect_right # next_left_player_index

@unique
class Suit(StrEnum):
    SPADES = 's'
    HEARTS = 'h'
    DIAMONDS = 'd'
    CLUBS = 'c'

    __SYMBOLS: ClassVar[dict[str, str]] = {
        's': '♠',
        'h': '♥',
        'd': '♦',
        'c': '♣'
    }

    @property
    def symbol(self) -> str:
        return type(self).__SYMBOLS[self.value]

    @property
    def colour(self) -> str:
        return "black" if self in {Suit.SPADES, Suit.CLUBS} else "red"


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

    @property
    def face(self) -> str:
        return self.name[0] if self.value >= 10 else str(self.value)

    def __str__(self):
        return self.face


class HandRank(IntEnum):
    ROYAL_FLUSH = 10
    STRAIGHT_FLUSH = 9
    QUADS = 8
    FULL_HOUSE = 7
    FLUSH = 6
    STRAIGHT = 5
    TRIPS = 4
    TWO_PAIR = 3
    PAIR = 2
    HIGH_CARD = 1

    def __str__(self):
        return self.name.replace("_", " ")


class GameState(StrEnum):
    SETUP = auto()
    PRE_FLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()
    END_HAND = auto()

class Action(StrEnum):
    CHECK = auto()
    BET = auto()
    CALL = auto()
    RAISE = auto()
    FOLD = auto()
    ALL_IN = auto()

@total_ordering
class Card:
    def __init__(self, rank: Rank, suit: Suit):
        self.rank: Rank = rank
        self.suit: Suit = suit

    def __repr__(self):
        return f"Card(Rank.{self.rank.name}, Suit.{self.suit.name})"

    def __str__(self):
        return f"{self.rank}{self.suit.symbol}"

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
        self.cards: list[Card] = [Card(r, s) for s in Suit for r in Rank]

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, n=1) -> list[Card]:
        if n <= 0: raise ValueError("Must draw at least one card.")
        if n > len(self.cards): raise ValueError("Not enough cards left to draw.")
        drawn = [self.cards.pop() for _ in range(n)]
        return drawn

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return "Deck()"

    def __str__(self):
        return ' '.join(str(c) for c in self.cards)


class Table:
    wait_list: 'deque[Player]' = deque()
    tables: 'list[Table]' = []

    @classmethod
    def num_of_tables(cls) -> int:
        return len(cls.tables)

    def __init__(self, num_of_seats: int = 9, small_blind_amt: int = 2, big_blind_amt: int = 3):
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
        self.headsup: bool = False

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
                player.newly_seated() # enforcement guardrails
                break
        if not found_seat:
            Table.wait_list.append(player)

    def leave_seat(self, seat_number: int, session_end: bool = False):
        self.seats[seat_number] = None
        if Table.wait_list and not session_end:
            next_player = Table.wait_list.popleft()
            self.seat_player(next_player)

    # Add change seat method

    def present(self, seat: int) -> bool:
        pl = self.seats[seat]
        return pl is not None and not pl.on_break

    def eligible(self, seat: int) -> bool:
        pl = self.seats[seat]
        return pl is not None and not pl.on_break and not pl.owes_bb and not pl.owes_sb

    def enough_players(self) -> bool:
        n_present = sum(self.present(s) for s in self.seats)
        if n_present < 2:
            raise RuntimeError("Need ≥2 present players to proceed with hand")
        else:
            return True

    def is_headsup(self) -> bool:
        n_present = sum(self.present(s) for s in self.seats)
        if n_present < 2:
            raise RuntimeError("Need ≥2 present players to move the button")
        elif n_present == 2:
            return True
        else:
            return False

    def post_small_blind(self, pl: 'Player', ante: bool = False, owed: bool = False, in_blinds: bool = True):
        if ante:
            sb = pl.pip(self.small_blind_amt, ante=True)
            self.pot_ante += sb
        else:
            sb = pl.pip(self.small_blind_amt)
        if in_blinds:
            pl.paid_sb = True
        pl.owes_sb = False
        print(f"{pl.name} posts{' owed ' if owed else ' '}small blind {'ante' if ante else ''} of {sb}")
        if pl.all_in: print(f"{pl.name} is all in")

    def post_big_blind(self, pl: 'Player', owed: bool = False, in_blinds: bool = True):
        bb = pl.pip(self.big_blind_amt)
        if in_blinds:
            pl.paid_bb = True
        pl.owes_bb = False
        pl.newly_joined = False
        print(f"{pl.name} posts{' owed ' if owed else ' '}big blind of {bb}")
        if pl.all_in: print(f"{pl.name} is all in")

    @staticmethod
    def ask_player_to_post(pl: 'Player', pos: str) -> bool:
        if pos.strip().upper() == 'BU':
            question = f"BU: {pl.name} to post owed:{'' if pl.paid_sb else '-Small Blind-'}{'' if pl.paid_bb else '-Big Blind-'}? (y/n):"
        elif pos.strip().upper() == 'SB':
            question = f"SB: {pl.name} to post owed:-Big Blind-? (y/n):"
        else:
            raise ValueError("Invalid String")

        while True:
            answer = input(question).strip().lower()
            if answer in ("yes", "y", "true", "1"):
                will_post = True
                break
            elif answer in ("no", "n", "false", "0"):
                will_post = False
                break
            else:
                print("Invalid input, please type yes or no.")

        return will_post

    def move_buttons_post_blinds(self) -> tuple[int, int, int]:
        """ This uses the Forward Moving Button rules for Cash Game """

        def _dealer_blinds_reset(dealer_pl: 'Player'):
            dealer_pl.paid_sb = False
            dealer_pl.paid_bb = False

        def _first_hand() -> tuple[int, int, int]:
            for pl in self.seats.values():
                if pl:
                    pl.owes_sb = pl.paid_sb = pl.paid_bb = False # Enforcement guardrails
                    if not pl.on_break:
                        pl.owes_bb = pl.newly_joined = False

            present_seats = [s for s in self.seats if self.present(s)]
            dealer_idx, dealer_button = len(present_seats) - 1, present_seats[-1]

            if self.is_headsup():
                big_blind_button = present_seats[(dealer_idx + 1) % 2]
                bb_player = self.seats[big_blind_button]
                dealer_player = self.seats[dealer_button]

                # Dealer posts Small Blind
                self.post_small_blind(dealer_player)
                _dealer_blinds_reset(dealer_player)

                # Post Big Blind
                self.post_big_blind(bb_player)

                self.headsup = True
                small_blind_button = dealer_button
                return dealer_button, small_blind_button, big_blind_button

            n = len(present_seats)
            small_blind_button = present_seats[(dealer_idx + 1) % n]
            big_blind_button = present_seats[(dealer_idx + 2) % n]
            sb_player, bb_player = self.seats[small_blind_button], self.seats[big_blind_button]

            # Post Blinds
            self.post_small_blind(sb_player)
            self.post_big_blind(bb_player)

            sb_player.paid_bb = True # First-hand setting to not falsely trigger an owed BB on 2nd hand

            return dealer_button, small_blind_button, big_blind_button

        def _missed_dealer(pl: Player):
            pl.owes_bb = not pl.paid_bb
            pl.owes_sb = not pl.paid_sb and not pl.newly_joined
            _dealer_blinds_reset(pl)

        def _missed_big_blind(pl: Player, headsup: bool = False):
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
                    self.post_big_blind(nxt_deal_pl, owed=True)
                    self.post_small_blind(nxt_deal_pl, ante=True)
                _dealer_blinds_reset(nxt_deal_pl)

                # Post Big Blind
                self.post_big_blind(nxt_bb_pl)
                if nxt_bb_pl.owes_sb and not nxt_bb_pl.newly_joined:
                    self.post_small_blind(nxt_bb_pl, ante=True, owed=True)

                self.headsup = True
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
                    will_post = self.ask_player_to_post(nxt_sb_pl, pos='SB')
                    if not will_post:
                        _missed_small_blind(nxt_sb_pl)
                        continue

                # Post Small Blind
                if not nxt_sb_pl.paid_bb:
                    self.post_big_blind(nxt_sb_pl, owed=True)
                    self.post_small_blind(nxt_sb_pl, ante=True)
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
                self.post_big_blind(nxt_bb_pl)
                if nxt_bb_pl.owes_sb and not nxt_bb_pl.newly_joined:
                    self.post_small_blind(nxt_bb_pl, ante=True, owed=True)

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
                    will_post = self.ask_player_to_post(nxt_deal_pl, pos='BU')
                    if not will_post:
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

                _dealer_blinds_reset(nxt_deal_pl)

                next_small_blind = _find_small_blind(next_dealer)
                next_big_blind = _find_big_blind(next_small_blind)

                return next_dealer, next_small_blind, next_big_blind
            raise RuntimeError("No present players found for the big blind")

        self.enough_players() # Check if >= 2 present players

        if self.dealer_button is None:  # If first hand of the table session
            self.dealer_button, self.small_blind_button, self.big_blind_button = _first_hand()
        else:
            self.dealer_button, self.small_blind_button, self.big_blind_button = _move_buttons()

        buttons = (self.dealer_button, self.small_blind_button, self.big_blind_button)
        non_button_active_players = [
            pl for s, pl in self.seats.items()
            if s not in buttons
               and self.present(s)
               and not ((pl.owes_bb or pl.owes_sb) and pl.waiting_for_big_blind)
        ]

        for pl in non_button_active_players:
            if pl.owes_bb:
                self.post_big_blind(pl, owed=True, in_blinds=False)
            if pl.owes_sb:
                self.post_small_blind(pl, ante=True, owed=True, in_blinds=False)

        return buttons

    def consolidate_ante(self) -> int:
        total_ante = self.pot_ante
        self.pot_ante = 0
        return total_ante

    def end_session(self) -> list[tuple[str, int, str]]:
        end_session_players: list[tuple[str, int, str]] = []
        for pl in self.seats.values():
            if pl:
                end_session_players.append(pl.leave_game(session_end=True))
        self.dealer_button = None
        self.big_blind_button = None
        self.small_blind_button = None
        self.pot_ante = 0
        self.headsup = False
        return end_session_players

    def print_table(self):

        def is_there(_seat: int) -> str:
            pl = self.seats[_seat]
            if pl is None:
                return "**"
            elif pl.on_break:
                return "br"
            elif pl.owes_bb or pl.owes_sb:
                return "ob"
            return f"{pl.position[-2:]}"

        print(f"   /=[{is_there(4)}]==[{is_there(5)}]==[{is_there(6)}]=\\")
        print(f" [{is_there(3)}]                 [{is_there(7)}]  ")
        print(f"||                      ||")
        print(f" [{is_there(2)}]                 [{is_there(8)}]")
        print(f"   \\=[{is_there(1)}]==[de]==[{is_there(9)}]=/")

    def __repr__(self):
        return "Table()"

    def __str__(self):
        seated_occupants = ", ".join(
            f"{seat}: {player.name if player else 'Empty'}" for seat, player in self.seats.items())
        return f"Table {self.table_number}: {seated_occupants}"


class Player:
    num_of_players: int = 0
    players: 'list[Player]' = []

    def __init__(self, name: str, stack: int, strategy: str, waiting_for_big_blind: bool = False):
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
        Player.players.append(self)

        # In the Hand
        self.position: str | None = None
        self.current_bet: int = 0
        self.hole_cards: list[Card] = []
        self.folded: bool = False
        self.all_in: bool = False

    def newly_seated(self):
        self.newly_joined = self.owes_bb = True  # Enforcement guardrails
        self.owes_sb = self.paid_sb = self.paid_bb = False  # Enforcement guardrails

    def leave_game(self, session_end: bool = False) -> tuple[str, int, str]:
        if self.position is not None and not self.folded:
            self.fold()
        if self.table is not None and self.seat is not None:
            self.table.leave_seat(self.seat, session_end)
        self.seat = None
        self.table = None
        self.on_break = False

        self.newly_joined = True
        self.owes_bb = True
        self.owes_sb = False
        self.paid_bb = False
        self.paid_sb = False

        return self.name, self.stack, self.strategy

    def take_break(self):
        self.on_break = True
        if self.position is not None and not self.folded:
            self.fold()

    def resume_play(self):
        if self.stack > 0:
            self.on_break = False
            print(f"{self.name} has resumed play")
        else:
            print(f"{self.name} has {self.stack} chips and not enough to play")

    def pip(self, amount: int, ante: bool = False) -> int:
        """Put-money-In-Pot. Takes from stack and handles all-in if necessary"""
        if amount < 0:
            raise ValueError("Amount cannot be negative.")

        pay = min(amount, self.stack)
        self.stack -= pay
        if not ante:
            self.current_bet += pay
        if self.stack == 0:
            self.all_in = True
        return pay

    def draw(self, deck: Deck, n: int = 1):
        self.hole_cards.extend(deck.draw(n))

    def get_player_hand(self, board: list[Card] | None = None) -> tuple[list[Card], tuple[HandRank, tuple[int, ...]]]:
        """Return best 5-card hand, and HandRanking, using the two hole cards and the board"""
        cards = list(self.hole_cards)
        if board:
            cards.extend(board)

        cards.sort(reverse=True)  # sorts cards high->low. Logic relies on this

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

        def _determine_hand(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) \
                -> tuple[list[Card], tuple[HandRank, tuple[int, ...]]]:
            """ Since the output of _find_* helpers is passed into _get_ranks, then _get_ranks output is always in the
                        correct group rank order for the hand rank. ie a full-house is [T,T,T,P,P]. Therefore, a tuple of the
                        rank values of _hand_cards will have correctly placed kickers for determining a winning hand. """

            def _get_ranks(_hand_cards: list[Card]) -> tuple[int, ...]:
                return tuple(c.rank.value for c in _hand_cards)

            if sf := _find_straight_flush(_cards):
                if sf[0].rank == Rank.ACE:
                    return sf, (HandRank.ROYAL_FLUSH, _get_ranks(sf))
                else:
                    return sf, (HandRank.STRAIGHT_FLUSH, _get_ranks(sf))
            elif q := _find_quads(_cards, _tally_groups):
                return q, (HandRank.QUADS, _get_ranks(q))
            elif fh := _find_full_house(_cards, _tally_groups):
                return fh, (HandRank.FULL_HOUSE, _get_ranks(fh))
            elif f := _find_flush(_cards):
                return f, (HandRank.FLUSH, _get_ranks(f))
            elif s := _find_straight(_cards):
                return s, (HandRank.STRAIGHT, _get_ranks(s))
            elif t := _find_trips(_cards, _tally_groups):
                return t, (HandRank.TRIPS, _get_ranks(t))
            elif tp := _find_two_pair(_cards, _tally_groups):
                return tp, (HandRank.TWO_PAIR, _get_ranks(tp))
            elif p := _find_pair(_cards, _tally_groups):
                return p, (HandRank.PAIR, _get_ranks(p))
            else:
                return _cards[:5], (HandRank.HIGH_CARD, _get_ranks(_cards[:5]))

        return _determine_hand(cards, _tally_rank_groupings(cards))

    def show_hand(self, board: list[Card] = None) -> str:
        hand, rank = self.get_player_hand(board)
        hand_string = ""
        for c in hand:
            hand_string += f"{c} "
        return hand_string

    def can_act(self) -> bool:
        return not self.folded and not self.all_in and not self.on_break and self.seat is not None

    def check(self) -> tuple[Action, int]:
        action_check = (Action.CHECK, 0)
        print(f"{self.position} CHECKS. ({self.name})")
        return action_check

    # Make sure amount is "to_call"
    def call(self, amount: int) -> tuple[Action, int]:
        action_call = (Action.CALL, self.pip(amount))
        print(f"{self.position} CALLS {action_call[1]} more for a total of {self.current_bet}. ({self.name})")
        if self.all_in:
            action_all_in = (Action.ALL_IN, action_call[1])
            print(f"{self.position} is All-In.")
            return action_all_in
        return action_call

    # Always first bet of round, ie can never be used preflop and never if another player has already bet
    # ie self.highest_bet must always be 0
    def bet(self, amount: int, x: float = 1.0) -> tuple[Action, int]:
        target = max(round(x * amount), 0)
        if target <= 0:
            return self.check()
        action_bet = (Action.BET, self.pip(target))
        if self.all_in:
            action_all_in = (Action.ALL_IN, action_bet[1])
            print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")
            return action_all_in
        print(f"{self.position} BETS {self.current_bet}. ({self.name})")
        return action_bet

    # amount should be total amount of raise, not "to_call"
    def raise_to(self, amount: int, x: float = 1.0) -> tuple[Action, int]:
        add = max(round(x * amount) - self.current_bet, 0)
        if add <= 0:
            raise ValueError("Raise amount must be greater than current bet")
        action_raise = (Action.RAISE, self.pip(add))
        if self.all_in:
            action_all_in = (Action.ALL_IN, action_raise[1])
            print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")
            return action_all_in
        print(f"{self.position} RAISES to {self.current_bet}. ({self.name})")
        return action_raise

    def go_all_in(self) -> tuple[Action, int]:
        action_allin = (Action.ALL_IN, self.pip(self.stack))
        print(f"{self.position} ALL-IN for {self.current_bet}. ({self.name})")
        return action_allin

    def fold(self) -> tuple[Action, int]:
        self.folded = True
        action_fold = (Action.FOLD, 0)
        print(f"{self.position} FOLDS. ({self.name})")
        return action_fold

    def action_pre_flop(self, pot: int, highest_bet: int, to_call: int, raise_amount: int, raised_pre: int, open_action: bool=True) -> tuple[Action, int]:

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        elif self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_to(pot, 2.5)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_to(highest_bet, 5)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

        else: return self.check() if to_call == 0 else self.fold() # default

    def action_flop(self, pot: int, highest_bet: int, to_call: int, raise_amount: int, raised_pre: int, raised_flop: int, open_action: bool=True) -> tuple[Action, int]:

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        elif self.strategy == 'calling station':
            if to_call == 0:
                return self.bet(pot, 0.333)
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_to(pot, 0.333)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_to(pot, 1)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

        else: return self.check() if to_call == 0 else self.fold()  # default

    def action_turn(self, pot: int, highest_bet: int, to_call: int, raise_amount: int, raised_pre: int, raised_flop: int, raised_turn: int,
                    open_action: bool=True) -> tuple[Action, int]:

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        elif self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_to(pot, 2.5)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_to(highest_bet, 5)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

        else: return self.check() if to_call == 0 else self.fold()  # default

    def action_river(self, pot: int, highest_bet: int, to_call: int, raise_amount: int, raised_pre: int, raised_flop: int, raised_turn: int, raised_river: int,
                     open_action: bool=True) -> tuple[Action, int]:

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        elif self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
            else:
                return self.call(to_call)

        elif self.strategy == 'aggro':
            if not open_action:
                return self.call(to_call)
            elif to_call == 0:
                return self.raise_to(pot, 2.5)
            elif (highest_bet + raise_amount - self.current_bet) > self.stack:
                return self.go_all_in()
            else:
                return self.raise_to(highest_bet, 5)

        elif self.strategy == 'scared':
            if to_call == 0:
                return self.check()
            elif highest_bet == 3:
                return self.call(to_call)
            else:
                return self.fold()

        else: return self.check() if to_call == 0 else self.fold()  # default

    def reset_for_new_street(self):
        self.current_bet = 0

    def reset_for_new_hand(self):
        self.position = None
        self.current_bet = 0
        self.hole_cards.clear()
        self.folded = False
        self.all_in = False
        if self.stack <= 0 and self.seat is not None:
            self.on_break = True
            print(f"Player {self} has lost their stack")

    def __repr__(self):
        return f"Player('{self.name}', {self.stack}, '{self.strategy}')"

    def __str__(self):
        return f"{self.name}, stack: {self.stack}, {self.strategy}"


def seat_players(players: list[tuple[str, int, str]], table: Table):
    for name, stack, strategy in players:
        if stack > table.big_blind_amt:
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
    num_of_hands: int = 0

    def __init__(self, table: Table):
        # Hand setup
        self.table: Table = table
        self.game_state: GameState = GameState.SETUP
        self.hand_number: int = Hand.num_of_hands + 1

        self.small_blind_amt: int = self.table.small_blind_amt
        self.big_blind_amt: int = self.table.big_blind_amt
        self.dealer_button: int
        self.small_blind_button: int
        self.big_blind_button: int
        self.dealer_button, self.small_blind_button, self.big_blind_button = self.table.move_buttons_post_blinds()
        self._num_of_pots: int = 0
        self.pots: list[Hand.Pot] = [self.Pot(self)]
        self.pots[0].pot += self.table.consolidate_ante()
        self.headsup: bool = self.table.headsup

        self.players_in_hand: list[Player] = self.get_players_in_hand()
        self.n_players_in_hand: int = len(self.players_in_hand)
        self.positions: dict[str, Player] = self.assign_position()
        self.table.print_table() # Can remove later

        self.highest_bet: int = self.big_blind_amt
        self.raise_amt: int = self.big_blind_amt
        self.n_raises: dict[GameState, int] = { # Keep track of 3bet pot, 4bet pot etc.
            GameState.PRE_FLOP: 1,
            GameState.FLOP: 0,
            GameState.TURN: 0,
            GameState.RIVER: 0
        }
        self.deck: Deck = Deck()
        self.deck.shuffle()
        self.deal_hole_cards()
        self.mucked_pile: set[Card] = set()
        self.community_board: list[Card] = []
        self.burn_cards: list[Card] = []
        self.end_hand: bool = False

        # Begin hand
        self.run_hand()
        self.end_hand_reset()

    def _next_pot_number(self) -> int:
        n = self._num_of_pots
        self._num_of_pots += 1
        return n

    class Pot:
        def __init__(self, hand: 'Hand'):
            self.hand: Hand = hand
            self.pot_number: int = hand._next_pot_number()
            self.pot: int = 0
            self.eligible_players: set[Player] = set()
            self.capped: bool = False  # No more chips can be added

        def __repr__(self):
            return "Pot()"

        def __str__(self):
            return f"{'Main Pot' if self.pot_number == 0 else f'Side Pot {self.pot_number}'}: ${self.pot}"

    def tot_value_pot(self) -> int:
        current_bets_val = sum(pl.current_bet for pl in self.players_in_hand)
        past_pots_val = sum(p.pot for p in self.pots)
        return current_bets_val + past_pots_val

    def get_players_in_hand(self) -> list[Player]:
        _players_in_hand = []
        for seat, occupant in self.table.seats.items():
            if self.table.eligible(seat):
                _players_in_hand.append(occupant)
        return _players_in_hand

    @staticmethod
    def _get_index_map(_players_list: list[Player]) -> dict[int, int]:
        return {pl.seat: index for index, pl in enumerate(_players_list)}

    def _next_left_player_index(self, seat: int, _players_list: list[Player], index_map: dict[int, int] | None = None) -> int:
        pl_seats = sorted(pl.seat for pl in _players_list)
        j = bisect_right(pl_seats, seat)
        next_seat = pl_seats[0] if j == len(pl_seats) else pl_seats[j]
        idx_map = index_map or self._get_index_map(_players_list)
        return idx_map[next_seat]

    def assign_position(self) -> dict[str, Player]:
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

        positions = {}
        idx_map = self._get_index_map(self.players_in_hand)
        bu_index = idx_map[self.dealer_button]
        for i, p in enumerate(hand_positions):
            positions[p] = self.players_in_hand[(bu_index + 1 + i) % m]
            positions[p].position = p
        return positions

    def deal_hole_cards(self):
        for _ in range(2):
            for pl in self.positions.values():
                pl.draw(self.deck)

    def reset_for_next_street(self, _players_in_round: list[Player]):
        for pl in _players_in_round:
            pl.reset_for_new_street()
        self.highest_bet = 0
        self.raise_amt = 0

    def betting_round(self, players_in_round: list[Player]):

        # in headsup, starts on the dealer button (who also posts the small blind).
        # else, if pre-flop, starts left of Big Blind
        # starts left of dealer button on later streets
        idx_map = self._get_index_map(players_in_round)
        if self.headsup and self.game_state == GameState.PRE_FLOP:
            start = idx_map[self.dealer_button]
        elif self.game_state == GameState.PRE_FLOP:
            start = self._next_left_player_index(self.big_blind_button, players_in_round, idx_map)
        else:
            start = self._next_left_player_index(self.dealer_button, players_in_round, idx_map)

        order = deque(players_in_round) # create a player queue from collections import
        order.rotate(-start)
        active = set(players_in_round) # not folded, not all-in
        live = set(players_in_round) # not folded
        pending = set(players_in_round) # yet to act

        while len(live) > 1 and pending:
            player_to_act = order[0]

            to_call = self.highest_bet - player_to_act.current_bet
            open_action = to_call >= self.raise_amt

            if self.game_state == GameState.PRE_FLOP:
                player_action, bet = player_to_act.action_pre_flop(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises[GameState.PRE_FLOP],
                    open_action
                )
            elif self.game_state == GameState.FLOP:
                player_action, bet = player_to_act.action_flop(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises[GameState.PRE_FLOP],
                    self.n_raises[GameState.FLOP],
                    open_action
                )
            elif self.game_state == GameState.TURN:
                player_action, bet = player_to_act.action_turn(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises[GameState.PRE_FLOP],
                    self.n_raises[GameState.FLOP],
                    self.n_raises[GameState.TURN],
                    open_action
                )
            elif self.game_state == GameState.RIVER:
                player_action, bet = player_to_act.action_river(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.n_raises[GameState.PRE_FLOP],
                    self.n_raises[GameState.FLOP],
                    self.n_raises[GameState.TURN],
                    self.n_raises[GameState.RIVER],
                    open_action
                )
            else:
                raise AssertionError(f"{self.game_state} isn't a poker street")

            if player_action == Action.FOLD:
                for pot in self.pots:
                    pot.eligible_players.discard(player_to_act)
                self.mucked_pile.update(player_to_act.hole_cards)
                player_to_act.hole_cards.clear()
                active.remove(player_to_act)
                live.remove(player_to_act)
                pending.remove(player_to_act)
                order.popleft()
                continue

            if player_action in (Action.CHECK, Action.CALL):
                pending.remove(player_to_act)
                order.rotate(-1)
                continue

            if player_action in (Action.RAISE, Action.BET):
                if player_action == Action.RAISE:
                    full_raise = (player_to_act.current_bet - self.highest_bet) >= self.raise_amt
                    if not full_raise:
                        msg = f"{player_to_act.name} bet of {player_to_act.current_bet} below minimum raise of {self.raise_amt} on top of the highest bet of {self.highest_bet}"
                        raise ValueError(msg)
                    self.n_raises[self.game_state] += 1
                self.raise_amt = player_to_act.current_bet - self.highest_bet
                self.highest_bet = player_to_act.current_bet
                pending = active - {player_to_act}
                order.rotate(-1)
                continue

            if player_action == Action.ALL_IN:
                bet_increased = player_to_act.current_bet > self.highest_bet
                full_raise = (player_to_act.current_bet - self.highest_bet) >= self.raise_amt
                if bet_increased:
                    if full_raise:
                        self.raise_amt = player_to_act.current_bet - self.highest_bet
                        self.n_raises[self.game_state] += 1
                    self.highest_bet = player_to_act.current_bet
                    pending = active - {player_to_act}
                else:
                    pending.remove(player_to_act)
                active.remove(player_to_act)
                order.popleft()
                continue

        # check if any bets
        if self.highest_bet > 0:
            self.create_pots(players_in_round)
        self.reset_for_next_street(players_in_round)

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
                print(
                    f"Returned bet of {live_players[0].current_bet - second_highest_bet} for player: {live_players[0]}")
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
                    self.pots.append(self.Pot(self))
                    active_pot_index += 1
                elif len(remaining) == 1:
                    remaining[0].stack += remaining[0].current_bet - prev
                    print(f"Returned bet of {remaining[0].current_bet - prev} for player: {remaining[0]}")
                    break
        else:
            _calculate_bets(players_in_round, active_pot_index)

        while self.pots and self.pots[-1].pot == 0:
            self.pots.pop()
            self._num_of_pots -= 1

    def award_pots_without_showdown(self, winner):
        for pot in self.pots:
            if pot.pot == 0:
                print(f"{pot} has no chips")
                continue
            winner.stack += pot.pot
            print(f"{pot} awarded to {winner}")

    def showdown(self):
        self.game_state = GameState.SHOWDOWN

        for pot in self.pots:
            if pot.pot == 0:
                print(f"{pot} has no chips")
                continue

            eligible_players = {ep: ep.get_player_hand(self.community_board)
                                for ep in pot.eligible_players if not ep.folded}
            winning_key = max([gph[1] for gph in eligible_players.values()])
            winners_info = {ep: gph for ep, gph in eligible_players.items() if gph[1] == winning_key}
            print(f"{pot} winning key: {winning_key}")

            if len(winners_info) == 1:
                wp, (cards, (hr, k)) = next(iter((ep, (gph[0], gph[1])) for ep, gph in winners_info.items()))
                wp.stack += pot.pot
                print(f"{pot} is awarded to {wp}, with: {hr}: {' '.join(map(str, cards))}")
                continue

            def seats_left_of_dealer(pl: Player) -> int:
                left = (pl.seat - self.dealer_button) % self.table.num_of_seats
                return self.table.num_of_seats if left == 0 else left

            winners = sorted(winners_info.keys(), key=seats_left_of_dealer)
            pot_share, remaining_chips = divmod(pot.pot, len(winners))
            print(f"{pot} is split between {len(winners)} players: ")

            for i, pl in enumerate(winners):
                extra = 1 if i < remaining_chips else 0  # odd chips go left of dealer first
                pl.stack += pot_share + extra
                cards, (hr, k) = winners_info[pl]
                print(f"   {pl} wins {pot_share + extra} with: {hr}: {' '.join(map(str, cards))}")
                if extra == 1:
                    print(f"      (Uneven Split: {pl.name} awarded 1 remaining chip)")

    def preflop(self):
        self.game_state = GameState.PRE_FLOP
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
                print(f"   {c}", end="")
            print("\n-----------------------------")

    def flop(self):
        self.game_state = GameState.FLOP
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
        self.game_state = GameState.TURN
        turn_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        if len(turn_players) > 1:
            self.betting_round(turn_players)

    def river(self):
        self.game_state = GameState.RIVER
        river_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        if len(river_players) > 1:
            self.betting_round(river_players)

    def run_hand(self):
        self.preflop()
        if self.end_hand: return

        self.flop()
        if self.end_hand: return

        self.turn()
        if self.end_hand: return

        self.river()
        if self.end_hand: return

        self.showdown()

    def end_hand_reset(self):
        self.game_state = GameState.END_HAND
        for p in self.players_in_hand:
            p.reset_for_new_hand()
        self.table.headsup = False
        self.end_hand = True
        Hand.num_of_hands += 1
        print(f"\n\n   END of HAND {self.hand_number}   \n\n")

    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return f"Hand {self.hand_number}"


player_list = [
    ('Young White TAG', 500, 'calling station')
    , ('ME', 500, 'calling station')
    , ('Young Asian LAG', 800, 'calling station')
    , ('Young Asian TAG', 100, 'aggro')
    , ('Old Asian Laggy', 500, 'calling station')
    , ('Fat Old White Guy', 1000, 'passive')
    , ('White Pro', 500, 'passive')
    , ('Indian LAG', 1000, 'calling station')
    , ('Villain LAG', 137, 'aggro')
]

t1 = Table()
seat_players(player_list, t1)

h1 = Hand(t1)

h2 = Hand(t1)
h3 = Hand(t1)
h4 = Hand(t1)
h5 = Hand(t1)

# t1.seats[1].take_break()
# h6 = Hand(t1)
# h7 = Hand(t1)
# t1.seats[9].take_break()
# h8 = Hand(t1)
# t1.seats[9].resume_play()
# h9 = Hand(t1)
# t1.seats[3].take_break()
# t1.seats[6].take_break()
# h10 = Hand(t1)
# h11 = Hand(t1)
# h12 = Hand(t1)
# t1.seats[1].resume_play()
# h13 = Hand(t1)
# t1.seats[3].resume_play()
# t1.seats[6].resume_play()
# h14 = Hand(t1)
# t1.seats[7].take_break()
# h15 = Hand(t1)
# h16 = Hand(t1)
# h17 = Hand(t1)
# h18 = Hand(t1)
# t1.seats[7].resume_play()
# h19 = Hand(t1)
# h20 = Hand(t1)