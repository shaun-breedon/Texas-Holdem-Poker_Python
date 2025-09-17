suits = ['Spades','Hearts','Clubs','Diamonds']
faces = ['Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten','Jack','Queen','King','Ace']
values = list(range(2,15))
face_cards = {v+2: faces[v] for v in range(13)} | {faces[v]: v+2 for v in range(13)}

class Card:
    def __init__(self,value,suit):
        self.value = value
        self.suit = suit

    def fullcard(self):
        return '{} of {}'.format(self.value, self.suit)

def generate_deck(values,suits):
    deck = []
    for s in suits:
        for v in values:
            if v >= 11:
                card_value = face_cards[v]
                deck.append(Card(card_value,s))
            else:
                deck.append(Card(v, s))
    return deck

deck = generate_deck(values,suits)

print(deck)
for card in deck:
    print(card.fullcard())

# deck = [Card(v,s) for v in values for s in suits]
# card_deck = [deck[n].fullcard() for n in range(0,len(deck))]

# print(face_cards)
# print(values)
# print(deck)
# print(card_deck)

