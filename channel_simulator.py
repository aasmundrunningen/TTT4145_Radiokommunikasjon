SIMULATOR = True
IDEAL_CHANNEL = True
SNR = 20
import numpy as np

def simulator(tx):
    rx = np.zeros(np.shape(tx))
    if SIMULATOR:
        if IDEAL_CHANNEL:
            rx = tx
        
    return rx
