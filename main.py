import concurrent.futures
import itertools

import unittest
#import jsonpickle
import pickle
import msgpack
import json
import yahtzee_iterators as yzi
import yahtzee_state
import state_evaluator 
import cProfile, pstats
from yahtzee_state_manager import StateManager
from game_manager import GameManager

roll_outcomes = yzi.getRollOutcomes()
def computeAllStateValues(known_values):
    for turnsRemaining in range(0,2):
        for turnsUsedTuple, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            zeroedYahtzeeOptions = (True, False) if turnsUsedTuple[yahtzee_state.yahtzeeSlot] == 0 else (True,)
            for zeroedYahtzeeOption in zeroedYahtzeeOptions:
                for ptsNeededForBonus, isPossible in enumerate(yzi.getBonusPtsPossibilities(yahtzee_state.State.upperOnly(turnsUsedTuple))):
                    if not isPossible:
                        continue
                    if sum(turnsUsedTuple) > 0:
                        for rollsRemaining in (0,1,2):
                            for possibleRoll in roll_outcomes[5]:
                                s = yahtzee_state.State(possibleRoll,turnsUsedTuple,rollsRemaining, ptsNeededForBonus, zeroedYahtzeeOption)
                                state_evaluator.StateEvaluator.computeStateValue(s, known_values)
                    s = yahtzee_state.State(yahtzee_state.none_held,turnsUsedTuple,3, ptsNeededForBonus, zeroedYahtzeeOption)
                    print(s)
                    state_evaluator.StateEvaluator.computeStateValue(s, known_values)


def parallelizeComputeStateValues(knownValues, workerCnt):
    for turnsRemaining in range(1,2):
        workerAssignments = [[] for _ in range(workerCnt)]
        itemCnt = 0
        for turnsUsedTuple, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            workerAssignments[itemCnt % workerCnt].append(turnsUsedTuple)
            itemCnt += 1
        args =  [(assignment,knownValues) for assignment in workerAssignments]   
        with concurrent.futures.ProcessPoolExecutor() as executor:
            #partial will unpack the tuple of arguments the gets passed in so that computeSubsetStateValues ses two distinct args
            results = list(executor.map(computeSubsetStateValuesWrapper,args))
        for result in results:
            knownValues.update(result)    
 
    
def computeSubsetStateValues(turnsUsedTuples, knownValues):
    for turnsUsedTuple in turnsUsedTuples:
        for rollsRemaining in (0,1,2):
            for possibleRoll in roll_outcomes[5]:
                s = yahtzee_state.State(possibleRoll,turnsUsedTuple,rollsRemaining)
                state_evaluator.StateEvaluator.computeStateValue(s, knownValues)
        s = yahtzee_state.State(yahtzee_state.none_held,turnsUsedTuple,3)
        #print(s)
        state_evaluator.StateEvaluator.computeStateValue(s, knownValues)                     
    return knownValues

def computeSubsetStateValuesWrapper(args):
    return computeSubsetStateValues(*args)


#computeOneRowOneRoll()
state_values = {}
# finalState = yahtzee_state.finalState()
# state_values[finalState] = (0, None)
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
            print(f"{k}={v[0]:.2f},{v[1]}")


computeAllStateValues(state_values)
profiler = cProfile.Profile()
profiler.enable()
#parallelizeComputeStateValues(state_values,16)
# profiler.disable()
# stats = pstats.Stats(profiler).sort_stats('ncalls')
# #stats.print_stats()
# print(len(state_values))
# sm = StateManager()
# sm.categorize(state_values)
# StateManager.dumpStateValues(state_values,'states.pickle')
# #sm.write("text","output/states",1,3)
# sm.writeAll("text","output/states")
# sm.writeAll("pickle","pickled/states")
# print(len(sm.get(1,3)))
# #printStateValues(state_values)


#######################################################
# Play a game
gm = GameManager()
gm.playRandom()
#######################################################
        
# print (len(reloaded_states))
# for k, v in reloaded_states.items():
#     if k.openSlotCount() == 1 and k.rolls_left == 3:
#         print(k,v)      

# writeStateValues(state_values, 'states_values_refactored.msgpack')
