import numpy as np


a = np.zeros(10)

for i in range(20): 
    a[:-1] = a[1:]
    a[-1] = i
    print(a)