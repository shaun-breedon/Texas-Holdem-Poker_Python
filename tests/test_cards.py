from holdem.core.cards import *
from holdem.core.enums import *

d = Deck(shuffle_on_init=True)
print(d)
hand = d.draw(2)           # -> list[Card] of length 2
print(hand)
one = d.draw_one()         # -> Card
print(one)
d.reset(shuffle_on_reset=True)      # full deck, shuffled
print(d)
players = d.deal(6, 2)     # 6 hands, 2 cards each
print(players)
assert len(d) == 52 - (6*2)
# sorting behaviour:
cards = [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.CLUBS), Card(Rank.KING, Suit.HEARTS)]
print(sorted(cards, reverse=True))
assert sorted(cards, reverse=True)[0].suit == Suit.SPADES  # because suit tie-breaker

assert Card(Rank.ACE, Suit.CLUBS) < Card(Rank.ACE, Suit.SPADES)