import concurrent.futures

class State:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

def parallel_task(states):
    result = {}
    for state in states:
        # Do some computation
        result[state] = len(state.name)  # Example computation, you can replace this with your logic
    return result

if __name__ == "__main__":
    num_tasks = 8
    num_workers = 4
    states = [State(f"State{i}") for i in range(num_tasks)]
    shared_table = {}  # Initialize your shared data structure here
    assignments = [[] for _ in range(num_workers)]
    for i in range(num_tasks):
        assignments[i % num_workers].append(states[i])
    print(assignments)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(executor.map(parallel_task, assignments))

    # Update shared_table with results
    for task_id, result in enumerate(results):
        shared_table.update(result)
        
    for k,v in shared_table.items():
        print(k,v)