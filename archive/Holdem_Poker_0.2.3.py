import random

class Card:
    def __init__(self,value,suit):
        self.value = value
        self.suit = suit

    def show(self):
        print('{} of {}'.format(self.value, self.suit))

    def __repr__(self):
        return "Card('{}', '{}')".format(self.value,self.suit)

class Deck:
    def __init__(self):
        self.cards = []
        self.build()

    def build(self):
        face_cards = {
            11: 'Jack', 12: 'Queen', 13: 'King', 14: 'Ace',
            'Jack': 11, 'Queen': 12, 'King': 13, 'Ace': 14
        }
        for s in ['Spades','Hearts','Clubs','Diamonds']:
            for v in range(2,15):
                if v in face_cards:
                    card_value = face_cards[v]
                    self.cards.append(Card(card_value,s))
                else:
                    self.cards.append(Card(v, s))

    def show(self):
        for c in self.cards:
            c.show()

    def shuffle(self):
        for i in range(len(self.cards)-1,0,-1):
            r = random.randint(0,i)
            self.cards[i], self.cards[r] = self.cards[r], self.cards[i]

    def draw(self):
        return self.cards.pop()

class Player:

    seats = {i: None for i in range(8)}
    num_of_players = 0
    players = []

    def __init__(self,name,stack):
        self.name = name
        self.stack = stack
        self.seat = None
        self.seat_player()

        Player.num_of_players += 1
        Player.players.append(self)

    def seat_player(self):
        for s in Player.seats:
            if not Player.seats[s]:
                self.seat = s
                Player.seats[s] = self
                break

    def pip(self,amount):
        if self.stack - amount >= 0:
            self.stack = self.stack - amount
            return amount
        else:
            all_in = self.stack
            self.stack = 0
            return all_in

    def __repr__(self):
        return "Player('{}', {})".format(self.name,self.stack)

    def __str__(self):
        return "{}, stack: {}".format(self.name,self.stack)

def seat_players(players):
    for p in players:
        Player(p[0],p[1])

class Hand(Player):

    holdemPositions = [
        'BU',
        'CO',
        'HJ',
        'LJ',
        'UTG+1',
        'UTG'
    ]

    small_blind_amt = 2
    big_blind_amt = 3
    num_of_hands = 0

    def __init__(self):

        self.hand_number = Hand.num_of_hands + 1
        self.players_in_hand = []
        for p in Player.seats:
            if Player.seats[p].stack >= self.big_blind_amt:
                self.players_in_hand.append(self.PlayerInHand(Player.seats[p]))
        self.n_players_in_hand = len(self.players_in_hand) # Remove later
        self.positions = {}
        self.assign_position()
        self.pot = 0
        self.postBlinds()
        self.deck = Deck()
        self.deck.shuffle()
        self.dealCards(self.deck)

        Hand.num_of_hands += 1

    class PlayerInHand(Player):
        def __init__(self, player: Player):
            self.player = player
            self.position = None
            self.starting_stack = self.player.stack
            self.current_bet = 0
            self.holeCards = []

        def draw(self, deck: Deck):
            self.holeCards.append(deck.draw())

        def show_holeCards(self):
            for c in self.holeCards:
                c.show()

        def fold(self):
            self.holeCards.clear()

        def bet(self, amount):
            bet = self.player.pip(amount - self.current_bet)
            self.current_bet = amount
            return bet

        def __repr__(self):
            return "PlayerInHand(Player('{}', {})) and {}".format(self.player.name, self.player.stack, self.starting_stack)

        def __str__(self):
            return "{} stack: {} and startstack: {}".format(self.player.name, self.player.stack, self.starting_stack)

    def assign_position(self):
        # Implement Hold'em rules for position ordering
        # There is always a small and big blind. Additional positions then start from the Button anti-clockwise.
        # Lastly, UTG+1 only appears when there is already a UTG
        hand_positions = []
        if len(self.players_in_hand) == 2:
            hand_positions = ['SB', 'BB']
        elif len(self.players_in_hand) > 2:
            hand_positions = Hand.holdemPositions[0:(len(self.players_in_hand)-2)]
            hand_positions.extend(['BB','SB'])
            hand_positions.reverse()
            if 'UTG+1' in hand_positions and 'UTG' not in hand_positions:
                hand_positions[hand_positions.index('UTG+1')] = 'UTG'

        m = len(self.players_in_hand)
        n = 0
        for p in hand_positions:
            # Unsure whether to have dict of ints or position name strings
            #self.positions[n] = self.players_in_hand[(Hand.num_of_hands + n) % m]
            self.positions[p] = self.players_in_hand[(Hand.num_of_hands + n) % m]
            self.positions[p].position = p
            n += 1

    def postBlinds(self):
        self.pot += self.positions['SB'].bet(Hand.small_blind_amt) + self.positions['BB'].bet(Hand.big_blind_amt)

    def dealCards(self, deck: Deck):
        two_hole_cards = 0
        while two_hole_cards != 2:
            for p in self.positions:
                self.positions[p].draw(deck)
            two_hole_cards += 1

    def preflop(self):
        self.preflop_positions = self.positions
        for p in self.preflop_positions:
            pass


    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return "Hand {}".format(self.hand_number)





player_list = [
    ['Young White TAG',500],
    ['ME',500],
    ['Young Asian LAG',500],
    ['Young Asian TAG',0],
    ['Old Asian Laggy',500],
    ['Fat Old White Guy',500],
    ['White Pro',500],
    ['Indian LAG',500]
]



seat_players(player_list)


h1 = Hand()
# print('Hand 1: {}'.format(h1.__dict__))
h2 = Hand()
h3 = Hand()
h4 = Hand()
# h5 = Hand()
# h6 = Hand()
# h7 = Hand()
# h8 = Hand()



print(Player.__dict__)
print(Hand.__dict__)
print(h1.__dict__)
print(h1.players_in_hand[1].player.show)
# print('Hand 1: {}'.format(h1.__dict__))
# print('Hand 2: {}'.format(h2.__dict__))
# print('Hand 3: {}'.format(h3.__dict__))
# print('Hand 4: {}'.format(h4.__dict__))
# print('Hand 5: {}'.format(h5.__dict__))
# print('Hand 6: {}'.format(h6.__dict__))
# print('Hand 7: {}'.format(h7.__dict__))
# print('Hand 8: {}'.format(h8.__dict__))

print(h1.players)
print(h1.players_in_hand)
print(h1.positions)

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