from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
import random
from .automated_trader import AutomatedTrader


class Constants(BaseConstants):
    name_in_url = 'producer_consumer'
    players_per_group = 4
    num_rounds = 2
    endowment = c(50)
    reward = c(20)
    red = 'Red'
    blue = 'Blue'
    trade_good = 'Trade Good'


class Subsession(BaseSubsession):
    
    #tried making transaction count belong to Subsession
    fc_transactions = models.IntegerField()
    
    def creating_session(self):
        if self.round_number == 1:

            # puts players into groups of size players_per_group
            self.group_randomly()

            # depends on if traders are on or off
            if self.session.config['automated_traders']:
                n_groups = len(self.get_groups()) * 2

            else:
                n_groups = len(self.get_groups())

            # create random pairings
            # for the whole session
            # a way to pair people given certain probabilities of
            # getting paired within your group or within the other group
            self.session.vars['pairs'] = []
            for r in range(Constants.num_rounds):
                # maps traders to their trading partners
                # (group_id, player_id) <=> (group_id, player_id)
                # so that a player can look up who their trading partner is
                # in this map
                pairs = {}
                groups = []
                for gi in range(n_groups):
                    # create player ids in group
                    # ex: 1,2,3,4
                    g = [i for i in range(Constants.players_per_group)]
                    
                    # shuffle player numbers
                    # ex: 1,3,2,4
                    random.shuffle(g)

                    # NOTE: self.session.config['probability_of_same_group'] times
                    # Constants.players_per_group needs to cleanly divide 2.
                    index = int(Constants.players_per_group *
                        self.session.config['probability_of_same_group'])
                    assert(index % 2 == 0)

                    # sampling probability_of_same_group % of players from g
                    # ex: 1,3
                    g_sample_homogeneous = g[:index]
                    
                    # sampling other 1 - probability_of_same_group % of players from g
                    # ex: 2,4
                    g_sample_heterogeneous = g[index:]
                    # pairing homogeneous
                    # ex: (0,1) <=> (0,3)
                    #     (0,3) <=> (0,1)
                    for i in range(0, index, 2):
                        pairs[(gi, g_sample_homogeneous[i])] = (gi, g_sample_homogeneous[i + 1])
                        pairs[(gi, g_sample_homogeneous[i + 1])] = (gi, g_sample_homogeneous[i])
                    # store the heterogeneous players so they can be paired later
                    groups.append(g_sample_heterogeneous)
   
                # pair traders between groups
                # randomize trader order within each group
                for i, _ in enumerate(groups):
                    random.shuffle(groups[i])

                g = []
                groups_ = groups.copy()
                # randomly select 2 different groups. then select 1 random traders
                # from each group. remove those traders from their respective group
                # lists and put them in the pairs list as a pair.
                # It is possible to get left with 2 traders from the same group
                # at the end. If this happens, scrap it and start over.
                # Repeat until you get a working heterogeneous pairing for each
                # trader.
                while any(groups):
                    indices = [i for i, gl in enumerate(groups) if len(gl) > 0] # indices of non-empty groups
                    if len(indices) < 2:
                        g = []
                        groups = groups_.copy()
                        continue
                    i0, i1 = random.sample(indices, 2)
                    p0 = (i0, groups[i0].pop())
                    p1 = (i1, groups[i1].pop())
                    g.append((p0, p1))

                #g = [(i, p) for i in range(n_groups) for p in groups[i]]
                # num groups needs to be even (b/c one bot group per player group)
                # therefore len(g) is even

                # ex: (0,4) <=> (1,8)
                #     (1,8) <=> (0,4)
                for gg in g:
                    pairs[gg[0]] = gg[1]
                    pairs[gg[1]] = gg[0]

                self.session.vars['pairs'].append(pairs)

            # if there is only 1 group, then we can do another loop after this
            # one and do the exact same shit, except instantiating bots
            # instead of getting players with p.

            # if there can be more than 1 group, we can easily just repeat the
            # loop some number of times for the number of bot groups. And,
            # we will also need to change the loop above to
            # do not just 0 and 1 for g index but other numbers, and also change
            # the method for getting your group index since looking at your
            # color will not suffice anymore.

            # BOTS
            self.session.vars['automated_traders'] = {}
            # automated traders are always in 2nd half of groups

            ### ONLY CREATE BOTS IF BOT TREATMENT IS TURNED ON

            # only create bots if the bot treatment is on
            if self.session.config['automated_traders']:

                for gi in range(n_groups // 2, n_groups):
                    group_color = Constants.blue
                    roles = [Constants.trade_good for n in range(Constants.players_per_group // 2)]
                    roles += [group_color for n in range(Constants.players_per_group // 2)]
                    random.shuffle(roles)

                    # within the pair, find group number and position in group
                    for pi in range(Constants.players_per_group):
                        trader = AutomatedTrader(self.session, pi + 1)
                        trader.participant.vars['group_color'] = group_color
                        trader.participant.vars['group'] = gi
                        trader.participant.payoff += Constants.endowment
                        trader.participant.vars['token'] = roles[pi]
                        self.session.vars['automated_traders'][(gi, pi)] = trader

            # player groups
            for g_index, g in enumerate(self.get_groups()):
                group_color = Constants.red

                # define random roles for players (producer/consumer),
                # ensuring half are producers and half are consumers
                # denotes half with a trade good
                # denotes half with group color
                roles = [Constants.trade_good for n in range(Constants.players_per_group // 2)]
                roles += [group_color for n in range(Constants.players_per_group // 2)]
                random.shuffle(roles)

                # set each player's group color, and starting token (which
                # determines who is going to be a producer vs consumer
                # whatever number (p_index) the player is defines role
                for p_index, p in enumerate(g.get_players()):
                    p.participant.vars['group_color'] = group_color
                    p.participant.vars['group'] = g_index
                    p.participant.vars['token'] = roles[p_index]
                    p.participant.payoff += Constants.endowment
            
        else:
            self.group_like_round(1)
            
        # set number of transactions back to 0 each round
        self.fc_transactions = 0
        
            
class Group(BaseGroup):
    pass
    

class Player(BasePlayer):
    # For detecting bots in this section of the game
    trading = models.LongStringField(blank=True)

    role_pre = models.StringField() # 'Producer', 'Consumer'
    other_role_pre = models.StringField()
    token_color = models.StringField() # Constants.red, Constants.blue, None
    other_token_color = models.StringField()
    group_color = models.StringField() # Constants.red, Constants.blue
    other_group_color = models.StringField()
    trade_attempted = models.BooleanField(
        choices=[
            [False, 'No'],
            [True, 'Yes'],
        ]
    )
    trade_succeeded = models.BooleanField()
                
    def set_payoffs(self, round_payoff):
        self.payoff = round_payoff
