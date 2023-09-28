import itertools
from functools import reduce
import operator
import yahtzee_iterators as yzi

none_held = (0,0,0,0,0,0)
no_row = -1
all_dice = 5
max_rolls_allowed = 3
max_turns=13
#for i in itertools.product(range(3),range(3)):
#    print(i)
roll_outcomes = yzi.getRollOutcomes()

class Action:
    def __init__(self,held,rerolled,chosen_row):
        #print("Action: ", held,"Rerolled:",rerolled)
        self.held = held
        self.rerolled = rerolled
        self.chosen_row = chosen_row
    def __str__(self):
        if self.chosen_row > 0:
            return "Selected Row " + str(self.chosen_row)
        elif self.rerolled == all_dice:
            return "Roll All"
        else:
            return "Keep " + str(self.held) + " Reroll" + str(self.rerolled)

class State:
    def __init__(self,dice,remaining_rows, rolls_left):
        self.dice = dice
        self.remaining_rows = remaining_rows
        self.rolls_left = rolls_left
    def __str__(self):
        return "     Dice " + str(self.dice) + str(self.remaining_rows) + str(self.rolls_left)
    def __eq__(self,other):
        return (self.dice == other.dice and self.remaining_rows == other.remaining_rows and self.rolls_left == other.rolls_left)
    def __hash__(self):
        return hash((self.dice,self.remaining_rows,self.rolls_left))
    def openSlotCount(self):
        return sum(self.remaining_rows)


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
            total_outcome = total_dice(action.held, reroll_outcome)
            yield (State(total_outcome,self.remaining_rows, self.rolls_left-1), prob)
    else:
        # If there are no rerolls left, the action must be to score a row
        assert action.chosen_row != no_row
        # Make sure the row selected for scoring is available
        assert self.remaining_rows[action.chosen_row] == 1
        still_remaining = get_leftovers_after_playing(self.remaining_rows,action.chosen_row)
        yield (State(none_held, still_remaining, max_rolls_allowed),1)

def immediateReward(self, action):
    if action.chosen_row == no_row:
        return 0
    else:
        assert self.remaining_rows[action.chosen_row] == 1
        return score_for(self.dice,action.chosen_row)

def score_for(roll,t):
  switcher = {
      0:ones,
      1:twos,
      2:threes,
      3:fours,
      4:fives,
      5:sixes,
      6:three_of_a_kind,
      7:four_of_a_kind,
      8:full_house,
      9:small_straight,
      10:large_straight,
      11:yahtzee,
      12:chance
  }
  return switcher[t](roll)

def getNoRows():
    return tuple([0]*max_turns)

def total_dice(held, rerolled):
    #print("Held",held,"Rerolled",rerolled)
    total =  tuple(map(sum,zip(held,rerolled)))
    #print("Total ",total)
    return total

def yahtzee(t):
    assert(len(t) == 6)
    if sum(t) == max(t) and max(t) == 5:
        return 50
    return 0

def large_straight(t):
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
    if not has3(t) or not has4(t):
        return 0
    if (has2(t) and has5(t)) or (has1(t) and has2(t)) or (has5(t) and has6(t)):
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
    return chance(t)

def four_of_a_kind(t):
    if max(t) < 4:
        return 0
    return chance(t)

def full_house(t):
    if yahtzee(t) or (2 in t and 3 in t):
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
    return (ones(t),twos(t),threes(t),fours(t),fives(t),sixes(t),three_of_a_kind(t),four_of_a_kind(t),full_house(t),small_straight(t),large_straight(t),yahtzee(t),chance(t))

# Helpers

def get_leftovers_after_playing(remaining_rows,used):
    temp_list = list(remaining_rows)
    return tuple(temp_list[:used]+[temp_list[used]-1]+temp_list[used+1:])