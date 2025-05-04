import random

class Card:
    face_cards = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
    def __init__(self,rank,suit):
        self.rank = rank
        self.suit = suit
        if rank in Card.face_cards:
            self.value = Card.face_cards[rank]
        else:
            self.value = rank

    def show(self):
        print('{} of {}'.format(self.value, self.suit))

    def __repr__(self):
        return "Card('{}', '{}')".format(self.rank,self.suit)

    def __str__(self):
        return "{}{}".format(self.value, self.suit)

class Deck:
    suits = '♠ ♥ ♦ ♣'.split()
    ranks = list(range(2,15))
    def __init__(self):
        self.cards = [Card(r, s) for s in Deck.suits for r in Deck.ranks]

    def show(self):
        for c in self.cards:
            c.show()

    def shuffle(self):
        for i in range(len(self.cards)-1,0,-1):
            r = random.randint(0,i)
            self.cards[i], self.cards[r] = self.cards[r], self.cards[i]

    def draw(self):
        return self.cards.pop()

class Table:
    def __init__(self,num_of_seats = 8):
        self.seats = {s: None for s in range(num_of_seats)}

    def leave_seat(self,seat_number):
        self.seats[seat_number] = None

class Player:
    table = Table()
    num_of_players = 0
    wait_list = []

    def __init__(self,name,stack,strategy):
        self.name = name
        self.stack = stack
        self.strategy = strategy
        self.seat = None
        self.on_break = False

        Player.num_of_players += 1
        self.seat_player()

        # In the Hand
        self.position = None
        self.current_bet = 0
        self.hole_cards = []
        self.folded = False
        self.all_in = False

    def seat_player(self):
        found_seat = []
        for s in Player.table.seats:
            if not Player.table.seats[s]:
                self.seat = s
                Player.table.seats[s] = self
                found_seat.append(True)
                break
            else:
                found_seat.append(False)
        if not any(found_seat):
            Player.wait_list.append(self)

    def leave_game(self):
        Player.table.leave_seat(self.seat)
        if Player.wait_list:
            Player.wait_list[0].seat_player()
            Player.wait_list.pop(0)
        return [self.name, self.stack, self.strategy]

    def take_break(self):
        self.on_break = True

    def resume_play(self):
        self.on_break = False

    # Put-money-In-Pot. Make sure that pip's amount is always "to_call" and not the total bet
    def pip(self, amount):
        if self.stack - amount > 0:
            self.stack -= amount
            self.current_bet += amount
            return amount
        else:
            allin = self.stack
            self.stack = 0
            self.current_bet += allin
            self.all_in = True
            return allin

    def draw(self, deck: Deck):
        self.hole_cards.append(deck.draw())

    def show_hole_cards(self):
        for c in self.hole_cards:
            c.show()

    def can_act(self):
        return not self.folded and not self.all_in

    def check(self):
        action_check = ('CHECK', 0)
        print("Player {} in {} checks.".format(self.name,self.position))
        return action_check

    # Make sure amount is "to_call"
    def call(self, amount):
        action_call = ('CALL', self.pip(amount))
        print("Player {} in {} calls {} more for a total of {}.".format(self.name, self.position, action_call[1], self.current_bet))
        if self.all_in: print("Player {} is All-In.".format(self.name))
        return action_call

    # Always first bet of round, ie can never be used preflop and never if another player has already bet
    # ie self.current_bet must always be 0
    def bet(self, amount, x=1.0):
        action_bet = ('BET', self.pip(round(x * amount)))
        if self.all_in:
            action_all_in = ('ALL-IN', action_bet[1])
            print("Player {} in {} goes All-In for {}.".format(self.name, self.position, self.current_bet))
            return action_all_in
        else:
            print("Player {} in {} bets {}.".format(self.name, self.position, self.current_bet))
            return action_bet

    # amount should be total amount of raise, not "to_call"
    def raise_holdem(self, amount, x=3.0):
        action_raise = ('RAISE', self.pip(round(x * amount) - self.current_bet))
        if self.all_in:
            action_all_in = ('ALL-IN', action_raise[1])
            print("Player {} in {} goes All-In for {}.".format(self.name, self.position, self.current_bet))
            return action_all_in
        else:
            print("Player {} in {} raises to {}.".format(self.name, self.position, self.current_bet))
            return action_raise

    def go_all_in(self):
        action_allin = ('ALL-IN', self.pip(self.stack))
        print("Player {} in {} goes All-In for {}.".format(self.name, self.position, self.current_bet))
        return action_allin

    def fold(self):
        self.hole_cards.clear()
        self.folded = True
        action_fold = ('FOLD', 0)
        print("Player {} in {} folds.".format(self.name, self.position,))
        return action_fold

    def action_pre_flop(self, pot, highest_bet, to_call, raise_amount, raised_pre, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
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
        return "Player('{}', {}, '{}')".format(self.name,self.stack,self.strategy)

    def __str__(self):
        return "{}, stack: {}, {}".format(self.name,self.stack,self.strategy)

def seat_players(players):
    return [Player(p[0],p[1],p[2]) for p in players]

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

    def __init__(self, small_blind_amt=2, big_blind_amt=3):
        # Start of Hand
        self.hand_number = Hand.num_of_hands + 1
        self.small_blind_amt = small_blind_amt
        self.big_blind_amt = big_blind_amt
        self.players_in_hand = []
        for s,p in Player.table.seats.items():
            if p:
                if p.stack > 0 and not p.on_break:
                    self.players_in_hand.append(p)
        self.n_players_in_hand = len(self.players_in_hand)
        if self.n_players_in_hand == 2:
            self.headsup = True
        elif self.n_players_in_hand > 2:
            self.headsup = False
        self.positions = {}
        self.positionsInt = {}
        self.assign_position()
        self.pots = [self.Pot()]
        self.current_bets = {p: 0 for p in self.players_in_hand}
        self.post_blinds()
        self.deck = Deck()
        self.deck.shuffle()
        self.deal_hole_cards(self.deck)

        # Preflop
        self.is_preflop = True
        self.highest_bet = self.big_blind_amt
        self.raise_amt = self.big_blind_amt
        self.raised_pre = 1  # Keep track of 3bet pot, 4bet pot etc.
        #self.betting_round()
        self.preflop()

        Hand.num_of_hands += 1

    class Pot:
        num_of_pots = 0
        def __init__(self):
            self.pot_number = Hand.Pot.num_of_pots
            self.pot = 0
            self.bets = {}
            self.eligible_players = set()

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

    def tot_value_pot(self):
        current_bets_val = sum([v for v in self.current_bets.values()])
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
            hand_positions = Hand.holdemPositions[0:(m - 2)]
            hand_positions.extend(['BB', 'SB'])
            hand_positions.reverse()
            if m == 8:
                hand_positions[hand_positions.index('UTG+1')] = 'UTG'
                hand_positions[hand_positions.index('UTG+2')] = 'UTG+1'
            elif m == 7:
                hand_positions[hand_positions.index('UTG+2')] = 'UTG'

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
        sb.pip(self.small_blind_amt)
        bb.pip(self.big_blind_amt)
        # self.current_bets[sb] = sb.pip(self.small_blind_amt)
        # self.current_bets[bb] = bb.pip(self.big_blind_amt)
        ## Old Way
        # self.pots[0].add_bet(sb, sb.pip(self.small_blind_amt))
        # self.pots[0].add_bet(bb, bb.pip(self.big_blind_amt))
        # self.current_bets[sb] = sb.current_bet
        # self.current_bets[bb] = bb.current_bet


    def deal_hole_cards(self, deck: Deck):
        two_hole_cards = 0
        while two_hole_cards != 2:
            for person in self.positions:
                self.positions[person].draw(deck)
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

        m = self.n_players_in_hand
        p = 0       # incrementor to loop through players. Resets when a raise occurs
        while p < m:
            player_to_act = self.players_in_hand[(p + start) % m]

            if not player_to_act.can_act():
                p += 1
            else:

                if self.highest_bet - player_to_act.current_bet < self.raise_amt:
                    open_action = False
                else:
                    open_action = True

                ## Old
                # pots_tot_val = sum([p.value_pot() for p in self.pots])
                to_call = self.highest_bet - player_to_act.current_bet

                player_action, bet = player_to_act.action_pre_flop(
                    self.tot_value_pot(),
                    self.highest_bet,
                    to_call,
                    self.raise_amt,
                    self.raised_pre,
                    open_action
                )

                # Check here if player_to_act.allin == true
                # Generate sidepot
                # Track which players are eligible for sidepots and mainpots

                if player_action == 'CHECK':
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action,bet, self.highest_bet, player_to_act.current_bet, self.pots[0], player_to_act.all_in,player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'CALL':
                    # self.pots[0].pot += bet   # Broken. Doesn't add to sidepots
                    self.current_bets[player_to_act] = player_to_act.current_bet
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action, bet, self.highest_bet, player_to_act.current_bet, self.pots[0],player_to_act.all_in,player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'RAISE':
                    # self.pots[0].pot += bet   # Broken. Doesn't add to sidepots
                    self.current_bets[player_to_act] = player_to_act.current_bet
                    self.raise_amt = player_to_act.current_bet - self.highest_bet
                    self.highest_bet = max(self.highest_bet, player_to_act.current_bet)
                    self.raised_pre += 1
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action, bet, self.highest_bet, player_to_act.current_bet, self.pots[0],player_to_act.all_in, player_to_act.position, player_to_act))
                    start = start + p
                    p = 0
                    p += 1
                elif player_action == 'FOLD':
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action, bet, self.highest_bet, player_to_act.current_bet, self.pots[0],player_to_act.all_in, player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'ALL-IN':
                    # self.pots[0].pot += bet   # Broken. Doesn't add to sidepots
                    self.current_bets[player_to_act] = player_to_act.current_bet
                    if player_to_act.current_bet - self.highest_bet >= self.raise_amt:
                        self.raise_amt = player_to_act.current_bet - self.highest_bet
                        self.raised_pre += 1
                    self.highest_bet = max(self.highest_bet, player_to_act.current_bet)
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p, start, m, self.players_in_hand.index(player_to_act), player_action, bet,self.highest_bet, player_to_act.current_bet, self.pots[0], player_to_act.all_in,player_to_act.position, player_to_act))
                    start = start + p
                    p = 0
                    p += 1
        self.create_pots(self.players_in_hand)

    def create_pots(self,players_in_round):
        active_pot_index = len(self.pots) - 1
        all_in_players = set(p.all_in for p in players_in_round)

        ## Remember to add functionality to return remainder of bet for player who's all in is called by another all-in that doesn't cover the first player

        # Figure out how to get around the min function
        # def calculate_bets(players, index, previous=0, amt=0, looping=False):
        #     if looping:
        #         bets_value = sum([(min(p.current_bet, amt) - previous) for p in players])
        #     else:
        #         bets_value = sum([p.current_bet - previous for p in players])
        #     self.pots[index].pot += bets_value
        #     for p in players:
        #         if not p.folded:
        #             self.pots[index].eligible_players.add(p)
        #     print(self.pots[index])
        #
        # if any(all_in_players):
        #     all_in_bets = sorted(set(p.current_bet for p in players_in_round if p.all_in))
        #     remaining = [p for p in players_in_round]
        #     prev = 0
        #     for amount in all_in_bets:
        #         calculate_bets(remaining, active_pot_index, prev, amount, True)
        #         remaining = [p for p in players_in_round if (p.current_bet - amount) > 0]
        #         prev = amount
        #         self.pots.append(self.Pot())
        #         active_pot_index += 1
        #     calculate_bets(remaining,active_pot_index,max(all_in_bets))
        # else:
        #     calculate_bets(players_in_round, active_pot_index)

        if any(all_in_players):
            all_in_bets = sorted(set(p.current_bet for p in players_in_round if p.all_in))
            remaining = [p for p in players_in_round]
            prev = 0
            n = 0
            for amount in all_in_bets:
                bets_val = sum([(min(p.current_bet,amount) - prev) for p in remaining])
                self.pots[active_pot_index + n].pot += bets_val
                for p in remaining:
                    if not p.folded:
                        self.pots[active_pot_index + n].eligible_players.add(p)
                print(self.pots[active_pot_index + n])
                remaining = [p for p in players_in_round if (p.current_bet - amount) > 0]
                prev = amount
                n += 1
                self.pots.append(self.Pot())
            current_bets_val = sum([p.current_bet - max(all_in_bets) for p in remaining])
            self.pots[active_pot_index + n].pot += current_bets_val
            for p in remaining:
                if not p.folded:
                    self.pots[active_pot_index + n].eligible_players.add(p)
            print(self.pots[active_pot_index + n])
        else:
            current_bets_val = sum([p.current_bet for p in players_in_round])
            self.pots[active_pot_index].pot += current_bets_val
            for p in players_in_round:
                if not p.folded:
                    self.pots[active_pot_index].eligible_players.add(p)
            print(self.pots[active_pot_index])

    def preflop(self):
        self.betting_round()

    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return "Hand {}".format(self.hand_number)





player_list = [
    ['Young White TAG',15, 'passive']
    ,['ME',10, 'passive']
    ,['Young Asian LAG',3, 'passive']
    ,['Young Asian TAG',200, 'aggro']
    ,['Old Asian Laggy',500, 'scared']
    ,['Fat Old White Guy',1000, 'passive']
    ,['White Pro',450, 'aggro']
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

print(h1.players_in_hand[1].stack)
# print(h1.players_in_hand[4])
# print(h1.players_in_hand[4].current_bet)
print(h1.pots)

print(h1.players_in_hand[6].hole_cards)
print(h1.players_in_hand)
print(h1.positions)
print(h1.positions['CO'].hole_cards)

for p in h1.pots:
    print("{}    Eligible players: {}".format(p, p.eligible_players))

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