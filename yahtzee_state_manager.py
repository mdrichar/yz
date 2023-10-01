from yahtzee_state import State
from yahtzee_state import Action
import yahtzee_state
import pickle

class StateManager:
    def __init__(self):        
        self.state_values = [[ {}, {}, {}, {} ] for _ in range(yahtzee_state.max_turns+1)]
    
    def categorize(self,stateValues):
        for k, v in stateValues.items():
            turnsLeft = k.openSlotCount()
            rollsLeft = k.rollsLeft()
            #print(turnsLeft,rollsLeft)
            self.state_values[turnsLeft][rollsLeft][k] = v
        for tl in range(len(self.state_values)):
            for rl in range (len(self.state_values[tl])):
                size = len(self.get(tl,rl))
                print(f"{tl:02d} {rl:02d} {size:08d}")
            
    def get(self,turnsLeft,rollsLeft):
        return self.state_values[turnsLeft][rollsLeft]
    
    def writeAll(self,format,prefix):
        for tl in range(len(self.state_values)):
            for rl in range (len(self.state_values[tl])):
                self.write(format,prefix,tl,rl)
    
    def write(self,format, prefix, turnsLeft, rollsLeft):
        assert (format in ("text","pickle","msgpack"))
        if format == "text":
            file_path = f"{prefix}_{turnsLeft}_{rollsLeft}.txt"
            print("write",len(self.get(turnsLeft,rollsLeft)))
            StateManager.writeText(self.get(turnsLeft,rollsLeft),file_path)
        elif format == "pickle":
            file_path = f"{prefix}_{turnsLeft}_{rollsLeft}.pickle"
            StateManager.dumpStateValues(self.get(turnsLeft,rollsLeft),file_path)
            
    def dumpStateValues(state_values, filepath):
        if len(state_values) > 0:
            with open(filepath, 'wb') as file:
                pickle.dump(state_values,file)
            
    def loadStateValues(filepath):
        with open(filepath, 'rb') as file:
            state_values = pickle.load(file)
        return state_values
    
    def writeText(state_values, filepath):
        print(f"Size {len(state_values)}")
        with open(filepath, 'w') as file:
            for k,v in state_values.items():
                file.write(f"{k}={v[0]:.2f},{v[1]}\n")
                #print(kv)