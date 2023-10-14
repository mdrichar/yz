import itertools
from functools import reduce
import operator
import yahtzee_iterators as yzi
import random
import yahtzee_action
from abc import ABC, abstractmethod
none_held = (0,0,0,0,0,0)
no_row = None
all_dice = 5
max_rolls_allowed = 3
max_turns=13
bonusThreshold = 63
bonusAmount = 35
actionTbl = yahtzee_action.seedLegalActionTable()
callCnt = 0

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

class AbstractState(ABC):
    @abstractmethod
    def openSlotCount(self):
        pass
    @abstractmethod
    def isOpen(self,slot):
        pass
    @abstractmethod
    def getDice(self):
        pass
    @abstractmethod
    def getRemainingRows(self):
        pass
    @abstractmethod
    def getRollsLeft(self):
        pass
    @abstractmethod
    def getZeroedYahtzee(self):
        pass
    @abstractmethod
    def getPtsNeededForBonus(self):
        pass
    def isFinalState(self):
        return self.openSlotCount() == 0
    
    def legal_actions(self):
        rollsLeft = self.getRollsLeft()
        if rollsLeft == 3:
            yield yahtzee_action.makeAction(none_held,all_dice,no_row)
        elif rollsLeft == 0: # Can't reroll, must choose a row to apply score
            for r in range(max_turns):
                if self.isOpen(r):
                    yield yahtzee_action.makeAction(none_held,0,r)
        else: # 1 or 2 rerolls left
            actions = actionTbl[self.getDice()]
            for action in actions:
                yield action
            # for action in itertools.product(
            # range(dice[0] + 1), range(dice[1] + 1), range(dice[2] + 1),range(dice[3] + 1),
            # range(dice[4] + 1), range(dice[5] + 1)):
            #     yield yahtzee_action.makeAction(action,5-sum(action),no_row)



    def stateTransitionsFrom(self, action):
        rollsLeft = self.getRollsLeft()
        remainingRows = self.getRemainingRows()
        held = action.getHeld()
        chosenRow = action.getChosenRow()
        if rollsLeft > 0:
            assert chosenRow == no_row
            # for reroll_outcome, prob in roll_outcomes[action.getRerolled()].items():
            #     total_outcome = AbstractState.total_dice(held, reroll_outcome)
            #     yield (makeState(total_outcome,remainingRows, rollsLeft-1, self.getPtsNeededForBonus(), self.getZeroedYahtzee()), prob)
            myActionResults = actionResults[action]
            assert len(myActionResults) > 0
            for total_outcome, prob in myActionResults:
                yield (makeState(total_outcome,remainingRows, rollsLeft-1, self.getPtsNeededForBonus(), self.getZeroedYahtzee()), prob)
        else:
            # If there are no rerolls left, the action must be to score a row
            assert chosenRow != no_row
            # Make sure the row selected for scoring is available
            assert remainingRows[chosenRow] == 1
            still_remaining = AbstractState.get_leftovers_after_playing(remainingRows,chosenRow)
            basePoints, upperBonus, yahtzeeBonus = self.immediateReward(action)
            ptsNeededForBonus = self.getPtsNeededForBonus() #pts needed in current state; cache to avoid multiple calls
            ptsStillNeededForBonus = 0 # pts still needed in next state
            if upperBonus == 0 and sum(still_remaining[0:6]) > 0:
                if AbstractState.isUpperSection(action.getChosenRow()):
                    ptsStillNeededForBonus = max(0,ptsNeededForBonus - basePoints)
                else:
                    ptsStillNeededForBonus = ptsNeededForBonus
            zeroingYahtzee = True if self.getZeroedYahtzee() or (action.isScoringYahtzee() and basePoints == 0) else False
            #To do: compute ptsStillNeededForBonus
            yield (makeState(none_held, still_remaining, max_rolls_allowed,ptsStillNeededForBonus, zeroingYahtzee),1)
            
    def apply(self, action):
        rollsLeft = self.getRollsLeft()
        remainingRows = self.getRemainingRows()
        if rollsLeft > 0:
            assert action.getChosenRow() == no_row
            reroll_outcome = randomRoll(action.getRerolled())
            total_outcome = AbstractState.total_dice(action.getHeld(), reroll_outcome)
            return (makeState(total_outcome,remainingRows, rollsLeft-1, self.getPtsNeededForBonus(), self.getZeroedYahtzee()), 0)
        else:
            # If there are no rerolls left, the action must be to score a row
            assert action.getChosenRow() != no_row
            # Make sure the row selected for scoring is available
            assert remainingRows[action.getChosenRow()] == 1
            still_remaining = AbstractState.get_leftovers_after_playing(self.remaining_rows,action.getChosenRow())
            basePoints, upperBonus, yahtzeeBonus = self.immediateReward(action)
            ptsStillNeededForBonus = 0
            if upperBonus == 0 and sum(still_remaining[0:6]) > 0:
                if AbstractState.isUpperSection(action.getChosenRow()):
                    ptsStillNeededForBonus = max(0,self.getPtsNeededForBonus() - basePoints)
                else:
                    ptsStillNeededForBonus = self.getPtsNeededForBonus()
            zeroingYahtzee = True if self.getZeroedYahtzee() or (action.isScoringYahtzee() and basePoints == 0) else False
            return (makeState(none_held, still_remaining, max_rolls_allowed,ptsStillNeededForBonus, zeroingYahtzee),basePoints+upperBonus+yahtzeeBonus)
        
            

    def immediateReward(self, action):
        remainingRows = self.getRemainingRows()
        chosenRow = action.getChosenRow()
        if chosenRow == no_row:
            return (0, 0, 0)
        else:
            assert remainingRows[chosenRow] == 1
            return AbstractState.score_for(self.getDice(),chosenRow, remainingRows, self.getPtsNeededForBonus(), self.getZeroedYahtzee())

    # @abstractmethod
    # def isFinalState(self):
    #     pass
    # @abstractmethod
    # def legal_actions(self):
    #     pass
    # @abstractmethod
    # def stateTransitionsFrom(self, action):
    #     pass
    # @abstractmethod
    # def apply(self, action):
    #     pass
    # @abstractmethod
    # def immediateReward(self, action):
    #     pass
################################################ Class-level functions

    def score_for(roll,t, slotsUsed, ptsNeededForBonus, zeroedYahtzee):
        upperBonus = 0
        yahtzeeBonus = 0
        # switcher = {
        #     0:AbstractState.ones,
        #     1:AbstractState.twos,
        #     2:AbstractState.threes,
        #     3:AbstractState.fours,
        #     4:AbstractState.fives,
        #     5:AbstractState.sixes,
        #     6:AbstractState.three_of_a_kind,
        #     7:AbstractState.four_of_a_kind,
        #     8:AbstractState.full_house,
        #     9:AbstractState.small_straight,
        #     10:AbstractState.large_straight,
        #     11:AbstractState.yahtzee,
        #     12:AbstractState.chance
        # }
        # basePoints = switcher[t](roll)
        basePoints = basePointsTable[roll][t]
        if ptsNeededForBonus > 0 and basePoints >= ptsNeededForBonus and AbstractState.isUpperSection(t):
            upperBonus = bonusAmount
        if AbstractState.five_of_a_kind(roll):
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
    
    def getBasePoints(rollOutcomes):
        switcher = {
            0:AbstractState.ones,
            1:AbstractState.twos,
            2:AbstractState.threes,
            3:AbstractState.fours,
            4:AbstractState.fives,
            5:AbstractState.sixes,
            6:AbstractState.three_of_a_kind,
            7:AbstractState.four_of_a_kind,
            8:AbstractState.full_house,
            9:AbstractState.small_straight,
            10:AbstractState.large_straight,
            11:AbstractState.yahtzee,
            12:AbstractState.chance
        }
        result = {}
        for rollOutcome, prob in rollOutcomes.items():
            result[rollOutcome] = [switcher[t](rollOutcome) for t in range(max_turns)]  
        return result

    def getNoRows():
        return tuple([0]*max_turns)

    def total_dice(held, rerolled):
        #total =  tuple(map(sum,zip(held,rerolled)))
        #print("Total ",total)
        #return total
        #return tuple(starmap(add,zip(held,rerolled))) # Better than tuple(map(sum,zip... but not as good as all spelled out
        return (held[0]+rerolled[0],held[1]+rerolled[1],held[2]+rerolled[2],held[3]+rerolled[3],held[4]+rerolled[4],held[5]+rerolled[5])
    
    def five_of_a_kind(t):
        maxt = max(t)
        return maxt == 5 and sum(t) == maxt

    def yahtzee(t):
        assert(len(t) == 6)
        if AbstractState.five_of_a_kind(t):
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
        if not AbstractState.has3(t) or not AbstractState.has4(t):
            return 0
        if (AbstractState.has2(t) and AbstractState.has5(t)) or (AbstractState.has1(t) and AbstractState.has2(t)) or (AbstractState.has5(t) and AbstractState.has6(t)):
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
        return AbstractState.chance(t)

    def four_of_a_kind(t):
        if max(t) < 4:
            return 0
        return AbstractState.chance(t)

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
        return (AbstractState.ones(t),AbstractState.twos(t),AbstractState.threes(t),AbstractState.fours(t),AbstractState.fives(t),AbstractState.sixes(t),AbstractState.three_of_a_kind(t),AbstractState.four_of_a_kind(t),AbstractState.full_house(t),AbstractState.small_straight(t),AbstractState.large_straight(t),AbstractState.yahtzee(t),AbstractState.chance(t))

    def isUpperSection(slotNo):
        return slotNo < 6 # Upper Section is slots 0-5
    # Helpers
    
        
    def upperOnly(t):
        return t[0:6]

    def get_leftovers_after_playing(remaining_rows,used):
        temp_list = list(remaining_rows)
        return tuple(temp_list[:used]+[temp_list[used]-1]+temp_list[used+1:])
#####################################################################################################################################################################    
class CondensedState(AbstractState):
    def __init__(self,dice,remaining_rows, rolls_left, pts_needed_for_bonus, zeroed_yahtzee, full_state=None):
        # dice is tuple of six items with counts for how many 1s, 2s, 3s, ..., 6s 3bits each = 18 bits (0-17)
        # r = remaining_rows = 1 bit for each of 13 slots (18-30); 1 means slot is available, 0 means already scored there
        # rolls_left = how many more shakes left on this turn (0-3), two bits (31-32)
        # pts_needed_for_bonus is 0-63 integer; how many points more to secure the upper section bonus (0 if unattainable or already achieved): 6 bits (33-38)
        # zeroed_bonus is 1 if the yahtzee slot was score with a 0, meaning not eligible for Yahtzee bonus (39)
        if full_state:
            self.bit_field = full_state
        else:
            r =remaining_rows
            self.bit_field = (zeroed_yahtzee <<39) | (pts_needed_for_bonus << 33) | (rolls_left << 31) | (
                r[12] << 30 | r[11] << 29 | r[10] << 28 | r[9] << 27 | r[8] << 26 | r[7] << 25 | r[6] << 24 | r[5] << 23 | r[4] << 22 | r[3] << 21 | r[2] << 20 | r[1] << 19 | r[0] << 18
            ) | (
                dice[5] << 15 | dice[4] << 12 | dice[3] << 9 | dice[2] << 6 | dice[1] << 3 | dice[0]
            )
        
    def __str__(self):
        return f"{self.getDice()} {self.openSlotCount():02d}:{self.getRemainingRows()} {self.getRollsLeft()} {self.getPtsNeededForBonus():02d} {self.getZeroedYahtzee()}" 
    def __repr__(self):
        return self.__str__() 
    def __eq__(self,other):
        return self.bit_field == other.bit_field
    def __hash__(self):
        return hash(self.bit_field)
 
    def openSlotCount(self):
        bf = self.bit_field
        return ( ((bf>>18) &0x01) + ((bf>>19) &0x01) + ((bf>>20)&0x01) + ((bf>>21)&0x01) + ((bf>>22)&0x01) + ((bf>>23)&0x01) + ((bf>>24)&0x01) + ((bf>>25)&0x01) + 
                ((bf>>26)&0x01) + ((bf>>27)&0x01) +((bf>>28)&0x01) +((bf>>29)&0x01) + ((bf>>30) & 0x01))
    def isOpen(self,slot):
        return (self.bit_field >> (slot+18)) & 0x01      
    def getDice(self):
        bf = self.bit_field
        return (bf & 0x07,  (bf>>3) &0x07, (bf>>6) &0x07, (bf>>9)&0x07, (bf>>12)&0x07, (bf>>15)&0x07)   
    
    def getRemainingRows(self):
        bf = self.bit_field
        return ((bf>>18) &0x01, (bf>>19) &0x01, (bf>>20)&0x01, (bf>>21)&0x01, (bf>>22)&0x01, (bf>>23)&0x01, (bf>>24)&0x01, (bf>>25)&0x01, 
                (bf>>26)&0x01, (bf>>27)&0x01,(bf>>28)&0x01,(bf>>29)&0x01,(bf>>30) & 0x01)
    def getRollsLeft(self):
        bf = self.bit_field
        return (bf>>31)&0x3
    def getPtsNeededForBonus(self):
        bf = self.bit_field
        return (bf>>33)&0x3F
    def getZeroedYahtzee(self):
        bf = self.bit_field
        return (bf>>39 )&0x3F
    def getFullState(self):
        return self.bit_field
    def setFullState(self, bit_field):
        self.bit_field = bit_field
    def stateTransitionsFrom(self, action):
        rollsLeft = self.getRollsLeft()
        remainingRows = self.getRemainingRows()
        held = action.getHeld()
        chosenRow = action.getChosenRow()
        if rollsLeft > 0:
            assert chosenRow == no_row
            # for reroll_outcome, prob in roll_outcomes[action.getRerolled()].items():
            #     total_outcome = AbstractState.total_dice(held, reroll_outcome)
            #     yield (makeState(total_outcome,remainingRows, rollsLeft-1, self.getPtsNeededForBonus(), self.getZeroedYahtzee()), prob)
            base_inards = self.getFullState()
            common_next_inards = (base_inards & 0b1111111001111111111111000000000000000000) | ((rollsLeft-1) << 31)
            for total_outcome_bits, prob in actionResultsBits[action]:
                #total_outcome = fromBits(total_outcome_bits) 
                next_state_bits = common_next_inards | total_outcome_bits
                newState = CondensedState(None,None,None,None,None,full_state=next_state_bits)
                #newState = (makeState(total_outcome,remainingRows, rollsLeft-1, self.getPtsNeededForBonus(), self.getZeroedYahtzee()), prob)
                yield (newState, prob)
        else:
            # If there are no rerolls left, the action must be to score a row
            assert chosenRow != no_row
            # Make sure the row selected for scoring is available
            assert remainingRows[chosenRow] == 1
            still_remaining = AbstractState.get_leftovers_after_playing(remainingRows,chosenRow)
            basePoints, upperBonus, yahtzeeBonus = self.immediateReward(action)
            ptsNeededForBonus = self.getPtsNeededForBonus() #pts needed in current state; cache to avoid multiple calls
            ptsStillNeededForBonus = 0 # pts still needed in next state
            if upperBonus == 0 and sum(still_remaining[0:6]) > 0:
                if AbstractState.isUpperSection(action.getChosenRow()):
                    ptsStillNeededForBonus = max(0,ptsNeededForBonus - basePoints)
                else:
                    ptsStillNeededForBonus = ptsNeededForBonus
            zeroingYahtzee = True if self.getZeroedYahtzee() or (action.isScoringYahtzee() and basePoints == 0) else False
            #To do: compute ptsStillNeededForBonus
            yield (makeState(none_held, still_remaining, max_rolls_allowed,ptsStillNeededForBonus, zeroingYahtzee),1)

#####################################################################################################################################################################    
        
class StandardState(AbstractState):
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
    def isOpen(self,slot):
        return self.remaining_rows[slot]
    def getDice(self):
        return self.dice
    def getRemainingRows(self):
        return self.remaining_rows
    def getRollsLeft(self):
        return self.rolls_left
    def getZeroedYahtzee(self):
        return self.zeroed_yahtzee
    def getPtsNeededForBonus(self):
        return self.pts_needed_for_bonus
    
def toBits(dice): # Return dice counts (up to 8 of each face) as a bit-field
    return dice[5] << 15 | dice[4] << 12 | dice[3] << 9 | dice[2] << 6 | dice[1] << 3 | dice[0]
def fromBits(bf): 
    return (bf & 0x07,  (bf>>3) &0x07, (bf>>6) &0x07, (bf>>9)&0x07, (bf>>12)&0x07, (bf>>15)&0x07)
# For each possible rolling action from (0,0,0,0,0,0)+5 to (5,0,0,0,0,0)+0 compute and cache all the possible outcomes
def computeActionResultMaps():
    actionResults = {}
    actionResultsBits = {}
    for candidateHold in itertools.product(
        range(all_dice+1),
        range(all_dice+1),
        range(all_dice+1),
        range(all_dice+1),
        range(all_dice+1),
        range(all_dice+1)
    ):
        holdCnt = sum(candidateHold) # total dice kept
        results = []
        resultsBits = []
        if holdCnt <= all_dice:
            rerolledCnt = all_dice - holdCnt # rerolled
            action = yahtzee_action.makeAction(held=candidateHold,rerolled=rerolledCnt)
            #print(action)
            for reroll_outcome, prob in roll_outcomes[rerolledCnt].items():
                total_outcome = AbstractState.total_dice(candidateHold, reroll_outcome)
                #print(f"   {total_outcome} : {prob:.3f}")
                results.append((total_outcome,prob))
                resultsBits.append((toBits(total_outcome),prob))
            actionResults[action] = results
            actionResultsBits[action] = resultsBits
    return (actionResults, actionResultsBits)
actionResults, actionResultsBits = computeActionResultMaps()


    
def startState():
    startState = makeState(none_held,tuple([1]*max_turns),3,63,False)
    return startState

def makeState(dice,remaining_rows, rolls_left, pts_needed_for_bonus, zeroed_yahtzee):
    #return StandardState(dice,remaining_rows, rolls_left, pts_needed_for_bonus, zeroed_yahtzee)
    return CondensedState(dice,remaining_rows, rolls_left, pts_needed_for_bonus, zeroed_yahtzee)

basePointsTable = AbstractState.getBasePoints(roll_outcomes[all_dice])
#print(len(basePointsTable))

    
if __name__ == '__main__':  
    # Creating an Action with chosen_row
    myState = makeState((1,0,2,1,0,1),(1,0,1,0,1,0,1,0,1,0,1,0,1),3,63,0)
    # print(myState)
    myState = makeState((0,0,0,0,0,5),(0,1,0,1,0,1,0,1,0,1,0,1,0),2,1,1)
    # print(myState)
    #computeActionResultMaps()
