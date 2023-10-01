from yahtzee_state import State
from yahtzee_state import Action
import yahtzee_state
import random

class GameManager:
    def __init__(self):
        self.sequence = []
        self.current = yahtzee_state.startState()
        self.pointsScored = 0
        
    def playRandom(self):
        while True:
            options = [x for x in self.current.legal_actions()]
            if len(options) == 0:
                breakpoint
            randomActionIndex = random.randrange(0, len(options))
            selectedAction = options[randomActionIndex]
            print(self.current)
            print(options[randomActionIndex])
            nextState, points = self.current.apply(selectedAction)
            self.pointsScored += points
            if selectedAction.chosen_row != yahtzee_state.no_row:
                print(f"Score: {points} {self.pointsScored}")
            self.current = nextState
            if self.current == yahtzee_state.finalState():
                break
    