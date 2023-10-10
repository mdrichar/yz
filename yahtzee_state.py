import itertools
from functools import reduce
import operator
import yahtzee_iterators as yzi
import random

none_held = (0,0,0,0,0,0)
no_row = -1
all_dice = 5
max_rolls_allowed = 3
max_turns=13
bonusThreshold = 63
bonusAmount = 35
yahtzeeSlot = 11
#for i in itertools.product(range(3),range(3)):
#    print(i)
roll_outcomes = yzi.getRollOutcomes()
slot_name = ["Ones","Twos","Threes","Fours","Fives","Sixes","Three of a kind","Four of a kind","Full House","Small Straight","Large Straight","Yahtzee","Chance"]


def randomRoll(diceCnt):
    result = list(none_held)
    for _ in range(diceCnt):
        randomFace = random.randrange(0,6)
        result[randomFace] += 1
    return tuple(result)

class Action:
    def __init__(self,held,rerolled,chosen_row):
        #print("Action: ", held,"Rerolled:",rerolled)
        self.held = held
        self.rerolled = rerolled
        self.chosen_row = chosen_row
    def __str__(self):
        if self.chosen_row >= 0:
            return "Score for " + slot_name[self.chosen_row]
        elif self.rerolled == all_dice:
            return "Roll All"
        else:
            return "Keep " + str(self.held) + " Reroll " + str(self.rerolled)
    def __repr__(self):
        return self.__str__()
    def isScoringYahtzee(self):
        return self.chosen_row == yahtzeeSlot

class State:
    def __init__(self,dice,remaining_rows, rolls_left, pts_needed_for_bonus, zeroed_yahtzee):
        assert type(pts_needed_for_bonus) == int
        self.dice = dice
        self.remaining_rows = remaining_rows
        self.rolls_left = rolls_left
        self.pts_needed_for_bonus = pts_needed_for_bonus
        self.zeroed_yahtzee = zeroed_yahtzee
    def __str__(self):
        return "     Dice " + str(self.dice) + str(self.remaining_rows) + str(self.rolls_left) + " PLB" + str(self.pts_needed_for_bonus) + " ZY" + str(self.zeroed_yahtzee)
    def __eq__(self,other):
        return (self.dice == other.dice and self.remaining_rows == other.remaining_rows and self.rolls_left == other.rolls_left 
                and self.pts_needed_for_bonus == other.pts_needed_for_bonus and self.zeroed_yahtzee == other.zeroed_yahtzee)
    def __hash__(self):
        return hash((self.dice,self.remaining_rows,self.rolls_left,self.pts_needed_for_bonus,self.zeroed_yahtzee))
    def openSlotCount(self):
        return sum(self.remaining_rows)
    def rollsLeft(self):
        return self.rolls_left
    def zeroedYahtzee(self):
        return self.zeroed_yahtzee
    def ptsNeededForBonus(self):
        return self.pts_needed_for_bonus
    
    def isFinalState(self):
        return self.openSlotCount() == 0
    
    def upperOnly(t):
        return t[0:6]


    def legal_actions(self):
        if self.rolls_left == 3:
            yield Action(none_held,all_dice,no_row)
        elif self.rolls_left == 0: # Can't reroll, must choose a row to apply score
            for r in range(len(self.remaining_rows)):
                if self.remaining_rows[r] > 0:
                    yield Action(none_held,0,r)
        else: # 1 or 2 rerolls left
            dice = self.dice
            for action in itertools.product(
            range(dice[0] + 1), range(dice[1] + 1), range(dice[2] + 1),range(dice[3] + 1),
            range(dice[4] + 1), range(dice[5] + 1)):
                yield Action(action,5-sum(action),no_row)



    def stateTransitionsFrom(self, action):
        if self.rolls_left > 0:
            assert action.chosen_row == no_row
            for reroll_outcome, prob in roll_outcomes[action.rerolled].items():
                total_outcome = State.total_dice(action.held, reroll_outcome)
                yield (State(total_outcome,self.remaining_rows, self.rolls_left-1, self.ptsNeededForBonus(), self.zeroedYahtzee()), prob)
        else:
            # If there are no rerolls left, the action must be to score a row
            assert action.chosen_row != no_row
            # Make sure the row selected for scoring is available
            assert self.remaining_rows[action.chosen_row] == 1
            still_remaining = State.get_leftovers_after_playing(self.remaining_rows,action.chosen_row)
            basePoints, upperBonus, yahtzeeBonus = self.immediateReward(action)
            ptsStillNeededForBonus = 0
            if upperBonus == 0 and sum(still_remaining[0:6]) > 0:
                if State.isUpperSection(action.chosen_row):
                    ptsStillNeededForBonus = max(0,self.ptsNeededForBonus() - basePoints)
                else:
                    ptsStillNeededForBonus = self.ptsNeededForBonus()
            zeroingYahtzee = True if self.zeroed_yahtzee or (action.isScoringYahtzee() and basePoints == 0) else False
            #To do: compute ptsStillNeededForBonus
            yield (State(none_held, still_remaining, max_rolls_allowed,ptsStillNeededForBonus, zeroingYahtzee),1)
            
    def apply(self, action):
        if self.rolls_left > 0:
            assert action.chosen_row == no_row
            reroll_outcome = randomRoll(action.rerolled)
            total_outcome = State.total_dice(action.held, reroll_outcome)
            return (State(total_outcome,self.remaining_rows, self.rolls_left-1, self.ptsNeededForBonus(), self.zeroedYahtzee()), 0)
        else:
            # If there are no rerolls left, the action must be to score a row
            assert action.chosen_row != no_row
            # Make sure the row selected for scoring is available
            assert self.remaining_rows[action.chosen_row] == 1
            still_remaining = State.get_leftovers_after_playing(self.remaining_rows,action.chosen_row)
            basePoints, upperBonus, yahtzeeBonus = self.immediateReward(action)
            ptsStillNeededForBonus = 0
            if upperBonus == 0 and sum(still_remaining[0:6]) > 0:
                if State.isUpperSection(action.chosen_row):
                    ptsStillNeededForBonus = max(0,self.ptsNeededForBonus() - basePoints)
                else:
                    ptsStillNeededForBonus = self.ptsNeededForBonus()
            zeroingYahtzee = True if self.zeroed_yahtzee or (action.isScoringYahtzee() and basePoints == 0) else False
            return (State(none_held, still_remaining, max_rolls_allowed,ptsStillNeededForBonus, zeroingYahtzee),basePoints+upperBonus+yahtzeeBonus)
        
            

    def immediateReward(self, action):
        if action.chosen_row == no_row:
            return (0, 0, 0)
        else:
            assert self.remaining_rows[action.chosen_row] == 1
            return State.score_for(self.dice,action.chosen_row, self.remaining_rows, self.pts_needed_for_bonus, self.zeroed_yahtzee)

    def score_for(roll,t, slotsUsed, ptsNeededForBonus, zeroedYahtzee):
        upperBonus = 0
        yahtzeeBonus = 0
        switcher = {
            0:State.ones,
            1:State.twos,
            2:State.threes,
            3:State.fours,
            4:State.fives,
            5:State.sixes,
            6:State.three_of_a_kind,
            7:State.four_of_a_kind,
            8:State.full_house,
            9:State.small_straight,
            10:State.large_straight,
            11:State.yahtzee,
            12:State.chance
        }
        basePoints = switcher[t](roll)
        if ptsNeededForBonus > 0 and basePoints >= ptsNeededForBonus and State.isUpperSection(t):
            upperBonus = bonusAmount
        if State.five_of_a_kind(roll):
            if t != 11: #Yahtzee slot
                if slotsUsed[11] == 0: #Yahtzee slot used
                    #Joker rules
                    if t == 8: #Full house
                        basePoints = 25
                    elif t == 9: #Small straight
                        basePoints = 30
                    elif t == 10: #Large straight
                        basePoints = 40
                if not zeroedYahtzee:
                    yahtzeeBonus = 100
            #else: 
                # This is a legal (but foolish) play where the user as rolled a Yahtzee but isn't using it to maximum benefit
        return (basePoints, upperBonus, yahtzeeBonus)
        

    def getNoRows():
        return tuple([0]*max_turns)

    def total_dice(held, rerolled):
        #print("Held",held,"Rerolled",rerolled)
        total =  tuple(map(sum,zip(held,rerolled)))
        #print("Total ",total)
        return total
    
    def five_of_a_kind(t):
        return max(t) == 5 and sum(t) == max(t)

    def yahtzee(t):
        assert(len(t) == 6)
        if State.five_of_a_kind(t):
            return 50
        return 0

    def large_straight(t): # If I have no more than 1 of anything, and if I have either a 1 or a 6 but not both
        if sum(t) == 5 and max(t) == 1 and (t[0]+t[5]==1):
            return 40
        return 0

    def has1(t):
        return t[0] > 0
    def has2(t):
        return t[1] > 0
    def has3(t):
        return t[2] > 0
    def has4(t):
        return t[3] > 0
    def has5(t):
        return t[4] > 0
    def has6(t):
        return t[5] > 0

    def small_straight(t):
        if not State.has3(t) or not State.has4(t):
            return 0
        if (State.has2(t) and State.has5(t)) or (State.has1(t) and State.has2(t)) or (State.has5(t) and State.has6(t)):
            return 30
        return 0

    def prod(factors):
        return(reduce(operator.mul, factors, 1))

    def chance(t):
        #return sum(map(prod(zip(t,(1,2,3,4,5,6)))))
        return sum(p*q for p,q in zip(t,(1,2,3,4,5,6)))

    def three_of_a_kind(t):
        if max(t) < 3:
            return 0
        return State.chance(t)

    def four_of_a_kind(t):
        if max(t) < 4:
            return 0
        return State.chance(t)

    def full_house(t):
        if 2 in t and 3 in t:
            return 25
        return 0

    def ones(t):
        return t[0]
    def twos(t):
        return 2*t[1]
    def threes(t):
        return 3*t[2]
    def fours(t):
        return 4*t[3]
    def fives(t):
        return 5*t[4]
    def sixes(t):
        return 6*t[5]

    def scores(t):
        return (State.ones(t),State.twos(t),State.threes(t),State.fours(t),State.fives(t),State.sixes(t),State.three_of_a_kind(t),State.four_of_a_kind(t),State.full_house(t),State.small_straight(t),State.large_straight(t),State.yahtzee(t),State.chance(t))

    def isUpperSection(slotNo):
        return slotNo < 6 # Upper Section is slots 0-5
    # Helpers

    def get_leftovers_after_playing(remaining_rows,used):
        temp_list = list(remaining_rows)
        return tuple(temp_list[:used]+[temp_list[used]-1]+temp_list[used+1:])
    
# def finalState():
#     finalState = State(none_held,tuple([0]*max_turns),3)
#     return finalState
    
def startState():
    startState = State(none_held,tuple([1]*max_turns),3,63,False)
    return startState
    
