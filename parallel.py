import os
import time
import pandas as pd
import numpy as np
import multiprocessing as mp
from multiprocessing.pool import ThreadPool

def findLHS(arr):
    '''
    do stuff
    '''
    pid  = os.getpid()
    ppid = os.getppid()
    start = time.time()

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
    # print("PPID %s->%s Completed in %s seconds"%(ppid,pid,completed_in))
    return res

if __name__ == '__main__':
    size = 1000
    arrays = np.random.randint(0, 10, (size, 250))

    start = time.time()
    with mp.Pool(processes=mp.cpu_count()) as pool:
        print(pool.map(findLHS, arrays))

    end = time.time()
    print("-------------------------------------------")
    print(f"With workers completed in {round(end-start,2)}")

    start = time.time()
    res = []
    for arr in arrays:
        res = res + [findLHS(arr)]
    print(res)
    end = time.time()
    print("-------------------------------------------")
    print(f"Without workers completed in {round(end-start,2)}")

# if __name__ == '__main__':
    # logical    = False
    # df_results = []
    # num_procs  = psutil.cpu_count(logical=logical)
    # if len(sys.argv) > 1:
    #     num_procs = int(sys.argv[1])

    
    # # fill a two dimensional array with random numbers between 0 and 10
    # size = 10
    # arrays = np.random.randint(0, 10, (size, 200))
    # found_lhs = np.full(size, np.nan)

    # test = []

    # start = time.time()
    # with concurrent.futures.ProcessPoolExecutor(max_workers=num_procs) as executor:
    #     results = [executor.submit(findLHS(arr)) for arr in arrays]
    #     for result in concurrent.futures.as_completed(results):
    #         try:
    #             #df_results.append(result.result())
    #             test += [result.result()]
    #         except Exception as ex:
    #             print(str(ex))
    #             pass
    # end = time.time()
    # print("-------------------------------------------")
    # print("PPID %s Completed in %s"%(os.getpid(), round(end-start,2)))