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
import os
import multiprocessing

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


def computeAllStateValuesForUsedSlots(known_values, turnsUsedTuple, file=None):
    try:
        zeroedYahtzeeOptions = (True, False) if turnsUsedTuple[yahtzee_action.yahtzeeSlot] == 0 else (False,)
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
                print(s,flush=True,file=file)
                state_evaluator.StateEvaluator.computeStateValue(s, known_values)
    except Exception as e:
        print(f"Exception in {e}")
        raise
            # currit += 1
    #t2 = time.perf_counter(), time.process_time()
    #print(f"    Real time: {t2[0] - t1[0]:.2f} seconds")
    #print(f"    CPU time: {t2[1] - t1[1]:.2f} seconds")
    
def worker_process(work_queue, result_queue, known_values, qLock, worker_id):
    maxItems = 50
    try:
        while True:
            item = work_queue.get()
            with qLock:
                while result_queue.qsize() >= maxItems:
                    print(f"Waiting with lock in {worker_id} at size {result_queue.qsize()}",flush=True)
                    time.sleep(0.1)
                if item is None:
                    print(f"Putting in sentinel in worker process {worker_id}")
                    result_queue.put(item)
                    break  # Exit the loop when there is no more work
                else:
                    result = computeSubsetStateValues([item], known_values, worker_id)
                    assert len(result) == 4
                    print ("Result",flush=True)
                    result_queue.put(result)
    except Exception as e:
        print(f"Worker {worker_id} encountered an exception {e}",flush=True)
    print(f"Breaking out of {worker_id}",flush=True)
    
# def consumer_process(result_queue, stateManager, workerCnt):
#     with open("consumer.txt","w") as file:
#         finishedWorkerCnt = 0
#         try:
#             while True:
#                 result = result_queue.get()
#                 if result == None:
#                     finishedWorkerCnt += 1
#                     print("Pulled sentinel in consume",flush=True,file=file)
#                     if finishedWorkerCnt == workerCnt:
#                         print("All workers finished",flush=True, file=file)
#                         return
#                     else:
#                         continue
#                 assert len(result) == 4
#                 print("Processing result",flush=True,file=file)
#                 for rollsRemaining in (0,1,2,3):
#                     stateManager.categorize(result[rollsRemaining])
#         except Exception as e:
#             print(f"Exception in consumer process {e}")
#     sync_queue.put(0)    

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
    
def isIn(assignment, knownValues):
    for k, v in knownValues.items():
        if k.getRemainingRows() == assignment:
            print("Found",flush=True)
            return True
    return False
def matchInputOutput(assignments, result):
    print(f"CalledInputOutput {len(assignments)}, {len(result)}",flush=True)
    for assignment in assignments:
        for rollsRemaining in (0,1,2):
            if not isIn(assignment,result[rollsRemaining]):
                print(f"{assignment} not found in result")
                return False
    return True
def parallelizeComputeMultiprocessing(stateManager, workerCnt):
    max_index = yahtzee_state.max_rolls_allowed
    num_workers = workerCnt  # Set the number of worker processes
    for turnsRemaining in range(3,14):
        work_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        qLock = multiprocessing.Lock()
        # Start worker processes
        workers = []
        knownValues = [{} for _ in range(yahtzee_state.max_rolls_allowed+1)]
        knownValues[max_index] = stateManager.read("pickle","parallelpickled/states",turnsRemaining-1,max_index) # Only need he starting points for next fewer slots remaining

        for i in range(1, num_workers + 1):
            worker = multiprocessing.Process(target=worker_process, args=(work_queue, result_queue, knownValues, qLock, i))
            worker.start()
            workers.append(worker)
        # consumer = multiprocessing.Process(target=consumer_process, args=(result_queue, stateManager, workerCnt, sync_queue))
        # consumer.start()
        
        
        # Dispatch work items to worker processes
        for item, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            print(f"Putting {item}",flush=True)
            work_queue.put(item)
        print("Sending nones",flush=True)

        for _ in range(num_workers):
            work_queue.put(None)
            
        with open("consumer.txt","w") as file:
            finishedWorkerCnt = 0
            try:
                while True:
                    result = result_queue.get()
                    if result == None:
                        finishedWorkerCnt += 1
                        print("Pulled sentinel in consume",flush=True,file=file)
                        if finishedWorkerCnt == workerCnt:
                            print("All workers finished",flush=True, file=file)
                            break
                        else:
                            continue
                    assert len(result) == 4
                    print(f"Processing result {result_queue.qsize()}",flush=True,file=file)
                    for rollsRemaining in (0,1,2,3):
                        stateManager.categorize(result[rollsRemaining])
            except Exception as e:
                print(f"Exception in consumer process {e}")


        print("Waiting for sync signal",flush=True)
        # syncer = sync_queue.get()
        print("Got sync signal",flush=True)
        # Signal workers to exit by sending None for each worker
        # Wait for all worker processes to finish
        for i, worker in enumerate(workers):
            print("Joining",flush=True)
            worker.join()
            print(f"Joined {i}",flush=True)
        for worker in workers:
            worker.terminate()
        # consumer.join()
        # consumer.terminate()
        print("Done with joining",flush=True)
        # Collect results from the result queue
        results = []
        for rollsRemaining in (0,1,2,3):
            try:
                print(f"Writing {i} {rollsRemaining}",flush=True)
                stateManager.write("pickle","parallelpickled/states",turnsRemaining,rollsRemaining)
                print(f"Writing more {i} {rollsRemaining}",flush=True)
                stateManager.write("text","parallel/states",turnsRemaining,rollsRemaining)
                print(f"Written {i} {rollsRemaining}",flush=True)
                i += 1
            except Exception as e:
                print(f"Exception during writeouts: {e}")
                raise



def parallelizeComputeStateValues(stateManager, workerCnt):
    max_index = yahtzee_state.max_rolls_allowed
    for turnsRemaining in range(1,14):
        print("TurnsRemaining",turnsRemaining)
        t1 = time.perf_counter(), time.process_time()
        #knownValues = stateManager.get(turnsRemaining-1,3) # The only "known values" for this iteration are those computed on the previous iteration
        #assert knownValues[max] != None
        maxItemsPerBatch = 1 
        allWorkerAssignments = buildWorkloads(maxItemsPerBatch, workerCnt, yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining))
        print (len(allWorkerAssignments))
        for i, wave in enumerate(allWorkerAssignments):
            print(f"Wave {i} for round {turnsRemaining}")
            for assignment in wave:
                print(assignment)
        for workSet in allWorkerAssignments:
            knownValues = [{} for _ in range(yahtzee_state.max_rolls_allowed+1)]
            knownValues[max_index] = stateManager.read("pickle","parallelpickled/states",turnsRemaining-1,max_index) # Only need he starting points for next fewer slots remaining
            args =  [(assignment,knownValues,workerId) for workerId, assignment in enumerate(workSet)]   
            with concurrent.futures.ProcessPoolExecutor() as executor:
                try:
                    #partial will unpack the tuple of arguments the gets passed in so that computeSubsetStateValues ses two distinct args
                    results = list(executor.map(computeSubsetStateValuesWrapper,args))
                    print("Have results", flush=True)
                    i = 0
                    for j, result in enumerate(results):
                        print("Checking input",flush=True)
                        if not matchInputOutput(args[j][0],result):
                            raise Exception("Did not find all assignments in results")
                        for rollsRemaining in (0,1,2,3):
                            print(f"Before categorize {i} {rollsRemaining}", flush=True)
                            stateManager.categorize(result[rollsRemaining])
                            print(f"After categorize {i} {rollsRemaining}", flush=True)
                        i += 1
                except Exception as e:
                    print(f"Exception during parallel execution: {e}")
                    raise
        i = 0
        for rollsRemaining in (0,1,2,3):
            try:
                print(f"Writing {i} {rollsRemaining}",flush=True)
                stateManager.write("pickle","parallelpickled/states",turnsRemaining,rollsRemaining)
                print(f"Writing more {i} {rollsRemaining}",flush=True)
                stateManager.write("text","parallel/states",turnsRemaining,rollsRemaining)
                print(f"Written {i} {rollsRemaining}",flush=True)
                i += 1
            except Exception as e:
                print(f"Exception during writeouts: {e}")
                raise
                

def computeSubsetStateValues(turnsUsedTuples, knownValues, workerId=None):
    slotsUsed = sum(turnsUsedTuples[0]) if len(turnsUsedTuples) > 0 else 0
    file_path = f"procs/process{slotsUsed}_{workerId}.txt"
    with open(file_path,"a") as file:
        try:
            print("Kicking off computeSubset",file=file,flush=True)
            for turnsUsedTuple in turnsUsedTuples:
                computeAllStateValuesForUsedSlots(knownValues, turnsUsedTuple, file) # Last value returned should include all the previous updates
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
            raise

def computeSubsetStateValuesWrapper(args):
    try:
        result = computeSubsetStateValues(*args)
        return result
    except Exception as e:
        print(f"Error in compute SubsetStateValuesWrapper: {e}")
        raise


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
            
import os


def purge(directory_path):
    # Check if the directory exists
    if os.path.exists(directory_path):
        # Get the list of files in the directory
        files = os.listdir(directory_path)

        # Iterate over each file and delete it
        for file in files:
            file_path = os.path.join(directory_path, file)
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

    else:
        print(f"The directory {directory_path} does not exist.")


if __name__ == '__main__':
    purge("procs")
    purge("parallel")
    purge("output")
    sm = StateManager()
    profiler = cProfile.Profile()
    profiler.enable()
    #computeAllStateValues(sm)
    #parallelizeComputeStateValues(sm,8)
    parallelizeComputeMultiprocessing(sm,7)
    #sm.writeAll("pickle","parallelpickled/states")
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('ncalls')
    stats.print_stats()
    #print(yahtzee_state.callCnt)

    #######################################################
    # Play a game
    #gm = GameManager()
    #gm.playRandom()
    #######################################################

    