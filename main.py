import concurrent.futures
import itertools

import unittest
#import jsonpickle
import msgpack
import json
import yahtzee_iterators as yzi
import yahtzee_state
import state_evaluator 




# def getStateValue(state):
#     if state in state_values:
#         return (state_values[state], None)
#     else:
#         max_value = -1000
#         best_action = None
#         for action in legal_actions(state):
#             #print ("    Considering action: ", action)
#             immediate_reward = immediateReward(action,state)
#             expected_future_value = 0
#             total_prob = 0
#             for (next_state, prob) in stateTransitionsFrom(action, state):
#                 total_prob += prob
#                 # if not next_state in state_values:
#                 #     print("Not in there",next_state)
#                 if not next_state in state_values:
#                     print(state)
#                     print(action)
#                     print(next_state)
#                 assert next_state in state_values
#                 #print("                 ",prob, next_state, "Val: ",state_values[next_state])
#                 expected_future_value += prob * state_values[next_state]
#                 total_value = immediate_reward + expected_future_value
#                 if total_value > max_value:
#                     max_value = total_value
#                     best_action = action
#             #print("Action %s TV: %2f" % (action, total_value))
#         #print("In ",state," value is ",max_value," by doing ",best_action)
#         state_values[state] = max_value
#         return (max_value, best_action)
#         #return(1,None)






# return a tuple that is the same as remaining_rows but with remaining_rows[used] reduced by 1


# Utility method to add an item
# def add_to(remaining_rows, row_to_add):
#     assert row_to_add >= 0
#     assert row_to_add < len(remaining_rows)
#     temp_list = list(remaining_rows)
#     temp_list[row_to_add] = 1
#     return tuple(temp_list)

# def valueOf(row_choice, final_roll, remaining_rows):
#   assert(remaining_rows[row_choice] == 1)
#   new_remaining_rows = get_leftovers_after_playing(remaining_rows,row_choice)
#   assert(new_remaining_rows in state_values)
#   score_now = score_for(final_roll, row_choice)

#   score_later = state_values(new_remaining_rows)
#   return score_now + score_later
  
# def computeOneRowNoRoll():
#     noRows = getNoRows()
#     for row in range(len(noRows)):
#         oneRow = add_to(noRows,row)
#         for outcome in roll_outcomes[all_dice]:
#             state = State(outcome,oneRow,0)
#             (value, bestAction) = getStateValue(state)


#print("COMPUTING ONE ROLL LEFT")
# def computeOneRowOneRoll():
#     noRows = getNoRows()
#     for row in range(len(noRows)):
#         oneRow = add_to(noRows,row)
#         print(oneRow)
#         for outcome in roll_outcomes[all_dice]:
#              state = State(outcome,oneRow,1)
#              (value, bestAction) = getStateValue(state)
#              print("State: ",state, "Value: ", value, "Action: ",bestAction)
  
roll_outcomes = yzi.getRollOutcomes()
def computeAllStateValues(known_values):
    for turnsRemaining in range(1,2):
        for turnsUsedTuple, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            for rollsRemaining in (0,1,2):
                for possibleRoll in roll_outcomes[5]:
                    s = yahtzee_state.State(possibleRoll,turnsUsedTuple,rollsRemaining)
                    state_evaluator.StateEvaluator.computeStateValue(s, known_values)
            s = yahtzee_state.State(yahtzee_state.none_held,turnsUsedTuple,3)
            print(s)
            state_evaluator.StateEvaluator.computeStateValue(s, known_values)
                      

# jsonstr = jsonpickle.encode(state_values, unpicklable=True, keys=True)
# with open("sv0R.txt",'w') as ofile:
#     ofile.write(jsonstr)

# with open("sv0R.txt",'r') as ifile:
#     jsonstr = ifile.readlines()[0]
# #print(jsonstr)


# unpickled = jsonpickle.decode(jsonstr,keys=True)
# for svk, svv in unpickled.items():
#     print(svk,svv)

# def computeOneRow():
#     for rolls_remaining in range(3):
#         print("ROLLS REMAINING %i" % (rolls_remaining))
#         noRows = getNoRows()
#         for row in range(len(noRows)):
#             oneRow = add_to(noRows,row)
#             print(oneRow)
#             for outcome in roll_outcomes[all_dice]:
#                  state = State(outcome,oneRow,rolls_remaining)
#                  (value, bestAction) = getStateValue(state)
#                  #print("State: ",state, "Value: ", value, "Action: ",bestAction)
#computeOneRow()
        
            

# Compute probabilities of all possible outcomes when rolling 0, 1, 2, ..., len(roll_outcomes) dice


#computeOneRowOneRoll()
state_values = {}
finalState = yahtzee_state.State(yahtzee_state.none_held,tuple([0]*yahtzee_state.max_turns),3)
state_values[finalState] = (0, None)
# semifinalState = State((1,1,1,1,1,0),tuple([1]*13),2)
# state_values[semifinalState] = 4

#computeOneRowNoRoll()
#computeOneRow()
for k, v in state_values.items():
   if v[0] > 0 and k.remaining_rows[1] == 1:
        print("Computed",k,v)
print(len(state_values))
print(len(roll_outcomes))
print(len(roll_outcomes[5]))


#print(roll_outcomes)

#Serialization of rolled_outcomes
# Serialization with custom encoding
with open('data.msgpack', 'wb') as file:
    for item in roll_outcomes:
        file.write(msgpack.packb(item))
        
# Deserialization with custom decoding
with open('data.msgpack', 'rb') as file:
    loaded_data = [item for item in msgpack.Unpacker(file, strict_map_key=False, use_list=False)]
    # packed_data = file.read()
    # loaded_data = msgpack.unpackb(packed_data, object_hook=decode_dict, raw=False, strict_map_key=False, use_list=False)


def writeStateValues(state_values, filepath):
    with open(filepath, 'wb') as file:
        for k, v in state_values.items():
            file.write(msgpack.packb((k.dice,k.remaining_rows,k.rolls_left,v)))



def readStateValues(filepath):
    reloaded_states = {}        
    with open(filepath, 'rb') as file:
    #reloaded_states = { State(item[0], item[1], item[2]) : item[3] for item in msgpack.Unpacker(file, strict_map_key=False, use_list=False) }
        for item in msgpack.Unpacker(file, strict_map_key=False, use_list=False):
            s = yahtzee_state.State(item[0],item[1],item[2])
            reloaded_states[s] = item[3]
    return reloaded_states

def printStateValues(state_values):
    for k, v in state_values.items():
        if k.openSlotCount() == 1 and k.rolls_left <= 3:
            print(k,v)

# print("Read states from file")
# reloaded_states = readStateValues('states_values.msgpack')
# state_values = reloaded_states

# Comparing dictionaries of states values
# for k, v in state_values.items():
#     if k not in reloaded_states:
#         print("Missing",k)
#     elif reloaded_states[k] != v:
#         print("Bad Value")
#     #print(k)

computeAllStateValues(state_values)
printStateValues(state_values)
        
# print (len(reloaded_states))
# for k, v in reloaded_states.items():
#     if k.openSlotCount() == 1 and k.rolls_left == 3:
#         print(k,v)      

# writeStateValues(state_values, 'states_values_refactored.msgpack')
