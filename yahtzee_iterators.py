import itertools

# Iterate over all the tuples of 0s and 1s of given length where the total number of 1s is ones_cnt
def allBinaryPermutationsFixedOnesCnt(length,ones_cnt):
    if ones_cnt <= 0:
        yield (0,)*length, -1
    else:
        for starter, rightmost_one_index in allBinaryPermutationsFixedOnesCnt(length,ones_cnt-1):
            for next_one_index in range(rightmost_one_index + 1, length):
                new_item = list(starter)
                new_item[next_one_index] = 1
                yield tuple(new_item), next_one_index
                
# Iterate over all the 2^length tuples of 1s and 0s with given length
def allBinaryPermutations(length):
    for n in range(2**length):
        binary_str = bin(n)[2:]  # Convert integer to binary string, remove '0b' prefix
        binary_str = binary_str.zfill(length)  # Pad the string with zeros to the specified width
        binary_tuple = tuple(map(int, binary_str))  # Convert each character to an integer and create a tuple
        yield binary_tuple

   



# For each possible combination of upper section scores filled in, determine the total possible combinations of total points
# scored for the upper section (so far). Subtract this from 63 to determine the number of points that could be remaining to 
# achieve the bonus
def getBonusPtsPossibilities():
    possibilities = {}
    possibleScoresBySlot = [(0,1,2,3,4,5),(0,2,4,6,8,10),(0,3,6,9,12,15),(0,4,8,12,16,20),(0,5,10,15,20,25),(0,6,12,18,24,30)]
    for item in allBinaryPermutations(5):
        prodPoss = [(0,)]
        for i, v in enumerate(item):
            if v == 0:
                prodPoss.append(possibleScoresBySlot[i])
        #print(item,prodPoss)
        possPtsStillNeededForBonus = [0]*64
        for possibleScoreCombination in itertools.product(*prodPoss):
            possPts = sum(possibleScoreCombination)
            possPtsToBonus = max(63-possPts,0)
            possPtsStillNeededForBonus[possPtsToBonus] = 1
        possibilities[item] = possPtsStillNeededForBonus
    return possibilities             
        

def getRollOutcomes(): 
    all_dice = 5 #This is not really changeable, just avoiding a magic number
    roll_outcomes = [{} for i in range(6)]
    #roll_outcomes.append({})

    # If I roll 0 dice, the probability of rolling 0 1s, 0 2s, 0 3s, 0 4s, 0 5s, and 0 6s is 1
    roll_outcomes[0][(0,0,0,0,0,0)] = 1

    base = [(1,0,0,0,0,0),(0,1,0,0,0,0),(0,0,1,0,0,0),(0,0,0,1,0,0),(0,0,0,0,1,0),(0,0,0,0,0,1)]

    # First enumerate all the outcomes of rolling one die. (1,0,0,0,0,0) means rolling a 1, (0,0,1,0,0,0) means rolling a three.
    # There are six outcomes from rolling one die. Now, when I go to figure out all the outcomes of rolling two dice, I can iterate
    # over all the one die-outcomes, and for each of those, I can enumerate the six possibilities that result from adding a 1 or a 2
    # ... or 6 to that one-die outcome. 

    # Note that there could be some duplicates here. If my one-die outcome of rolling a 1 (1,0,0,0,0,0) and then I add the second die is a 3,
    # that would be (1,0,1,0,0,0). But when I consider the one-die outcome of rolling a 3 (0,0,1,0,0,0) and I add the second die is a 1, that
    # is also (1,0,1,0,0,0). Adding up the number of duplicates and dividing by the total (for each die count) gives the probability of that 
    # outcome. So for two dice, 6*6 caeses will be enumerated. The probability of rolling a pair of ones (2,0,0,0,0,0) is 1/36, but the 
    # probability of rolling a one and a three is 2/36=1/18, because the (1,0,1,0,0,0) will get generated twice.

    for i in range(1,len(roll_outcomes)):
        #print("i:",i)
        for j in range(6):
            #zlist = [0] * 6
            #zlist[j] = 1
            #print(f"(i,j):({i},{j})")
            for key,val in roll_outcomes[i-1].items():
                #print("Key: ",key)
                #print("Base[j]: ", base[j])
                #print("Zip(key,base[j]): ",zip(key,base[j]))
                t = tuple(map(sum,zip(key,base[j])))
                #print("t",t)
                if t in roll_outcomes[i]:
                    roll_outcomes[i][t] += val
                else:
                    roll_outcomes[i][t] = val
    roll_outcomes_sizes = [6**x for x in range(len(roll_outcomes))]
    for i in range(all_dice+1):
        total_outcomes = roll_outcomes_sizes[i]
        for key in roll_outcomes[i]:
            roll_outcomes[i][key] = roll_outcomes[i][key] / total_outcomes

    return roll_outcomes


