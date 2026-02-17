import numpy as np

upsampling_factor = 5
x = [1, -1, 1]
x_upsampled = np.zeros(np.size(x)*upsampling_factor)
x_upsampled[::upsampling_factor] = x
print(x)
print(x_upsampled)