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
    max_index = yahtzee_state.max_rolls_allowed
    for turnsRemaining in range(0,2):
        t1 = time.perf_counter(), time.process_time()
        known_values = [{} for _ in range(yahtzee_state.max_rolls_allowed+1)]
        known_values[max_index] = stateManager.read("pickle","pickled/states",turnsRemaining-1,max_index) # Only need he starting points for next fewer slots remaining
        #known_values = stateManager.get(turnsRemaining-1,3) # The only "known values" for this iteration are those computed on the previous iteration
        for turnsUsedTuple, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            computeAllStateValuesForUsedSlots(known_values, turnsUsedTuple)
            break

        for rollsRemaining in (0,1,2,3):
            stateManager.categorize(known_values[rollsRemaining])
            stateManager.write("text","output/states",turnsRemaining,rollsRemaining)
            stateManager.write("pickle","pickled/states",turnsRemaining,rollsRemaining)
        t2 = time.perf_counter(), time.process_time()
        print(f" {turnsRemaining} Real time: {t2[0] - t1[0]:.2f} seconds")
        print(f" {turnsRemaining} CPU time: {t2[1] - t1[1]:.2f} seconds")


def computeAllStateValuesForUsedSlots(known_values, turnsUsedTuple):
    try:
        zeroedYahtzeeOptions = (True, False) if turnsUsedTuple[yahtzee_action.yahtzeeSlot] == 0 else (True,)
        #t1 = time.perf_counter(), time.process_time()
        # currit = 1
        for zeroedYahtzeeOption in zeroedYahtzeeOptions:
            for ptsNeededForBonus, isPossible in enumerate(yzi.getBonusPtsPossibilities(yahtzee_state.AbstractState.upperOnly(turnsUsedTuple))):
                # if currit > maxits:
                #     return
                if not isPossible:
                    continue
                if sum(turnsUsedTuple) > 0:
                    for rollsRemaining in (0,1,2):
                        for possibleRoll in roll_outcomes[5]:
                            s = yahtzee_state.makeState(possibleRoll,turnsUsedTuple,rollsRemaining, ptsNeededForBonus, zeroedYahtzeeOption)
                            state_evaluator.StateEvaluator.computeStateValue(s, known_values)
                s = yahtzee_state.makeState(yahtzee_state.none_held,turnsUsedTuple,3, ptsNeededForBonus, zeroedYahtzeeOption)
                print(s,flush=True)
                state_evaluator.StateEvaluator.computeStateValue(s, known_values)
    except Exception as e:
        print(f"Exception in {e}")
        raise
            # currit += 1
    #t2 = time.perf_counter(), time.process_time()
    #print(f"    Real time: {t2[0] - t1[0]:.2f} seconds")
    #print(f"    CPU time: {t2[1] - t1[1]:.2f} seconds")

def buildWorkloads(itemsPerBlock, blocksPerWave, supplyIterable):
    totalWorkload = []
    currentWave = []
    currentBlock = []
    for turnsUsedTuple, _ in supplyIterable:
        currentBlock.append(turnsUsedTuple)
        
        #Check if current block is full
        if len(currentBlock) == itemsPerBlock:
            # Add the current block to the current Wave
            currentWave.append(currentBlock)
            
            if len(currentWave) == blocksPerWave:
                totalWorkload.append(currentWave)
                # Start a new wave 
                currentWave = []
            # Start a new block
            currentBlock = []
    if currentBlock:
        currentWave.append(currentBlock)
        while len(currentWave) < blocksPerWave:
            currentWave.append([])
    
    if currentWave:
        totalWorkload.append(currentWave)
    
    return totalWorkload
            

def parallelizeComputeStateValues(stateManager, workerCnt):
    max_index = yahtzee_state.max_rolls_allowed
    for turnsRemaining in range(0,14):
        print("TurnsRemaining",turnsRemaining)
        t1 = time.perf_counter(), time.process_time()
        knownValues = [{} for _ in range(yahtzee_state.max_rolls_allowed+1)]
        knownValues[max_index] = stateManager.read("pickle","parallelpickled/states",turnsRemaining-1,max_index) # Only need he starting points for next fewer slots remaining
        #knownValues = stateManager.get(turnsRemaining-1,3) # The only "known values" for this iteration are those computed on the previous iteration
        #assert knownValues[max] != None
        maxItemsPerBatch = 50
        allWorkerAssignments = buildWorkloads(maxItemsPerBatch, workerCnt, yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining))
        print (len(allWorkerAssignments))
        # workerAssignments = [[] for _ in range(workerCnt)]
        # itemCnt = 0
        # for turnsUsedTuple, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
        #     if itemCnt * maxItemsPerBatch
        #     workerAssignments[itemCnt % workerCnt].append(turnsUsedTuple)
        #     itemCnt += 1
        ##########args =  [(assignment,knownValues,workerId) for workerId, assignment in enumerate(workerAssignments)]   
        # with concurrent.futures.ProcessPoolExecutor() as executor:
        #     try:
        #         #partial will unpack the tuple of arguments the gets passed in so that computeSubsetStateValues ses two distinct args
        #         results = list(executor.map(computeSubsetStateValuesWrapper,args))
        #         print("Have results", flush=True)
        #         i = 0
        #         for result in results:
        #             for rollsRemaining in (0,1,2,3):
        #                 print(f"Before categorize {i} {rollsRemaining}", flush=True)
        #                 stateManager.categorize(result[rollsRemaining])
        #                 print(f"After categorize {i} {rollsRemaining}", flush=True)
        #             i += 1
        #         i = 0
        #         for rollsRemaining in (0,1,2,3):
        #             print(f"Writing {i} {rollsRemaining}",flush=True)
        #             stateManager.write("pickle","parallelpickled/states",turnsRemaining,rollsRemaining)
        #             print(f"Writing more {i} {rollsRemaining}",flush=True)
        #             stateManager.write("text","parallel/states",turnsRemaining,rollsRemaining)
        #             print(f"Written {i} {rollsRemaining}",flush=True)
        #             i += 1
        #     except Exception as e:
        #         print(f"Exception during parallel execution: {e}")
 
    
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

def computeSubsetStateValues(turnsUsedTuples, knownValues, workerId=None):
    slotsUsed = sum(turnsUsedTuples[0]) if len(turnsUsedTuples) > 0 else 0
    file_path = f"procs/process{slotsUsed}_{workerId}.txt"
    with open(file_path,"w") as file:
        try:
            print("Kicking off computeSubset",file=file,flush=True)
            for turnsUsedTuple in turnsUsedTuples:
                computeAllStateValuesForUsedSlots(knownValues, turnsUsedTuple) # Last value returned should include all the previous updates
            #Make a copy for output purposes
            print("Finished computeSubsetStateValues; compiling copy of results",flush=True,file=file)
            result = [{} for _ in range(len(knownValues))]
            for i in range(len(knownValues)):
                for k, v in knownValues[i].items():
                    result[i][k] = v
            print("Finished compiling result; returning",flush=True,file=file)
            return result
        except Exception as e:
            print(f"Error: {e}",file=file,flush=True)

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
    #computeAllStateValues(sm)
    parallelizeComputeStateValues(sm,8)
    #sm.writeAll("pickle","parallelpickled/states")
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('ncalls')
    stats.print_stats()
    print(yahtzee_state.callCnt)
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
    