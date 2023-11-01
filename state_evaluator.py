import yahtzee_state

class StateEvaluator:
    @staticmethod
    def getStateValue(state, known_values):
        rollsLeft = state.getRollsLeft()
        if not state in known_values:
            StateEvaluator.computeStateValue(state, known_values)
        return known_values[rollsLeft][state]
        
    @staticmethod    
    def computeStateValue(state, known_values):
        try:
            rollsLeft = state.getRollsLeft()
            nextStateRollsLeft = (rollsLeft - 1) % (yahtzee_state.max_rolls_allowed + 1) # e.g., if 0 left now, there will be 3 in next State
            if state.openSlotCount() == 0:
                ##print("Base case: ", state)
                known_values[rollsLeft][state] = (0, None)
            else:
                max_value = -1000
                best_action = None
                # for action in state.legal_actions():
                #     #print ("    Considering action: ", action)
                #     immediate_reward = sum(state.immediateReward(action))
                #     expected_future_value = 0
                #     total_prob = 0
                #     for (next_state, prob) in state.stateTransitionsFrom(action):
                #         total_prob += prob
                #         # if not next_state in state_values:
                #         #     print("Not in there",next_state)
                #         if not next_state in known_values[nextStateRollsLeft]:
                #             print("ERROR: state, action, next state follow")
                #             print(state)
                #             print(action)
                #             print(next_state)
                #         assert next_state in known_values[nextStateRollsLeft]
                #         #print("                 ",prob, next_state, "Val: ",state_values[next_state])
                #         expected_future_value += prob * known_values[nextStateRollsLeft][next_state][0]
                #         total_value = immediate_reward + expected_future_value
                #         if total_value > max_value:
                #             max_value = total_value
                #             best_action = action
                #     #print("Action %s TV: %2f" % (action, total_value))
                # #print("In ",state," value is ",max_value," by doing ",best_action)
                known_values[rollsLeft][state] = (max_value, best_action)
        except Exception as e:
            print(f"Exception in computeStateValue {e}")
            raise
            