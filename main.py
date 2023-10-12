import concurrent.futures
import itertools
import yahtzee_action
import time
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
def computeAllStateValues(stateManager):
    for turnsRemaining in range(0,2):
        t1 = time.perf_counter(), time.process_time()
        known_values = stateManager.read("pickle","pickled/states",turnsRemaining-1,3) # Only need he starting points for next fewer slots remaining
        #known_values = stateManager.get(turnsRemaining-1,3) # The only "known values" for this iteration are those computed on the previous iteration
        for turnsUsedTuple, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            updated_values = computeAllStateValuesForUsedSlots(known_values, turnsUsedTuple)
            break
        stateManager.categorize(updated_values)
        stateManager.writeAll("text","output/states")
        for rollsRemaining in (0,1,2,3):
            stateManager.write("pickle","pickled/states",turnsRemaining,rollsRemaining)
        t2 = time.perf_counter(), time.process_time()
        print(f" {turnsRemaining} Real time: {t2[0] - t1[0]:.2f} seconds")
        print(f" {turnsRemaining} CPU time: {t2[1] - t1[1]:.2f} seconds")


def computeAllStateValuesForUsedSlots(known_values, turnsUsedTuple):
    zeroedYahtzeeOptions = (True, False) if turnsUsedTuple[yahtzee_action.yahtzeeSlot] == 0 else (True,)
    #t1 = time.perf_counter(), time.process_time()
    maxits = 10
    currit = 1
    for zeroedYahtzeeOption in zeroedYahtzeeOptions:
        for ptsNeededForBonus, isPossible in enumerate(yzi.getBonusPtsPossibilities(yahtzee_state.State.upperOnly(turnsUsedTuple))):
            if currit > maxits:
                return known_values
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
            currit += 1
    t2 = time.perf_counter(), time.process_time()
    #print(f"    Real time: {t2[0] - t1[0]:.2f} seconds")
    #print(f"    CPU time: {t2[1] - t1[1]:.2f} seconds")
    return known_values


def parallelizeComputeStateValues(stateManager, workerCnt):
    for turnsRemaining in range(0,2):
        print("TurnsRemaining",turnsRemaining)
        #knownValues = stateManager.get(turnsRemaining-1,3) # The only "known values" for this iteration are those computed on the previous iteration
        knownValues = stateManager.read("pickle","parallelpickled/states",turnsRemaining-1,3) # Only need he starting points for next fewer slots remaining
        assert knownValues != None
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
            stateManager.categorize(result)
        stateManager.writeAll("text","parallel/states")
        for rollsRemaining in (0,1,2,3):
            stateManager.write("pickle","parallelpickled/states",turnsRemaining,rollsRemaining)
 
    
# def computeSubsetStateValues(turnsUsedTuples, knownValues):
#     for turnsUsedTuple in turnsUsedTuples:
#         for rollsRemaining in (0,1,2):
#             for possibleRoll in roll_outcomes[5]:
#                 s = yahtzee_state.State(possibleRoll,turnsUsedTuple,rollsRemaining)
#                 state_evaluator.StateEvaluator.computeStateValue(s, knownValues)
#         s = yahtzee_state.State(yahtzee_state.none_held,turnsUsedTuple,3)
#         #print(s)
#         state_evaluator.StateEvaluator.computeStateValue(s, knownValues)                     
#     return knownValues

def computeSubsetStateValues(turnsUsedTuples, knownValues):
    print("Kicking off computeSubset")
    for turnsUsedTuple in turnsUsedTuples:
        knownValues = computeAllStateValuesForUsedSlots(knownValues, turnsUsedTuple) # Last value returned should include all the previous updates
    return knownValues

def computeSubsetStateValuesWrapper(args):
    return computeSubsetStateValues(*args)


#computeOneRowOneRoll()

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

if __name__ == '__main__':
    sm = StateManager()
    profiler = cProfile.Profile()
    profiler.enable()
    computeAllStateValues(sm)
    #parallelizeComputeStateValues(sm,8)
    #sm.writeAll("pickle","parallelpickled/states")
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('ncalls')
    stats.print_stats()
    # print(len(state_values))
    # sm.categorize(state_values)
    # StateManager.dumpStateValues(state_values,'states.pickle')
    # #sm.write("text","output/states",1,3)
    # sm.writeAll("text","output/states")
    # sm.writeAll("pickle","pickled/states")
    # print(len(sm.get(1,3)))
    # #printStateValues(state_values)


    #######################################################
    # Play a game
    #gm = GameManager()
    #gm.playRandom()
    #######################################################
            
    # print (len(reloaded_states))
    # for k, v in reloaded_states.items():
    #     if k.openSlotCount() == 1 and k.rolls_left == 3:
    #         print(k,v)      

    # writeStateValues(state_values, 'states_values_refactored.msgpack')
    