import random
import time
from matplotlib import pyplot as plt
import numpy as np

n_sim=100
inside = 0
start = time.time()
fig = plt.figure(figsize=[5,5])
plt.xlim(0,1)
plt.ylim(0,1)
plt.ion() #intercative matplotlib

# circle draw
xc = 0.5
yc = 0.5
r = 0.5
theta = np.linspace(0,2*np.pi,100)
x = xc + r*np.cos(theta)
y = yc + r*np.sin(theta)
plt.plot(x,y)

for _ in range(n_sim):
    x = random.random()
    y = random.random()

    if (x-xc)**2+(y-yc)**2 <= r**2:
        inside += 1
        plt.scatter(x,y,s=10,color="green")
    else:
        plt.scatter(x,y,color="red",s=10)
    plt.pause(0.001)

plt.ioff()
pi = inside/n_sim * 4
print(f"Pi estimation: {pi}, with {n_sim} sample points used.")
print(f"in {round(time.time() - start,5)}s")

plt.show()