import random

class Card:
    face_cards = {10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'}

    def __init__(self,rank,suit):
        self.rank = rank
        self.suit = suit
        self.value = Card.face_cards.get(rank, rank)

    def __repr__(self):
        return f"Card('{self.rank}', '{self.suit}')"

    def __str__(self):
        return f"{self.value}{self.suit}"

class Deck:
    suits = '♠ ♥ ♦ ♣'.split()
    ranks = tuple(range(2,15))
    def __init__(self):
        self.cards = [Card(r, s) for s in Deck.suits for r in Deck.ranks]

    def show(self):
        for c in self.cards:
            print(c)

    def shuffle(self):
        for i in range(len(self.cards)-1,0,-1):
            r = random.randint(0,i)
            self.cards[i], self.cards[r] = self.cards[r], self.cards[i]

    def draw(self):
        return self.cards.pop()

class Table:
    def __init__(self,num_of_seats = 9):
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
        self.player_hand = []

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
        if self.hole_cards:
            print(f"{self.name}: {self.hole_cards[0]} {self.hole_cards[1]}")
        else:
            print(f"{self.name} has no hole cards")


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

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
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

    def action_flop(self, pot, highest_bet, to_call, raise_amount, raised_pre, raised_flop, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
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

    def action_turn(self, pot, highest_bet, to_call, raise_amount, raised_pre, raised_flop, raised_turn, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
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

    def action_river(self, pot, highest_bet, to_call, raise_amount, raised_pre, raised_flop, raised_turn, raised_river, open_action=True):

        if self.strategy == 'passive':
            if to_call == 0:
                return self.check()
            elif raised_pre >= 3:
                return self.fold()
            else:
                return self.call(to_call)

        if self.strategy == 'calling station':
            if to_call == 0:
                return self.check()
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
        self.post_blinds()
        self.deck = Deck()
        self.deck.shuffle()
        self.deal_hole_cards(self.deck)

        # Preflop
        self.game_state = 'PREFLOP'
        self.highest_bet = self.big_blind_amt
        self.raise_amt = self.big_blind_amt
        self.n_raises = {'PREFLOP': 1, 'FLOP': 0, 'TURN': 0, 'RIVER': 0} # Keep track of 3bet pot, 4bet pot etc.
        #self.betting_round()
        self.preflop()
        self.community_board = []

        # Flop
        self.flop()

        # Turn
        self.turn()

        # River
        self.river()

        Hand.num_of_hands += 1

    class Pot:
        num_of_pots = 0
        def __init__(self):
            self.pot_number = Hand.Pot.num_of_pots
            self.pot = 0
            self.eligible_players = set()

            Hand.Pot.num_of_pots += 1

        @classmethod
        def remove_pot(cls):
            cls.num_of_pots -= 1

        def __repr__(self):
            return "Pot()"

        def __str__(self):
            if self.pot_number == 0:
                return "Main Pot: ${}".format(self.pot)
            else:
                return "Side Pot {}: ${}".format(self.pot_number,self.pot)

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

    def deal_hole_cards(self, deck: Deck):
        two_hole_cards = 0
        while two_hole_cards != 2:
            for person in self.positions:
                self.positions[person].draw(deck)
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
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action,bet, self.highest_bet, player_to_act.current_bet, self.pots[0], player_to_act.all_in,player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'CALL':
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action, bet, self.highest_bet, player_to_act.current_bet, self.pots[0],player_to_act.all_in,player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'RAISE':
                    self.raise_amt = player_to_act.current_bet - self.highest_bet
                    self.highest_bet = max(self.highest_bet, player_to_act.current_bet)
                    self.n_raises[self.game_state] += 1
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action, bet, self.highest_bet, player_to_act.current_bet, self.pots[0],player_to_act.all_in, player_to_act.position, player_to_act))
                    start = start + p
                    p = 0
                    p += 1
                elif player_action == 'FOLD':
                    for pot in self.pots:
                        pot.eligible_players.discard(player_to_act)
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p,start,m,self.players_in_hand.index(player_to_act),player_action, bet, self.highest_bet, player_to_act.current_bet, self.pots[0],player_to_act.all_in, player_to_act.position, player_to_act))
                    p += 1
                elif player_action == 'ALL-IN':
                    if player_to_act.current_bet - self.highest_bet >= self.raise_amt:
                        self.raise_amt = player_to_act.current_bet - self.highest_bet
                        self.n_raises[self.game_state] += 1
                    if player_to_act.current_bet > self.highest_bet:
                        start = start + p
                        p = 0
                    self.highest_bet = max(self.highest_bet, player_to_act.current_bet)
                    print('p:{} start:{}  m:{}  i:{}  {} bet:{}   highestBet:{}   playerCurrentBet:{}    Pot:{}  allin?:{}   Pos:{}   {}'.format(p, start, m, self.players_in_hand.index(player_to_act), player_action, bet,self.highest_bet, player_to_act.current_bet, self.pots[0], player_to_act.all_in,player_to_act.position, player_to_act))
                    p += 1
        self.create_pots(players_in_round)

    def create_pots(self,players_in_round):
        active_pot_index = len(self.pots) - 1
        all_in_players = set(p.all_in for p in players_in_round)

        def calculate_bets(players, index, previous=0, amt=0, looping=False):
            if looping:
                bets_value = sum([(min(p.current_bet, amt) - previous) for p in players])
            else:
                bets_value = sum([p.current_bet - previous for p in players])
            self.pots[index].pot += bets_value
            for p in players:
                if not p.folded:
                    self.pots[index].eligible_players.add(p)
            print(self.pots[index])

        if any(all_in_players):
            all_in_bets = set(p.current_bet for p in players_in_round if p.all_in)
            levels = sorted(all_in_bets.union({max(p.current_bet for p in players_in_round)}))
            remaining = [p for p in players_in_round]
            prev = 0
            for amount in levels:
                calculate_bets(remaining, active_pot_index, prev, amount, True)
                remaining = [p for p in players_in_round if (p.current_bet - amount) > 0]
                prev = amount
                if len(remaining) > 1:
                    self.pots.append(self.Pot())
                    active_pot_index += 1
                elif len(remaining) == 1:
                    remaining[0].stack += remaining[0].current_bet - prev
                    print("Returned bet of {} for player: {}".format(remaining[0].current_bet - prev, remaining[0]))
                    break
            called_allin = [p for p in players_in_round if (p.current_bet - max(all_in_bets)) == 0 and p.can_act()]
            if len(called_allin) > 1:
                self.pots.append(self.Pot())
                active_pot_index += 1
                calculate_bets(called_allin, active_pot_index,max(all_in_bets))
                print("players remain who aren't all-in after calling all-in")
        else:
            calculate_bets(players_in_round, active_pot_index)

        for player in players_in_round:
            player.current_bet = 0
        self.highest_bet = 0
        self.raise_amt = 0

        # if any(all_in_players):
        #     all_in_bets = sorted(set(p.current_bet for p in players_in_round if p.all_in))
        #     remaining = [p for p in players_in_round]
        #     prev = 0
        #     counter = 0
        #     for amount in all_in_bets:
        #         calculate_bets(remaining, active_pot_index, prev, amount, True)
        #         remaining = [p for p in players_in_round if (p.current_bet - amount) > 0]
        #         prev = amount
        #         counter += 1
        #         if len(remaining) > 1:
        #             self.pots.append(self.Pot())
        #             active_pot_index += 1
        #             if counter == len(all_in_bets):
        #                 calculate_bets(remaining, active_pot_index, prev)
        #                 print("bets occured after all-in, and players remain who aren't all-in")
        #         elif len(remaining) == 1:
        #             remaining[0].stack += remaining[0].current_bet - prev
        #             print("Returned bet of {} for player: {}".format(remaining[0].current_bet - prev, remaining[0]))
        #             break
        #     called_allin = [p for p in players_in_round if (p.current_bet - max(all_in_bets)) == 0 and p.can_act()]
        #     if len(called_allin) > 1:
        #         self.pots.append(self.Pot())
        #         active_pot_index += 1
        #         calculate_bets(called_allin, active_pot_index, max(all_in_bets))
        #         print("players remain who aren't all-in after calling all-in")
        # else:
        #     calculate_bets(players_in_round, active_pot_index)
        #
        # for player in players_in_round:
        #     player.current_bet = 0
        # self.highest_bet = 0
        # self.raise_amt = 0

    def preflop(self):
        self.betting_round(self.players_in_hand)
        self.game_state = 'FLOP'

    def deal_flop(self):
        self.deck.draw() # burn card
        self.community_board.extend([self.deck.draw(),self.deck.draw(),self.deck.draw()])

    def show_board(self):
        print("------ Community Cards ------")
        if not self.community_board:
            print(" PREFLOP; No community cards dealt yet\n-----------------------------")
        else:
            for c in self.community_board:
                print("   {}".format(c),end="")
            print("\n-----------------------------")

    def flop(self):
        flop_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_flop()
        self.show_board()
        self.betting_round(flop_players)
        self.game_state = 'TURN'

    def deal_street(self):
        # For dealing Turn and River cards (commonly referred to as "streets")
        self.deck.draw()  # burn card
        self.community_board.append(self.deck.draw())

    def turn(self):
        turn_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        self.betting_round(turn_players)
        self.game_state = 'RIVER'

    def river(self):
        river_players = [remaining for remaining in self.players_in_hand if remaining.can_act()]
        self.deal_street()
        self.show_board()
        self.betting_round(river_players)

    def __repr__(self):
        return "Hand()"

    def __str__(self):
        return "Hand {}".format(self.hand_number)





player_list = [
    ['Young White TAG',500, 'passive']
    ,['ME',469, 'passive']
    ,['Young Asian LAG',200, 'passive']
    ,['Young Asian TAG',250, 'aggro']
    ,['Old Asian Laggy',300, 'scared']
    ,['Fat Old White Guy',1000, 'passive']
    ,['White Pro',450, 'aggro']
    ,['Indian LAG',900, 'calling station']
    ,['Villain LAG',1400, 'calling station']
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

print(h1.n_raises)
print(h1.community_board)
h1.show_board()

h1.positions['BU'].show_hole_cards()

print(Card.__dict__)

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