from collections import defaultdict
import random

suits = ['Spades','Hearts','Clubs','Diamonds']
values = ['Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten','Jack','Queen','King','Ace']

deck_of_cards = defaultdict(dict)
for x in suits:
    for i in values:
        card_name = i + ' of ' + x
        deck_of_cards[card_name] = {'Suit': x,'Value': i}
dict(deck_of_cards)
#print(deck_of_cards)

deck = []
for x in suits:
    for i in values:
        deck.append(
            {
                'Card': i + ' of ' + x,
                'Suit': x,
                'Value': i
            }
        )
#print(deck)

position = [
    'SB',
    'BB',
    'UTG',
    'UTG+1',
    'LJ',
    'HJ',
    'CO',
    'BU'
]

players = dict()
for p in position:
    players[p] = {'Hole Cards': [], "Chips": []}
#print(players)
print('Number of Players: ' + str(len(players)))

buyin = 500 # players buyin
for p in position:
    players[p]['Chips'] = buyin
#print(players)

random.shuffle(deck) # shuffle the deck

# print out the deck order
#for c in range(0,len(deck)):
#    print(deck[c]['Card'])


def dealcard(d,p,pos):
    p[pos]['Hole Cards'].append(d[0])
    d.pop(0)

# Deal the deck to players
def deal_holdem(d,p):
    positions = list(p.keys())
    i = 0
    while i < 2*len(positions):
        for n in positions:
            dealcard(d,p,n)
            i += 1


deal_holdem(deck,players)

#print(players)

# Print Player Cards
for p in players:
    players_cards = [d.get(list(d.keys())[0]) for d in players[p]['Hole Cards']]
    print(p + ' has', ', '.join(players_cards))

