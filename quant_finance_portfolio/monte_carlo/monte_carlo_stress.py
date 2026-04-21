import matplotlib.pyplot as plt
import numpy as np
import time

start = time.time()

N = 1000000 # numero di simulazioni
T = 252 # numero di periodi temporali
S0 = 100

prices = np.zeros((N,T+1))
prices[:,0] = S0

for i in range(N):
    for t in range(1,T+1):
        s = prices[i,t-1]
        prices[i,t] = np.random.normal(s,1)

end = round(time.time() - start,2)
print(f"Runtime: {end}s")

# for el in prices:   
#     plt.plot(el)
# plt.show()



