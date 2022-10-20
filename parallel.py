import os
import time
import numpy as np
import multiprocessing as mp

from time import sleep
from random import random
from multiprocessing import Pool
 
def findLHS(arg1, arg2):
    '''
    do stuff
    '''
    
    arr, multiplier = arg1, arg2


    pid  = os.getpid()
    ppid = os.getppid()
    start = time.time()

    arr = np.multiply(arr, multiplier)

    res = 0
    for i in range(len(arr)):
        count = 0
        flag = False
        for j in range(len(arr)):
            if arr[j] == arr[i]:
                count += 1
            elif arr[j] + 1 == arr[i]:
                count += 1
                flag = True
        if flag:
            res = max(res, count)

    stop  = time.time()
    completed_in  = round(stop - start,2)
    print(f"PPID {ppid}->{pid} Completed in {completed_in} seconds with result {res}")
    return res


# # task function executed in a child worker process
# def task(arg1, arg2):
#     # block for a moment
#     sleep(random())
#     # report values
#     print(f'Task {arg1}, {arg2}.', flush=True)
#     # return a result
#     return arg1 + arg2
 
# protect the entry point
if __name__ == '__main__':
    size = 10
    arrays = np.random.randint(0, 10, (size, 250))
    multiplier = 1
    args = [(arr, multiplier) for arr in arrays]

    # create the process pool
    start = time.time()
    with mp.Pool(processes=mp.cpu_count()) as pool:       
        # issue multiple tasks each with multiple arguments
        results = pool.starmap(findLHS, args)
    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    start = time.time()
    res = []
    for arg in args:
        res += [findLHS(*arg)]
    end = time.time()
    print("-------------------------------------------")
    print(f"Without workers completed in {round(end-start,2)}")
    print()

# if __name__ == '__main__':

#     print("dit moet maar 1x draaien")

#     size = 100
#     arrays = np.random.randint(0, 10, (size, 250))

#     start = time.time()
#     args = (arrays, 2)
#     with mp.Pool(processes=mp.cpu_count()) as pool:
#         pool.starmap(findLHS, args)
#     end = time.time()
#     print("-------------------------------------------")
#     print(f"With workers completed in {round(end-start,2)}")

#     start = time.time()
#     res = []
#     for arr in arrays:
#         res = res + [findLHS(args)]
#     print(res)
#     end = time.time()
#     print("-------------------------------------------")
#     print(f"Without workers completed in {round(end-start,2)}")