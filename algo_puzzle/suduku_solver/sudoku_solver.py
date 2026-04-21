from mytry.linkedin.suduku.library_sudoku import solveFast
import numpy as np
import time 
import copy

M = 1000
a = np.zeros(M)
b = np.zeros(M)

grid = [
    [5, 0, 0, 4, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 9, 3, 0, 0, 8],
    [0, 7, 0, 0, 0, 0, 0, 1, 0],
    [0, 6, 0, 1, 0, 9, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 7, 3, 0],
    [0, 0, 2, 6, 0, 0, 0, 0, 0],
    [0, 9, 0, 0, 8, 0, 4, 0, 7],
    [0, 2, 3, 0, 0, 0, 0, 9, 0],
    [0, 5, 0, 0, 0, 4, 0, 0, 0]
]

for i in range(M):
    # g = copy.deepcopy(grid)
    # uno = time.perf_counter()
    # solve(g)
    # due = time.perf_counter()
    # g = copy.deepcopy(grid)
    # solveSlow(g)
    tre = time.perf_counter()
    g = copy.deepcopy(grid)
    solveFast(g)
    quattro = time.perf_counter()
    # a[i] = tre-due
    b[i] = quattro-tre

print("to be solved")
for r in grid:
    print(r)

print("solved")
for r in g:
    print(r)

print("time: ", b.mean())
    