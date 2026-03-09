import numpy as np
a = [0, 1,2,3,4]
b = [1,2]
a = np.array(a)
b = np.array(b)

a[0:2] += b
print(a)
