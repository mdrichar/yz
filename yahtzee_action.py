import itertools
import yahtzee_iterators as yzi
from abc import ABC, abstractmethod
slot_name = ["Ones","Twos","Threes","Fours","Fives","Sixes","Three of a kind","Four of a kind","Full House","Small Straight","Large Straight","Yahtzee","Chance"]
yahtzeeSlot = 11
all_dice = 5

class AbstractAction(ABC):
    @abstractmethod
    def getChosenRow(self):
        pass
    @abstractmethod
    def getRerolled(self):
        pass
    @abstractmethod
    def getHeld(self):
        pass
    @abstractmethod
    def isScoringYahtzee(self):
        pass

###################################################################################################################################################
class StandardAction(AbstractAction):
    def __init__(self,held,rerolled,chosen_row):
        #print("Action: ", held,"Rerolled:",rerolled)
        self.held = held
        self.rerolled = rerolled
        self.chosen_row = chosen_row
    def __eq__(self,other):
        return self.held == other.held and self.rerolled == other.rerolled and self.chosen_row == other.chosen_row
    def __hash__(self):
        return hash((self.held,self.rerolled,self.chosen_row))
    def __str__(self):
        if self.chosen_row and self.chosen_row  >= 0:
            return "Score for " + slot_name[self.chosen_row]
        elif self.rerolled == all_dice:
            return "Roll All"
        else:
            return "Keep " + str(self.held) + " Reroll " + str(self.rerolled)
    def getHeld(self):
        return self.held
    def getRerolled(self):
        return self.rerolled
    def getChosenRow(self):
        return self.chosen_row
    def __repr__(self):
        return self.__str__()
    def isScoringYahtzee(self):
        return self.chosen_row == yahtzeeSlot

###################################################################################################################################################
    

class CondensedAction(AbstractAction):
    def __init__(self, held=None, rerolled=None, chosen_row=None):
        self.bit_field = 0

        if chosen_row is not None:
            # Set the type bit to 0
            self.bit_field = chosen_row
        elif rerolled is not None and held is not None:
            # Set the type bit to 1
            self.bit_field |= (1 << 22)

            # Set rerolled bits (3 bits)
            self.bit_field |= (rerolled & 0x07) << 18

            # Set held bits (6 elements, 3 bits each)
            for i in range(6):
                self.bit_field |= (held[i] & 0x07) << (i * 3)
    def __eq__(self,other):
        return self.bit_field == other.bit_field
    def __hash__(self):
        return hash(self.bit_field)
        
    def getChosenRow(self):
        if (self.bit_field >> 22) & 1 == 0:
            # Type bit is 0, so it's a chosen_row type
            return self.bit_field & 0x0F
        else:
            return None

    def getRerolled(self):
        if (self.bit_field >> 22) == 1:
            # Type bit is 1, so it's a rerolled type
            return (self.bit_field >> 18) & 0x07
        else:
            return None

    def getHeld(self):
        if (self.bit_field >> 22) == 1:
            # Type bit is 1, so it's a rerolled type
            #held = []
            #for i in range(6):
            #    held.append((self.bit_field >> (i * 3)) & 0x07)
            bf = self.bit_field
            return (bf & 0x07, (bf>>3) &0x07, (bf>>6) &0x07, (bf>>9)&0x07, (bf>>12)&0x07, (bf>>15)&0x07)
            #return tuple(held)
        else:
            return None
    
    def isScoringYahtzee(self):
        #return self.bit_field == (1 << 22) & yahtzeeSlot
        return self.getChosenRow() == yahtzeeSlot
        
    def __str__(self):
        chosenRow = self.getChosenRow()
        if chosenRow != None:
            return f"Score {slot_name[chosenRow]}"
        else:
            return f"{self.getHeld()}+{self.getRerolled()}"
        
    def __repr__(self):
        return self.__str__()

def makeAction(held=None, rerolled=None, chosen_row=None):
    return CondensedAction(held, rerolled, chosen_row)
    #return StandardAction(held, rerolled, chosen_row)
# Example usage:



def legalActions(dice):
    result = []
    for action in itertools.product(
    range(dice[0] + 1), range(dice[1] + 1), range(dice[2] + 1),range(dice[3] + 1),
    range(dice[4] + 1), range(dice[5] + 1)):
        result.append(makeAction(action,5-sum(action),None))
    return result
        
def getLegalActionLookupTable(roll_outcomes):
    legalActionsTbl = {}
    for outcome, _ in roll_outcomes.items():
        legalActionsTbl[outcome] = legalActions(outcome)
    return legalActionsTbl

def seedLegalActionTable():
    rollOutcomes = yzi.getRollOutcomes()
    legalActionsTbl = getLegalActionLookupTable(rollOutcomes[5])
    return legalActionsTbl
    

if __name__ == '__main__':  
    # Creating an Action with chosen_row
    action_chosen_row = makeAction(chosen_row=7)
    print("Chosen Row:", action_chosen_row.getChosenRow())
    print("Rerolled:", action_chosen_row.getRerolled())
    print("Held:", action_chosen_row.getHeld())

    # Creating an Action with rerolled and held
    action_rerolled_held = makeAction(held=(1, 2, 3, 4, 5, 0),rerolled=2)
    print("Chosen Row:", action_rerolled_held.getChosenRow())
    print("Rerolled:", action_rerolled_held.getRerolled())
    print("Held:", action_rerolled_held.getHeld())
    
    legalActionsTbl = seedLegalActionTable()
    # for possibleRoll, legalActions in legalActionsTbl.items():
    #      print(possibleRoll)
    #      print(len(legalActions))
    #     for legalAction in legalActions:
    #         print(f"   {legalAction}")