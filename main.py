from functools import reduce
import itertools
import operator
import unittest
#import jsonpickle
import msgpack
import json

none_held = (0,0,0,0,0,0)
no_row = -1
all_dice = 5
max_rolls_allowed = 3
#for i in itertools.product(range(3),range(3)):
#    print(i)

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


def legal_actions(state):
    if state.rolls_left == 3:
        yield Action(none_held,all_dice,no_row)
    elif state.rolls_left == 0: # Can't reroll, must choose a row to apply score
        for r in range(len(state.remaining_rows)):
            if state.remaining_rows[r] > 0:
                yield Action(none_held,0,r)
    else: # 1 or 2 rerolls left
        dice = state.dice
        for action in itertools.product(
          range(dice[0] + 1), range(dice[1] + 1), range(dice[2] + 1),range(dice[3] + 1),
          range(dice[4] + 1), range(dice[5] + 1)):
            yield Action(action,5-sum(action),no_row)

def total_dice(held, rerolled):
    #print("Held",held,"Rerolled",rerolled)
    total =  tuple(map(sum,zip(held,rerolled)))
    #print("Total ",total)
    return total

def stateTransitionsFrom(action, state):
    if state.rolls_left > 0:
        assert action.chosen_row == no_row
        for reroll_outcome, prob in roll_outcomes[action.rerolled].items():
            total_outcome = total_dice(action.held, reroll_outcome)
            yield (State(total_outcome,state.remaining_rows, state.rolls_left-1), prob)
    else:
        # If there are no rerolls left, the action must be to score a row
        assert action.chosen_row != no_row
        # Make sure the row selected for scoring is available
        assert state.remaining_rows[action.chosen_row] == 1
        still_remaining = get_leftovers_after_playing(state.remaining_rows,action.chosen_row)
        yield (State(none_held, still_remaining, max_rolls_allowed),1)

def immediateReward(action, state):
    if action.chosen_row == no_row:
        return 0
    else:
        assert state.remaining_rows[action.chosen_row] == 1
        return score_for(state.dice,action.chosen_row)

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


def getNoRows():
    return tuple([0]*13)

def getStateValue(state):
    if state in state_values:
        return (state_values[state], None)
    else:
        max_value = -1000
        best_action = None
        for action in legal_actions(state):
            print ("    Considering action: ", action)
            immediate_reward = immediateReward(action,state)
            expected_future_value = 0
            total_prob = 0
            for (next_state, prob) in stateTransitionsFrom(action, state):
                total_prob += prob
                if not next_state in state_values:
                    print("Not in there",next_state)
                assert next_state in state_values
                print("                 ",prob, next_state, "Val: ",state_values[next_state])
                expected_future_value += prob * state_values[next_state]
                total_value = immediate_reward + expected_future_value
                if total_value > max_value:
                    max_value = total_value
                    best_action = action
            print("Action %s TV: %2f" % (action, total_value))
        print("In ",state," value is ",max_value," by doing ",best_action)
        state_values[state] = max_value
        return (max_value, best_action)
        #return(1,None)




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

# return a tuple that is the same as remaining_rows but with remaining_rows[used] reduced by 1
def get_leftovers_after_playing(remaining_rows,used):
    temp_list = list(remaining_rows)
    return tuple(temp_list[:used]+[temp_list[used]-1]+temp_list[used+1:])

# Utility method to add an item
def add_to(remaining_rows, row_to_add):
    assert row_to_add >= 0
    assert row_to_add < len(remaining_rows)
    temp_list = list(remaining_rows)
    temp_list[row_to_add] = 1
    return tuple(temp_list)

def valueOf(row_choice, final_roll, remaining_rows):
  assert(remaining_rows[row_choice] == 1)
  new_remaining_rows = get_leftovers_after_playing(remaining_rows,row_choice)
  assert(new_remaining_rows in state_values)
  score_now = score_for(final_roll, row_choice)

  score_later = state_values(new_remaining_rows)
  return score_now + score_later
  
def computeOneRowNoRoll():
    noRows = getNoRows()
    for row in range(len(noRows)):
        oneRow = add_to(noRows,row)
        for outcome in roll_outcomes[all_dice]:
            state = State(outcome,oneRow,0)
            (value, bestAction) = getStateValue(state)


#print("COMPUTING ONE ROLL LEFT")
def computeOneRowOneRoll():
    noRows = getNoRows()
    for row in range(len(noRows)):
        oneRow = add_to(noRows,row)
        print(oneRow)
        for outcome in roll_outcomes[all_dice]:
             state = State(outcome,oneRow,1)
             (value, bestAction) = getStateValue(state)
             print("State: ",state, "Value: ", value, "Action: ",bestAction)
             

# jsonstr = jsonpickle.encode(state_values, unpicklable=True, keys=True)
# with open("sv0R.txt",'w') as ofile:
#     ofile.write(jsonstr)

# with open("sv0R.txt",'r') as ifile:
#     jsonstr = ifile.readlines()[0]
# #print(jsonstr)


# unpickled = jsonpickle.decode(jsonstr,keys=True)
# for svk, svv in unpickled.items():
#     print(svk,svv)

def computeOneRow():
    for rolls_remaining in range(3):
        print("ROLLS REMAINING %i" % (rolls_remaining))
        noRows = getNoRows()
        for row in range(len(noRows)):
            oneRow = add_to(noRows,row)
            print(oneRow)
            for outcome in roll_outcomes[all_dice]:
                 state = State(outcome,oneRow,rolls_remaining)
                 (value, bestAction) = getStateValue(state)
                 #print("State: ",state, "Value: ", value, "Action: ",bestAction)
#computeOneRow()
        
            

# Compute probabilities of all possible outcomes when rolling 0, 1, 2, ..., len(roll_outcomes) dice

roll_outcomes = [{} for i in range(6)]
#roll_outcomes.append({})

# If I roll 0 dice, the probability of rolling 0 1s, 0 2s, 0 3s, 0 4s, 0 5s, and 0 6s is 1
roll_outcomes[0][(0,0,0,0,0,0)] = 1

base = [(1,0,0,0,0,0),(0,1,0,0,0,0),(0,0,1,0,0,0),(0,0,0,1,0,0),(0,0,0,0,1,0),(0,0,0,0,0,1)]

# First enumerate all the outcomes of rolling one die. (1,0,0,0,0,0) means rolling a 1, (0,0,1,0,0,0) means rolling a three.
# There are six outcomes from rolling one die. Now, when I go to figure out all the outcomes of rolling two dice, I can iterate
# over all the one die-outcomes, and for each of those, I can enumerate the six possibilities that result from adding a 1 or a 2
# ... or 6 to that one-die outcome. 

# Note that there could be some duplicates here. If my one-die outcome of rolling a 1 (1,0,0,0,0,0) and then I add the second die is a 3,
# that would be (1,0,1,0,0,0). But when I consider the one-die outcome of rolling a 3 (0,0,1,0,0,0) and I add the second die is a 1, that
# is also (1,0,1,0,0,0). Adding up the number of duplicates and dividing by the total (for each die count) gives the probability of that 
# outcome. So for two dice, 6*6 caeses will be enumerated. The probability of rolling a pair of ones (2,0,0,0,0,0) is 1/36, but the 
# probability of rolling a one and a three is 2/36=1/18, because the (1,0,1,0,0,0) will get generated twice.

for i in range(1,len(roll_outcomes)):
    #print("i:",i)
    for j in range(6):
        #zlist = [0] * 6
        #zlist[j] = 1
        #print(f"(i,j):({i},{j})")
        for key,val in roll_outcomes[i-1].items():
            #print("Key: ",key)
            #print("Base[j]: ", base[j])
            #print("Zip(key,base[j]): ",zip(key,base[j]))
            t = tuple(map(sum,zip(key,base[j])))
            #print("t",t)
            if t in roll_outcomes[i]:
                roll_outcomes[i][t] += val
            else:
                roll_outcomes[i][t] = val
roll_outcomes_sizes = [6**x for x in range(len(roll_outcomes))]
for i in range(all_dice+1):
    total_outcomes = roll_outcomes_sizes[i]
    for key in roll_outcomes[i]:
        roll_outcomes[i][key] = roll_outcomes[i][key] / total_outcomes

#computeOneRowOneRoll()
state_values = {}
finalState = State(none_held,tuple([0]*13),3)
semifinalState = State((1,1,1,1,1,0),tuple([1]*13),2)
state_values[finalState] = 0
state_values[semifinalState] = 4

#computeOneRowNoRoll()
for k, v in state_values.items():
   if v > 0 and k.remaining_rows[1] == 1:
        print("Computed",k,v)
print(len(state_values))
print(len(roll_outcomes))
print(len(roll_outcomes[5]))


#print(roll_outcomes)

# Serialization with custom encoding
with open('data.msgpack', 'wb') as file:
    for item in roll_outcomes:
        file.write(msgpack.packb(item))
        
# Deserialization with custom decoding
with open('data.msgpack', 'rb') as file:
    loaded_data = [item for item in msgpack.Unpacker(file, strict_map_key=False, use_list=False)]
    # packed_data = file.read()
    # loaded_data = msgpack.unpackb(packed_data, object_hook=decode_dict, raw=False, strict_map_key=False, use_list=False)


with open('states1.msgpack', 'wb') as file:
    for k, v in state_values.items():
        file.write(msgpack.packb((k.dice,k.remaining_rows,k.rolls_left,v)))
        
with open('states1.msgpack', 'rb') as file:
    #reloaded_states = { State(item[0], item[1], item[2]) : item[3] for item in msgpack.Unpacker(file, strict_map_key=False, use_list=False) }
    for item in msgpack.Unpacker(file, strict_map_key=False, use_list=False):
        s = State(item[0],item[1],item[2])
        print(s)

# for k, v in reloaded_states:
#     print(k,v)      

# print(loaded_data)
# Define a custom serialization function for State objects
# def state_encoder(obj):
#     print("State_encoder: ",type(obj))
#     if isinstance(obj, State):
#         return (obj.dice, obj.remaining_rows, obj.rolls_left)
#     raise TypeError("Object of type 'State' is not serializable")

# with open('states1.msgpack', 'wb') as file:
#     file.write(msgpack.packb(state_values, default=state_encoder))
# # Serialize the dictionary using msgpack with the custom encoder

# # Define a custom decoding function for State objects
# def state_decoder(obj):
#     if isinstance(obj, tuple) and len(obj) == 3:
#         print("Decoding State")
#         return State(obj[0], obj[1], obj[2])
#     else:
#         print("Fall back",obj)
#         print(type(obj))
#         print(len(obj))
    
#     return obj

# # Deserialize the binary data using msgpack with the custom decoder
# with open('states1.msgpack', 'rb') as f:
#     serialized_data = f.read()
#     loaded_values = msgpack.unpackb(serialized_data, object_hook=state_decoder, strict_map_key=False, use_list = False)


# Now 'your_dictionary' contains the deserialized data with State objects as keys and integers as values
# for k, v in loaded_values.items():
#    if v > 0 and k.remaining_rows[1] == 1:
#         print("Computed",k,v)
# print(len(loaded_values))
# print(loaded_values)
#print(len(roll_outcomes))
#print(len(roll_outcomes[5]))




# Define a custom encoding function for the dictionary
# def dict_encoder(obj):
#     print("Encoding obj",type(obj))

#     if isinstance(obj, dict):
#         return {"state_dict": [(key.__dict__, value) for key, value in obj.items()]}

# # Define a custom decoding function for the dictionary
# def dict_decoder(obj):
#     print(type(obj))
#     if "state_dict" in obj:
#         return {
#             State(*key_values): value
#             for key_values, value in obj["state_dict"]
#         }
#     return obj

# Create a dictionary with State objects as keys and integers as values


# Serialize the dictionary using msgpack with the custom encoder
#serialized_data = msgpack.packb(state_values, default=dict_encoder)

# Deserialize the dictionary using msgpack with the custom decoder
#deserialized_dict = msgpack.unpackb(serialized_data, object_hook=dict_decoder, strict_map_key=False)

# Now 'deserialized_dict' contains the deserialized dictionary with State objects as keys and integers as values
#print(deserialized_dict)
