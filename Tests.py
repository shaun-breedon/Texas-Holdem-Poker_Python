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
        return isinstance(other, Card) and self.rank == other.rank

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

deck = Deck()
print(deck)

card = deck.cards[4]
print(card)
print(card.rank + 1)

empty_list = []
print(len(empty_list) < 2)