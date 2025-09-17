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
    TWOPAIR = 3
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

    def retrieve_card(self, rank: Rank, suit: Suit) -> Card:
        retrieved_card = next((c for c in self.cards if c.rank is rank and c.suit is suit), None)
        if retrieved_card:
            self.cards.remove(retrieved_card)
            return retrieved_card
        else:
            raise ValueError(f"{rank} of {suit} not in deck")

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
    def num_of_tables(cls):
        return len(cls.tables)

    def __init__(self, num_of_seats=9):
        if num_of_seats < 2:
            raise ValueError("A table must have at least 2 seats.")
        self.seats = {s: None for s in range(num_of_seats)}
        Table.tables.append(self)
        self.table_number = Table.num_of_tables()

    def seat_player(self, player):
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

    def leave_seat(self, seat_number):
        self.seats[seat_number] = None
        if Table.wait_list:
            next_player = Table.wait_list.pop(0)
            self.seat_player(next_player)

    def __repr__(self):
        return "Table()"

    def __str__(self):
        seated_occupants = ", ".join(
            f"{seat}: {player.name if player else 'Empty'}" for seat, player in self.seats.items())
        return f"Table {self.table_number}: {seated_occupants}"


class Player:
    num_of_players = 0

    def __init__(self, name: str, stack: int, strategy: str):
        self.name = name
        self.stack = stack
        self.strategy = strategy
        self.seat = None
        self.on_break = False

        Player.num_of_players += 1

        # In the Hand
        self.table = None
        self.position = None
        self.current_bet = 0
        self.hole_cards = []
        self.folded = False
        self.all_in = False
        self.player_hand = None
        self.player_hand_ranking = None

    def leave_game(self):
        if self.table is not None and self.seat is not None:
            self.table.leave_seat(self.seat)
        self.seat = None
        self.table = None
        return [self.name, self.stack, self.strategy]

    def take_break(self):
        self.on_break = True

    def resume_play(self):
        self.on_break = False

    def pip(self, amount: int) -> int:
        """Put-money-In-Pot. Takes from stack and handles all-in if necessary"""
        if amount < 0:
            raise ValueError("Amount cannot be negative.")
        elif self.stack - amount > 0:
            self.stack -= amount
            self.current_bet += amount
            return amount
        else:
            allin = self.stack
            self.stack = 0
            self.current_bet += allin
            self.all_in = True
            return allin

    def draw(self, deck: Deck, n: int = 1):
        self.hole_cards.extend(deck.draw(n))

    def show_hole_cards(self):
        if self.hole_cards:
            print(f"{self.name}: {self.hole_cards[0]} {self.hole_cards[1]}")
        else:
            print(f"{self.name} has no hole cards")

    # make board default to empty
    def get_player_hand(self, board: list[Card] = None):
        """Return best 5-card hand, and HandRanking, using the two hole cards and the board"""
        cards = list(self.hole_cards)
        if board:
            cards.extend(board)

        cards.sort(reverse=True)

        # def _find_straight_flush(_cards: list[Card]) -> list[Card] | None:
        #     for s in Suit:
        #         suited_ranks = {c.rank.value for c in _cards if c.suit == s}
        #         if len(suited_ranks) < 5:
        #             continue
        #
        #         if Rank.ACE.value in suited_ranks:
        #             suited_ranks.add(1) # Handles wheel straight flush
        #
        #         sf_vals = sorted(suited_ranks, reverse=True)
        #         for v in sf_vals:
        #             if all((v - offset) in suited_ranks for offset in range(5)): # if straight flush exists
        #                 straight_flush_vals_w_wheel_handling = [14 if x == 1 else x for x in range(v, v - 5, -1)]
        #
        #                 cards_by_rank = {c.rank.value: c for c in _cards if c.suit == s}
        #                 straight_flush_cards = [cards_by_rank[r] for r in straight_flush_vals_w_wheel_handling]
        #                 return straight_flush_cards
        #     return None

        # if sf := _find_straight_flush(cards):
        #     player_hand_ranking = HandRank.STRAIGHTFLUSH
        #     player_hand = sf

        # def _find_straight_flush(_cards: list[Card]) -> list[Card] | None:
        #     by_suit = {
        #         s: {c.rank.value for c in _cards if c.suit == s}
        #         for s in Suit
        #     }
        #     for k, v in by_suit.items():
        #         if Rank.ACE.value in v:
        #             v.add(1)
        #         by_suit[k] = sorted(v, reverse=True)
        #     for s in Suit:
        #         if len(by_suit[s]) < 5:
        #             continue
        #         for v in by_suit[s]:
        #             if all([(v - offset) in by_suit[s] for offset in range(5)]):
        #                 handle_wheel_straight_flush = [14 if rank_val == 1 else rank_val for rank_val in
        #                                                range(v, v - 5, -1)]
        #                 straight_flush_cards = [
        #                     next(c for c in _cards if c.rank.value == rank_val and c.suit == s)
        #                     for rank_val in handle_wheel_straight_flush
        #                 ]
        #                 return straight_flush_cards
        #     return None

        # Straight Flush
        # is_straight_flush = False
        # straight_flush_cards = []
        # straight_flush = {
        #     s: {c.rank.value for c in cards if c.suit == s}
        #     for s in Suit
        # }
        # for k, v in straight_flush.items():
        #     if Rank.ACE.value in v:
        #         v.add(1)
        #     straight_flush[k] = sorted(v, reverse=True)
        # for s in Suit:
        #     if len(straight_flush[s]) < 5:
        #         continue
        #     for v in straight_flush[s]:
        #         is_straight_flush = all([(v - offset) in straight_flush[s] for offset in range(5)])
        #         if is_straight_flush:
        #             handle_wheel_straight_flush = [14 if rank_val == 1 else rank_val for rank_val in range(v, v - 5, -1)]
        #             straight_flush_cards = [
        #                 next(c for c in cards if c.rank.value == rank_val and c.suit == s)
        #                 for rank_val in handle_wheel_straight_flush
        #             ]
        #             break
        #     if is_straight_flush:
        #         break

        # Flushes
        # is_flush = False
        # flush_cards = []
        # flush = {
        #     s: sum(1 for c in cards if c.suit == s)
        #     for s in Suit
        # }
        # flush_suit = next((s for s, count in flush.items() if count >= 5), None)
        # if flush_suit:
        #     is_flush = True
        #     flush_cards = [c for c in cards if c.suit == flush_suit]
        #     flush_cards = flush_cards[:5]

        # Straights
        # straight_cards = []
        # present_ranks = {c.rank.value for c in cards}
        # if Rank.ACE.value in present_ranks:
        #     present_ranks.add(1)
        # present_ranks = sorted(present_ranks, reverse=True)
        # is_straight = False
        # for v in present_ranks:
        #     is_straight = all([(v - offset) in present_ranks for offset in range(5)])
        #     if is_straight:
        #         handle_wheel_straight = [14 if rank_val == 1 else rank_val for rank_val in range(v, v - 5, -1)]
        #         straight_cards = [
        #             next(c for c in cards if c.rank.value == rank_val)
        #             for rank_val in handle_wheel_straight
        #         ]
        #         break

        # def _find_full_house_or_trips(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> tuple[HandRank, list[Card]] | None:
        #     if not _tally_groups[3]: # if not trips
        #         return None
        #     trips_rank = _tally_groups[3][0]
        #     trips = [c for c in _cards if c.rank == trips_rank]
        #     full_of_rank = None
        #     if _tally_groups[3][1]:
        #         full_of_rank = _tally_groups[3][1]
        #     elif _tally_groups[2]:
        #         full_of_rank = _tally_groups[2][0]
        #
        #     if full_of_rank:
        #         full_of = [c for c in _cards if c.rank == full_of_rank][:2]
        #         full_house_cards = trips + full_of
        #         return HandRank.FULLHOUSE, full_house_cards
        #     else:
        #         kickers = [c for c in _cards if c.rank != trips_rank][:2]
        #         trips_cards = trips + kickers
        #         return HandRank.TRIPS, trips_cards

        # Pairs, Two Pairs, Trips, Quads
        # rank_counts = {}
        # for c in cards:
        #     rank_counts[c.rank] = rank_counts.get(c.rank, 0) + 1
        # combinations = list(rank_counts.values())
        # print(rank_counts)
        # print(combinations)

        # Quads
        # quad_cards = []
        # quad_rank = next((r for r, cnt in rank_counts.items() if cnt == 4), None)
        # if quad_rank:
        #     kicker = max(c for c in cards if c.rank != quad_rank)
        #     quad_cards = [c for c in cards if c.rank == quad_rank] + [kicker]

        # Full House, Trips
        # full_house_cards = []
        # trips_cards = []
        # trips_rank = next((r for r, cnt in rank_counts.items() if cnt == 3), None)
        # if trips_rank:
        #     trips = [c for c in cards if c.rank == trips_rank]
        #     full_of_rank = next(
        #         (r for r, cnt in rank_counts.items() if (cnt == 3 and r != trips_rank)),
        #         next((r for r, cnt in rank_counts.items() if cnt == 2), None)
        #     )
        #     if full_of_rank:
        #         full_of = [c for c in cards if c.rank == full_of_rank][:2]
        #         full_house_cards = trips + full_of
        #     else:
        #         kickers = [c for c in cards if c.rank != trips_rank][:2]
        #         trips_cards = trips + kickers

        # Two Pair, Pair
        # two_pair_cards = []
        # pair_cards = []
        # first_pair_rank = next((r for r, cnt in rank_counts.items() if cnt == 2), None)
        # if first_pair_rank:
        #     first_pair = [c for c in cards if c.rank == first_pair_rank]
        #     second_pair_rank = next(
        #         (r for r, cnt in rank_counts.items() if (cnt == 2 and r != first_pair_rank)),
        #         None
        #     )
        #     if second_pair_rank:
        #         second_pair = [c for c in cards if c.rank == second_pair_rank]
        #         kicker = max(c for c in cards if c.rank not in (first_pair_rank, second_pair_rank))
        #         two_pair_cards = first_pair + second_pair + [kicker]
        #     else:
        #         kickers = [c for c in cards if c.rank != first_pair_rank][:3]
        #         pair_cards = first_pair + kickers

        # if is_straight_flush:
        #     player_hand_ranking = HandRank.STRAIGHTFLUSH
        #     player_hand = straight_flush_cards
        # elif 4 in combinations:
        #     player_hand_ranking = HandRank.QUADS
        #     player_hand = quad_cards
        # elif (combinations.count(3) == 2) or (3 in combinations and 2 in combinations):
        #     player_hand_ranking = HandRank.FULLHOUSE
        #     player_hand = full_house_cards
        # elif is_flush:
        #     player_hand_ranking = HandRank.FLUSH
        #     player_hand = flush_cards
        # elif is_straight:
        #     player_hand_ranking = HandRank.STRAIGHT
        #     player_hand = straight_cards
        # elif 3 in combinations:
        #     player_hand_ranking = HandRank.TRIPS
        #     player_hand = trips_cards
        # elif combinations.count(2) >= 2:
        #     player_hand_ranking = HandRank.TWOPAIR
        #     player_hand = two_pair_cards
        # elif 2 in combinations:
        #     player_hand_ranking = HandRank.PAIR
        #     player_hand = pair_cards
        # else:
        #     player_hand_ranking = HandRank.HIGHCARD
        #     player_hand = cards[:5]

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
            if not _tally_groups.get(4): # if not quads
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
            if not _tally_groups.get(3): # if not trips
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

        def _determine_hand(_cards: list[Card], _tally_groups: dict[int, list[Rank]]) -> tuple[list[Card],HandRank]:
            if sf := _find_straight_flush(_cards):
                return sf, HandRank.STRAIGHTFLUSH
            elif q := _find_quads(_cards, _tally_groups):
                return q, HandRank.QUADS
            elif fh := _find_full_house(_cards, _tally_groups):
                return fh, HandRank.FULLHOUSE
            elif f := _find_flush(_cards):
                return f, HandRank.FLUSH
            elif s := _find_straight(_cards):
                return s, HandRank.STRAIGHT
            elif t := _find_trips(_cards, _tally_groups):
                return t, HandRank.TRIPS
            elif tp := _find_two_pair(_cards, _tally_groups):
                return tp, HandRank.TWOPAIR
            elif p := _find_pair(_cards, _tally_groups):
                return p, HandRank.PAIR
            else:
                return _cards[:5], HandRank.HIGHCARD

        tally_groups = _tally_rank_groupings(cards)
        outcome = _determine_hand(cards,tally_groups)
        for c in outcome[0]:
            print(c,end="")
        print("     ")
        print(outcome[1])

        return outcome

    def can_act(self) -> bool:
        return not self.folded and not self.all_in and self.seat is not None

    def __repr__(self):
        return f"Player('{self.name}', {self.stack}, '{self.strategy}')"

    def __str__(self):
        return f"{self.name}, stack: {self.stack}, {self.strategy}"


def seat_players(players: list[tuple[str, int, str]], table: Table) -> None:
    for name, stack, strategy in players:
        table.seat_player(Player(name, stack, strategy))


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

    def __init__(self, table=Table, small_blind_amt=2, big_blind_amt=3):
        # Start of Hand
        self.table = table
        self.hand_number = Hand.num_of_hands + 1
        self.small_blind_amt = small_blind_amt
        self.big_blind_amt = big_blind_amt
        self.players_in_hand = []
        for occupant in self.table.seats.values():
            if occupant:
                if occupant.stack > 0 and not occupant.on_break:
                    self.players_in_hand.append(occupant)
        self.n_players_in_hand = len(self.players_in_hand)
        if self.n_players_in_hand == 2:
            self.headsup = True
        elif self.n_players_in_hand > 2:
            self.headsup = False
        self.positions = {}
        self.assign_position()
        self.pots = [self.Pot()]
        self.post_blinds()
        self.deck = Deck()
        self.deck.shuffle()
        # test_cards = [
        #     self.deck.retrieve_card(Rank.TWO, Suit.CLUBS),
        #     self.deck.retrieve_card(Rank.THREE, Suit.CLUBS),
        #     self.deck.retrieve_card(Rank.FOUR, Suit.CLUBS),
        #     self.deck.retrieve_card(Rank.FIVE, Suit.CLUBS),
        #     # self.deck.retrieve_card(Rank.THREE, Suit.HEARTS),
        #     # self.deck.retrieve_card(Rank.FOUR, Suit.DIAMONDS),
        #     # self.deck.retrieve_card(Rank.FIVE, Suit.SPADES)
        # ]
        self.deal_hole_cards()

        # Preflop
        self.game_state = 'PREFLOP'
        self.highest_bet = self.big_blind_amt
        self.raise_amt = self.big_blind_amt
        self.n_raises = {'PREFLOP': 1, 'FLOP': 0, 'TURN': 0, 'RIVER': 0} # Keep track of 3bet pot, 4bet pot etc.
        self.mucked_pile = set()
        #self.preflop()

        # Flop
        self.community_board = []
        self.burn_cards = []
        #self.flop()

        # Turn
        #self.turn()

        # River
        #self.river()

        self.deal_flop()
        self.deal_street()
        self.deal_street()

        # Manual Community Cards Testing
        # self.community_board.extend(test_cards)
        # self.deal_street()
        # self.deal_street()
        # self.deal_street()

        Hand.num_of_hands += 1

    class Pot:
        num_of_pots = 0
        def __init__(self):
            self.pot_number = Hand.Pot.num_of_pots
            self.pot = 0
            self.eligible_players = set()
            self.uncapped = True

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

        n = 0
        for p in hand_positions:
            self.positions[p] = self.players_in_hand[(Hand.num_of_hands + n) % m]
            self.positions[p].position = p
            n += 1

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
        while p < m:
            player_to_act = players_in_round[(p + start) % m]

            if not player_to_act.can_act():
                p += 1
            else:

                if self.highest_bet - player_to_act.current_bet < self.raise_amt:
                    open_action = False
                else:
                    open_action = True

                to_call = self.highest_bet - player_to_act.current_bet

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

                if player_action == 'CHECK':
                    #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                    p += 1
                elif player_action == 'CALL':
                    #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                    p += 1
                elif player_action == 'RAISE':
                    self.raise_amt = player_to_act.current_bet - self.highest_bet
                    self.highest_bet = max(self.highest_bet, player_to_act.current_bet)
                    self.n_raises[self.game_state] += 1
                    #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
                    start = start + p
                    p = 0
                    p += 1
                elif player_action == 'FOLD':
                    for pot in self.pots:
                        pot.eligible_players.discard(player_to_act)
                    self.mucked_pile.update(player_to_act.hole_cards)
                    player_to_act.hole_cards.clear()
                    #print(f'p:{p} start:{start}  m:{m}  i:{self.players_in_hand.index(player_to_act)}  {player_action} bet:{bet}   highestBet:{self.highest_bet}   playerCurrentBet:{player_to_act.current_bet}    Pot:{self.pots[0]}  allin?:{player_to_act.all_in}   Pos:{player_to_act.position}   {player_to_act}')
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
        any_bets = any(p.current_bet > 0 for p in players_in_round)
        if any_bets:
            self.create_pots(players_in_round)
            for player in players_in_round:
                player.current_bet = 0
            self.highest_bet = 0
            self.raise_amt = 0

    def create_pots(self, players_in_round):
        active_pot_index = len(self.pots) - 1
        if not self.pots[active_pot_index].uncapped:
            self.pots.append(self.Pot())
            active_pot_index += 1
        all_in_players = set(p.all_in for p in players_in_round)

        def calculate_bets(players, index, previous=0, amt=0, looping=False):
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

        if any(all_in_players):
            all_in_bets = set(p.current_bet for p in players_in_round if p.all_in)
            max_bet, max_all_in_bet = max(p.current_bet for p in players_in_round), max(all_in_bets)
            bets_occured_after_all_in = max_bet > max_all_in_bet
            levels = sorted(all_in_bets.union({max_bet}))
            remaining = [p for p in players_in_round]
            prev = 0
            for i, amount in enumerate(levels):
                is_last = (i == len(levels) - 1)
                if is_last and bets_occured_after_all_in:
                    print("bets occured after final all-in")
                calculate_bets(remaining, active_pot_index, prev, amount, True)
                if is_last and not bets_occured_after_all_in:
                    print("players remain who aren't all-in after calling all-in")
                    self.pots[active_pot_index].uncapped = False
                remaining = [p for p in remaining if (p.current_bet - amount) > 0]
                prev = amount
                if not is_last:
                    self.pots[active_pot_index].uncapped = False
                if len(remaining) > 1:
                    self.pots.append(self.Pot())
                    active_pot_index += 1
                elif len(remaining) == 1:
                    remaining[0].stack += remaining[0].current_bet - prev
                    print(f"Returned bet of {remaining[0].current_bet - prev} for player: {remaining[0]}")
                    break
        else:
            calculate_bets(players_in_round, active_pot_index)

    def preflop(self):
        self.betting_round(self.players_in_hand)
        self.game_state = 'FLOP'

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
        flop_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_flop()
        self.show_board()
        if len(flop_players) > 1:
            self.betting_round(flop_players)
        self.game_state = 'TURN'

    def deal_street(self):
        # For dealing Turn and River cards (commonly referred to as "streets")
        self.burn_cards.extend(self.deck.draw())
        self.community_board.extend(self.deck.draw())

    def turn(self):
        turn_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        if len(turn_players) > 1:
            self.betting_round(turn_players)
        self.game_state = 'RIVER'

    def river(self):
        river_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        if len(river_players) > 1:
            self.betting_round(river_players)

    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return f"Hand {self.hand_number}"


player_list = [
    ('Young White TAG', 500, 'passive')
    , ('ME', 469, 'passive')
    , ('Young Asian LAG', 3, 'passive')
    , ('Young Asian TAG', 200, 'aggro')
    , ('Old Asian Laggy', 500, 'calling station')
    , ('Fat Old White Guy', 1000, 'passive')
    , ('White Pro', 500, 'passive')
    , ('Indian LAG', 500, 'passive')
    , ('Villain LAG', 1000, 'aggro')
]

t1 = Table()
seat_players(player_list, t1)

h1 = Hand(t1)

print("\n\n   NEW LINE   \n\n")

print(Table.__dict__)
print(Player.__dict__)
print(Hand.__dict__)
print(f'Hand 1: {h1.__dict__}')

for k,v in h1.positions.items():
    print(f"{v.hole_cards[0]}{v.hole_cards[1]}",end="")
    print("  ",end="")
    for c in v.get_player_hand(h1.community_board):
        print(c,end="")
    print("\n")

h1.show_board()