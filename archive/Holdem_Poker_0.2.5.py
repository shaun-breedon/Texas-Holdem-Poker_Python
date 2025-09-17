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

    def __init__(self,name,stack,strategy):

        self.name = name
        self.stack = stack
        self.strategy = strategy
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
        return "Player('{}', {}, '{}')".format(self.name,self.stack,self.strategy)

    def __str__(self):
        return "{}, stack: {}, {}".format(self.name,self.stack,self.strategy)

def seat_players(players):
    for p in players:
        Player(p[0],p[1],p[2])

class Hand:

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

        # Start of Hand
        self.hand_number = Hand.num_of_hands + 1
        self.players_in_hand = []
        for p in Player.seats:
            if Player.seats[p]:
                if Player.seats[p].stack >= self.big_blind_amt:
                    self.players_in_hand.append(self.PlayerInHand(Player.seats[p]))
        self.n_players_in_hand = len(self.players_in_hand)
        if self.n_players_in_hand == 2:
            self.headsup = True
        elif self.n_players_in_hand > 2:
            self.headsup = False
        self.positions = {}
        self.positionsInt = {}
        self.assign_position()
        self.pots = [self.Pot()]
        self.post_blinds()
        self.deck = Deck()
        self.deck.shuffle()
        self.deal_hole_cards(self.deck)

        # Preflop
        self.is_preflop = True
        self.preflop_positions = [p for p in self.positions.values()]
        self.current_bet = Hand.big_blind_amt
        self.raise_amt = 0
        self.raised_preflop = 1  # Keep track of 3bet pot, 4bet pot etc.
        self.betting_round()
        #self.preflop()

        Hand.num_of_hands += 1

    class PlayerInHand(Player):
        def __init__(self, player: Player):

            self.player = player
            self.position = None
            self.starting_stack = self.player.stack
            self.player_current_bet = 0
            self.hole_cards = []
            self.folded = False
            self.allin = False

        def draw(self, deck: Deck):
            self.hole_cards.append(deck.draw())

        def show_hole_cards(self):
            for c in self.hole_cards:
                c.show()

        def bet(self, amount):
            if self.player.stack - (amount - self.player_current_bet) > 0:
                bet = self.player.pip(amount - self.player_current_bet)
                self.player_current_bet = amount
            else:
                bet = self.player.pip(amount - self.player_current_bet)
                self.player_current_bet = bet + self.player_current_bet
                self.allin = True
            return bet

        def check(self):
            action_check = ('CHECK',0)
            return action_check

        def call(self,amount):
            action_call = ('CALL', self.bet(amount))
            return action_call

        def raise_holdem(self,amount,x):
            action_raise = ('RAISE', self.bet(x*amount))
            return action_raise

        def allin_holdem(self):
            action_allin = ('ALL-IN', self.bet(self.player.stack + self.player_current_bet))
            return action_allin

        def fold(self):
            self.hole_cards.clear()
            self.folded = True
            action_fold = ('FOLD',0)
            return action_fold

        def action(self, pot, currentbet, raiseamount, raisedpreflop, openaction=True ):

            if self.player.strategy == 'passive':
                if currentbet == 0:
                    return self.check()
                elif raisedpreflop >= 3:
                    return self.fold()
                else:
                    return self.call(currentbet)

            elif self.player.strategy == 'aggro':
                if not openaction:
                    return self.call(currentbet)
                elif currentbet == 0:
                    return self.raise_holdem(pot,0.33)
                elif (currentbet + raiseamount - self.player_current_bet) > self.player.stack:
                    return self.allin_holdem()
                else:
                    return self.raise_holdem(currentbet, 5)

            elif self.player.strategy == 'scared':
                if currentbet == 0:
                    return self.check()
                elif currentbet == Hand.big_blind_amt:
                    return self.call(currentbet)
                else:
                    return self.fold()


            # if not self.allin:
            #     if self.player.strategy == 'passive':
            #         return self.bet(currentbet)
            #     elif self.player.strategy == 'aggro':
            #         return self.bet(5*currentbet)
            #     elif self.player.strategy == 'scared':
            #         if currentbet == Hand.big_blind_amt:
            #             return self.bet(currentbet)
            #         else:
            #             self.fold()
            #             return 0
            # else:
            #     return 0

        def __repr__(self):
            return "PlayerInHand(Player('{}', {}, '{}')) and {}".format(self.player.name,self.player.stack,self.player.strategy,self.starting_stack)

        def __str__(self):
            return "{} stack: {}, {} and startstack: {}".format(self.player.name,self.player.stack,self.player.strategy,self.starting_stack)

    class Pot:
        num_of_pots = 0

        def __init__(self):
            self.pot_number = Hand.Pot.num_of_pots
            self.pot = 0
            self.bets = {}

            Hand.Pot.num_of_pots += 1

        def add_bet(self, player, bet: int):
            self.bets[player] = bet

        def value_pot(self):
            value = sum(list(self.bets.values())) + self.pot
            return value

        def consolidate(self):
            self.pot = sum(list(self.bets.values()))
            self.bets.clear()

        def __repr__(self):
            return "Pot()"

        def __str__(self):
            if self.pot_number == 0:
                return "Main Pot: ${}".format(self.value_pot())
            else:
                return "Side Pot {}: ${}".format(self.pot_number,self.value_pot())


    def assign_position(self):
        # Implement Hold'em rules for position ordering
        # There is always a Button and Big Blind. Additional positions add the Small Blind then start from the Button anti-clockwise.
        # Lastly, UTG+1 only appears when there is already a UTG
        hand_positions = []
        if self.headsup:
            hand_positions = ['BB', 'BU']
        else:
            hand_positions = Hand.holdemPositions[0:(len(self.players_in_hand) - 2)]
            hand_positions.extend(['BB', 'SB'])
            hand_positions.reverse()
            if 'UTG+1' in hand_positions and 'UTG' not in hand_positions:
                hand_positions[hand_positions.index('UTG+1')] = 'UTG'

        m = len(self.players_in_hand)
        n = 0
        for p in hand_positions:
            # Unsure whether to have dict of ints or position name strings
            self.positions[p] = self.players_in_hand[(Hand.num_of_hands + n) % m]
            self.positions[p].position = p

            self.positionsInt[n] = self.players_in_hand[(Hand.num_of_hands + n) % m]
            self.positionsInt[n].position = p
            n += 1

    def post_blinds(self):
        bb = self.positions['BB']
        if self.headsup:
            sb = self.positions['BU']
        else:
            sb = self.positions['SB']
        self.pots[0].add_bet(sb, sb.bet(Hand.small_blind_amt))
        self.pots[0].add_bet(bb, bb.bet(Hand.big_blind_amt))

    def deal_hole_cards(self, deck: Deck):
        two_hole_cards = 0
        while two_hole_cards != 2:
            for p in self.positions:
                self.positions[p].draw(deck)
            two_hole_cards += 1

    def betting_round(self):

        # player_to_act index number start. Starts left of BB (2), and is updated to the last raiser.
        # in headsup, starts on the BU (1) (who also posts the small blind).
        if self.headsup and self.is_preflop:
            start = 1
        elif self.is_preflop:
            start = 2
        else:
            start = 0

        m = len(self.preflop_positions)
        p = 0       # incrementor to loop through players. Resets when a raise occurs
        while p < m:
            player_to_act = self.preflop_positions[(p + start) % m]

            if player_to_act.allin or player_to_act.folded:
                p += 1
            else:

                if self.current_bet - player_to_act.player_current_bet < self.raise_amt:
                    openaction = False
                else:
                    openaction = True

                pots_tot_val = sum([p.value_pot() for p in self.pots])

                player_action, bet = player_to_act.action(
                    pots_tot_val,
                    self.current_bet,
                    self.raise_amt,
                    self.raised_preflop,
                    openaction
                )

                # Check here if player_to_act.allin == true
                # Generate sidepot
                # Track which players are eligible for sidepots and mainpots

                if player_action == 'CHECK':
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   handCurrentBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.preflop_positions.index(player_to_act),player_action,bet, self.current_bet, player_to_act.player_current_bet, self.pots[0], player_to_act.allin,player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'CALL':
                    self.pots[0].pot += bet   # Broken. Doesn't add to sidepots
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   handCurrentBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.preflop_positions.index(player_to_act),player_action, bet, self.current_bet, player_to_act.player_current_bet, self.pots[0],player_to_act.allin,player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'RAISE':
                    self.pots[0].pot += bet   # Broken. Doesn't add to sidepots
                    self.raise_amt = player_to_act.player_current_bet - self.current_bet
                    self.current_bet = player_to_act.player_current_bet
                    self.raised_preflop += 1
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   handCurrentBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.preflop_positions.index(player_to_act),player_action, bet, self.current_bet, player_to_act.player_current_bet, self.pots[0],player_to_act.allin, player_to_act.position, player_to_act))
                    start = start + p
                    p = 0
                    p += 1
                elif player_action == 'FOLD':
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   handCurrentBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.preflop_positions.index(player_to_act),player_action, bet, self.current_bet, player_to_act.player_current_bet, self.pots[0],player_to_act.allin, player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'ALL-IN':
                    self.pots[0].pot += bet   # Broken. Doesn't add to sidepots
                    if player_to_act.player_current_bet - self.current_bet >= self.raise_amt:
                        self.raise_amt = player_to_act.player_current_bet - self.current_bet
                        self.raised_preflop += 1
                    self.current_bet = player_to_act.player_current_bet
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   handCurrentBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p, start, m, self.preflop_positions.index(player_to_act), player_action, bet,self.current_bet, player_to_act.player_current_bet, self.pots[0], player_to_act.allin,player_to_act.position, player_to_act))
                    start = start + p
                    p = 0
                    p += 1


    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return "Hand {}".format(self.hand_number)





player_list = [
    ['Young White TAG',500, 'passive']
    ,['ME',500, 'passive']
    ,['Young Asian LAG',500, 'passive']
    ,['Young Asian TAG',500, 'aggro']
    ,['Old Asian Laggy',500, 'scared']
    ,['Fat Old White Guy',500, 'passive']
    ,['White Pro',500, 'aggro']
    ,['Indian LAG',500, 'passive']
]



seat_players(player_list)


h1 = Hand()
# print('Hand 1: {}'.format(h1.__dict__))
# h2 = Hand()
# h3 = Hand()
# h4 = Hand()
# h5 = Hand()
# h6 = Hand()
# h7 = Hand()
# h8 = Hand()



print(Player.__dict__)
print(Hand.__dict__)
print(Hand.PlayerInHand.__dict__)
#print(h1.__dict__)
print('Hand 1: {}'.format(h1.__dict__))
# print('Hand 2: {}'.format(h2.__dict__))
# print('Hand 3: {}'.format(h3.__dict__))
# print('Hand 4: {}'.format(h4.__dict__))
# print('Hand 5: {}'.format(h5.__dict__))
# print('Hand 6: {}'.format(h6.__dict__))
# print('Hand 7: {}'.format(h7.__dict__))
# print('Hand 8: {}'.format(h8.__dict__))

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
print(h1.players_in_hand[1].player)
print(h1.players_in_hand[1].starting_stack)
print(h1.players_in_hand[1].player.stack)
# print(h1.players_in_hand[4])
# print(h1.players_in_hand[4].current_bet)
print(h1.pots)

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