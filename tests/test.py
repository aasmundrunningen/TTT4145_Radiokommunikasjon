import numpy as np

a = np.full(5, np.nan)
print(a)
for i in range(5):
    print(np.nanmean(a))
    a[i] = i