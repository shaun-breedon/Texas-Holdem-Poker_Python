from enum import Enum, IntEnum
import random

# 1. Define Suit and Rank Enums

class Suit(Enum):
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'
    SPADES = '♠'

    def __str__(self):
        return f"{self.value}"

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
        face_names = {
            Rank.TEN: 'T',
            Rank.JACK: 'J',
            Rank.QUEEN: 'Q',
            Rank.KING: 'K',
            Rank.ACE: 'A'
        }
        return face_names.get(self, str(self.value))

# 2. Define the Card class (no dataclasses)

class Card:
    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return f"Card(Rank.{self.rank.name}, Suit.{self.suit.name})"

    #Comparison methods
    def __eq__(self, other):
        return isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit

    def __lt__(self, other):
        return isinstance(other, Card) and self.rank < other.rank

    def __le__(self, other):
        return isinstance(other, Card) and self.rank <= other.rank

    def __gt__(self, other):
        return isinstance(other, Card) and self.rank > other.rank

    def __ge__(self, other):
        return isinstance(other, Card) and self.rank >= other.rank

    def __hash__(self):
        return hash((self.rank, self.suit))

# 3. Define the Deck class

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in Suit for rank in Rank]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, num_cards):
        if num_cards > len(self.cards):
            raise ValueError("Not enough cards left to deal.")
        dealt = self.cards[:num_cards]
        self.cards = self.cards[num_cards:]
        return dealt

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return "Deck()"
    #
    # def __str__(self):
    #     return ', '.join(str(card) for card in self.cards)

# 4. Example usage

deck = Deck()
print(f"Initial deck size: {len(deck)}")
deck.shuffle()

hand = deck.deal(5)
print("Dealt hand:", ', '.join(str(card) for card in hand))

card1, card2 = hand[0], hand[1]
print(f"Is {card1} > {card2}? {card1 > card2}")

# print(deck.cards[0])
# print(deck.cards[0].rank.name)
# print(deck.cards[0].rank.value)
# print(deck.cards[0].rank)
# print(deck.cards[0].suit.name)
# print(deck.cards[0].suit.value)
# print(deck.cards[0].suit)
#
# test = {Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)}
#

