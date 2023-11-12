import concurrent.futures
import itertools
import yahtzee_action
import time
import unittest
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
import logging
import psutil
import gc
import signal
import sys
import copy
import fnmatch

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set up file handler
log_file_path = 'output.log'
if os.path.exists(log_file_path):
    os.remove(log_file_path)
    
file_handler = logging.FileHandler(log_file_path)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

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
        #print(f" {turnsRemaining} Real time: {t2[0] - t1[0]:.2f} seconds")
        #print(f" {turnsRemaining} CPU time: {t2[1] - t1[1]:.2f} seconds")


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
                logger.info(s)
                state_evaluator.StateEvaluator.computeStateValue(s, known_values)
    except Exception as e:
        logger.error(f"Exception in {e}")
        raise
            # currit += 1
    #t2 = time.perf_counter(), time.process_time()
    #print(f"    Real time: {t2[0] - t1[0]:.2f} seconds")
    #print(f"    CPU time: {t2[1] - t1[1]:.2f} seconds")

def get_memory_usage(worker_id):
    process = psutil.Process()
    memory_info = process.memory_info()
    rss = memory_info.rss / (1024 * 1024)
    logger.info(f"{worker_id} Memory Usage: {rss:.2f} MB")
    if rss > 1000:
        gc.collect()
        
def signal_handler(signum, frame):
    print("Process received signal", signum)
    # Log information or perform cleanup before exiting
    sys.exit(1)
    
def worker_process(work_queue, result_queue, base_known_values, qLock, turnsRemaining, worker_id):
    signal.signal(signal.SIGTERM, signal_handler)
    os.makedirs(f"partst/{turnsRemaining}/{worker_id}")
    os.makedirs(f"parts/{turnsRemaining}/{worker_id}")
    maxItems = 8
    pulledItemCnt = 0
    sm = StateManager()
    partNumber = 0
    itemsPerWrite = 5
    known_values = copy.deepcopy(base_known_values)
    try:
        while True:
            logger.info(f"{turnsRemaining} Pulling an item from queue {worker_id}")
            get_memory_usage(worker_id)
            item = work_queue.get()
            #with qLock:
            while result_queue.qsize() >= maxItems:
                logger.debug(f"Waiting with lock in {worker_id} at size {result_queue.qsize()}")
                time.sleep(0.1)
            if item == None:
                logger.info(f"{turnsRemaining} Putting in sentinel in worker process {worker_id}")
                result_queue.put(item)
                #Write any remaining items out
                partNumber += 1
                for rollsRemaining in (0,1,2,3):
                        sm.write("pickle",f"parts/{turnsRemaining}/{worker_id}/P{partNumber}_states",turnsRemaining,rollsRemaining)
                        sm.write("text",f"partst/{turnsRemaining}/{worker_id}/P{partNumber}_states",turnsRemaining,rollsRemaining)

                break  # Exit the loop when there is no more work
            else:
                logger.info(f"{turnsRemaining} Pulled an item from queue {worker_id}: {item}")
                pulledItemCnt += 1
                result = computeSubsetStateValues([item], known_values, worker_id, sm)
                assert result == None
                logger.info(f"{turnsRemaining} Total items pulled so far by worker {worker_id} = {pulledItemCnt}")
                logger.info(f"Result {item}")
                #result_queue.put(result)
                #sm.categorize(result)
                if pulledItemCnt % itemsPerWrite == 0:
                    partNumber += 1
                    for rollsRemaining in (0,1,2,3):
                        sm.write("pickle",f"parts/{turnsRemaining}/{worker_id}/P{partNumber}_states",turnsRemaining,rollsRemaining)
                        sm.write("text",f"partst/{turnsRemaining}/{worker_id}/P{partNumber}_states",turnsRemaining,rollsRemaining)
                    sm = StateManager()
                    known_values = copy.deepcopy(base_known_values)
    except Exception as e:
        logger.error(f"Worker {worker_id} encountered an exception {e}")
    logger.info(f"Breaking out of {worker_id}")
    logger.info(f"Waiting at the end of {worker_id}")
    time.sleep(5)
    logger.info(f"Finished waiting at the end of {worker_id}")
    
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
            return True
    return False
def matchInputOutput(assignments, result):
    for assignment in assignments:
        for rollsRemaining in (0,1,2):
            if not isIn(assignment,result[rollsRemaining]):
                logger.error(f"{assignment} not found in result")
                return False
    return True
def parallelizeComputeMultiprocessing(stateManager, workerCnt):
    max_index = yahtzee_state.max_rolls_allowed
    num_workers = workerCnt  # Set the number of worker processes
    for turnsRemaining in range(1,14):
        os.makedirs(f"parts/{turnsRemaining}")
        os.makedirs(f"partst/{turnsRemaining}")
        work_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        qLock = multiprocessing.Lock()
        # Start worker processes
        workers = []
        knownValues = [{} for _ in range(yahtzee_state.max_rolls_allowed+1)]
        knownValues[max_index] = stateManager.read("pickle","parallelpickled/states",turnsRemaining-1,max_index) # Only need he starting points for next fewer slots remaining

        for i in range(1, num_workers + 1):
            worker = multiprocessing.Process(target=worker_process, args=(work_queue, result_queue, knownValues, qLock, turnsRemaining, i))
            worker.start()
            workers.append(worker)
        
        # Dispatch work items to worker processes
        workItemsPutCnt = 0
        for item, _ in yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining):
            logger.info(f"{turnsRemaining} Putting {item}")
            work_queue.put(item)
            workItemsPutCnt += 1
        logger.info(f"{turnsRemaining} Total Work Items Put {workItemsPutCnt}")
        logger.info(f"Sending nones {turnsRemaining}")

        for _ in range(num_workers):
            work_queue.put(None)
            
        with open("consumer.txt","w") as file:
            finishedWorkerCnt = 0
            try:
                while True:
                    result = result_queue.get()
                    assert result == None
                    if result == None:
                        finishedWorkerCnt += 1
                        logger.info(f"Pulled sentinel in consume: turnsRemaining {turnsRemaining} finishedWorkers {finishedWorkerCnt}")
                        if finishedWorkerCnt == workerCnt:
                            logger.info("All workers finished")
                            break
                        else:
                            continue
                    # assert len(result) == 4
                    # print(f"Processing result {result_queue.qsize()}",flush=True,file=file)
                    # for rollsRemaining in (0,1,2,3):
                    #     stateManager.categorize(result[rollsRemaining])
            except Exception as e:
                print(f"Exception in consumer process {e}")


        logger.info("Waiting for sync signal")
        # syncer = sync_queue.get()
        logger.info("Got sync signal")
        # Signal workers to exit by sending None for each worker
        # Wait for all worker processes to finish
        for i, worker in enumerate(workers):
            logger.info("Joining")
            worker.join()
            logger.info(f"Joined {i}")
        for worker in workers:
            worker.terminate()
        # consumer.join()
        # consumer.terminate()
        logger.info("Done with joining")
        #assert False
        for i in range(1,workerCnt + 1):
            for rollsRemaining in (0,1,2,3):
                directory = f"parts/{turnsRemaining}/{i}"
                for filename in os.listdir(directory):
                    logger.debug(f"Considering {filename}")
                    if fnmatch.fnmatch(filename, f"P*_states_{turnsRemaining}_{rollsRemaining}*"):
                        full_path = os.path.join(directory,filename)
                        logger.debug(f"Matched {filename}")
                        stateManager.readFull("pickle",full_path,turnsRemaining,rollsRemaining,mode='Append')   
                    else:
                        logger.debug(f"Rejected {filename}")
                        
        # Collect results from the result queue
        results = []
        for rollsRemaining in (0,1,2,3):
            try:
                logger.info(f"Writing {i} {rollsRemaining}")
                stateManager.write("pickle","parallelpickled/states",turnsRemaining,rollsRemaining)
                logger.info(f"Writing more {i} {rollsRemaining}")
                stateManager.write("text","parallel/states",turnsRemaining,rollsRemaining)
                logger.info(f"Written {i} {rollsRemaining}")
                i += 1
            except Exception as e:
                logger.info(f"Exception during writeouts: {e}")
                raise



def parallelizeComputeStateValues(stateManager, workerCnt):
    max_index = yahtzee_state.max_rolls_allowed
    for turnsRemaining in range(1,14):
        logger.debug("TurnsRemaining",turnsRemaining)
        t1 = time.perf_counter(), time.process_time()
        #knownValues = stateManager.get(turnsRemaining-1,3) # The only "known values" for this iteration are those computed on the previous iteration
        #assert knownValues[max] != None
        maxItemsPerBatch = 1 
        allWorkerAssignments = buildWorkloads(maxItemsPerBatch, workerCnt, yzi.allBinaryPermutationsFixedOnesCnt(yahtzee_state.max_turns,turnsRemaining))
        for i, wave in enumerate(allWorkerAssignments):
            logger.debug(f"Wave {i} for round {turnsRemaining}")
            for assignment in wave:
                logger.debug(assignment)
        for workSet in allWorkerAssignments:
            knownValues = [{} for _ in range(yahtzee_state.max_rolls_allowed+1)]
            knownValues[max_index] = stateManager.read("pickle","parallelpickled/states",turnsRemaining-1,max_index) # Only need he starting points for next fewer slots remaining
            args =  [(assignment,knownValues,workerId) for workerId, assignment in enumerate(workSet)]   
            with concurrent.futures.ProcessPoolExecutor() as executor:
                try:
                    #partial will unpack the tuple of arguments the gets passed in so that computeSubsetStateValues ses two distinct args
                    results = list(executor.map(computeSubsetStateValuesWrapper,args))
                    i = 0
                    for j, result in enumerate(results):
                        if not matchInputOutput(args[j][0],result):
                            raise Exception("Did not find all assignments in results")
                        for rollsRemaining in (0,1,2,3):
                            stateManager.categorize(result[rollsRemaining])
                        i += 1
                except Exception as e:
                    logger.error(f"Exception during parallel execution: {e}")
                    raise
        i = 0
        for rollsRemaining in (0,1,2,3):
            try:
                logger.debug(f"Writing {i} {rollsRemaining}")
                stateManager.write("pickle","parallelpickled/states",turnsRemaining,rollsRemaining)
                logger.debug(f"Writing more {i} {rollsRemaining}")
                stateManager.write("text","parallel/states",turnsRemaining,rollsRemaining)
                logger.debug(f"Written {i} {rollsRemaining}")
                i += 1
            except Exception as e:
                logger.error(f"Exception during writeouts: {e}")
                raise
                

def computeSubsetStateValues(turnsUsedTuples, knownValues, workerId=None, sm=None):
    slotsUsed = sum(turnsUsedTuples[0]) if len(turnsUsedTuples) > 0 else 0
    file_path = f"procs/process{slotsUsed}_{workerId}.txt"
    with open(file_path,"a") as file:
        try:
            logger.debug("Kicking off computeSubset")
            for turnsUsedTuple in turnsUsedTuples:
                computeAllStateValuesForUsedSlots(knownValues, turnsUsedTuple, file) # Last value returned should include all the previous updates
            #Make a copy for output purposes
            if sm != None:
                sm.categorizeCatalog(knownValues)
                return None
            else:
                logger.debug("Finished computeSubsetStateValues; compiling copy of results")
                result = [{} for _ in range(len(knownValues))]
                for i in range(len(knownValues)):
                    for k, v in knownValues[i].items():
                        result[i][k] = v
                logger.debug("Finished compiling result; returning")
                return result
        except Exception as e:
            logger.debug(f"Error: {e}")
            raise

def computeSubsetStateValuesWrapper(args):
    try:
        result = computeSubsetStateValues(*args)
        return result
    except Exception as e:
        logger.debug(f"Error in compute SubsetStateValuesWrapper: {e}")
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
import shutil


def purge(directory_path):
    # Check if the directory exists
    if os.path.exists(directory_path):
        # Get the list of files in the directory
        shutil.rmtree(directory_path)
        # files = os.listdir(directory_path)

        # # Iterate over each file and delete it
        # for file in files:
        #     file_path = os.path.join(directory_path, file)
        #     try:
        #         os.remove(file_path)
        #         logger.info(f"Deleted: {file_path}")
        #     except Exception as e:
        #         logger.error(f"Error deleting {file_path}: {e}")

    else:
        logger.debug(f"The directory {directory_path} does not exist.")
    os.makedirs(directory_path, exist_ok=True)


if __name__ == '__main__':
    purge("procs")
    purge("parallel")
    purge("output")
    purge("parts")
    purge("partst")
    purge("parallelpickled")
    sm = StateManager()
    profiler = cProfile.Profile()
    profiler.enable()
    #computeAllStateValues(sm)
    #parallelizeComputeStateValues(sm,8)
    parallelizeComputeMultiprocessing(sm,4)
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

    