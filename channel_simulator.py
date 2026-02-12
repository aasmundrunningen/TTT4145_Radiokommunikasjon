#from filter_generation import RRcos_filter
import scipy as sp
import numpy as np
from enum import Enum

#t, RRC_t, RRC_f = RRcos_filter(beta=0.7, span=5, sps=4)

data_size = 8 #number of bits
random_binary_stream = np.random.randint(low=0, high=1, size=data_size)

class Modulations(Enum):
    BPSK = "bpsk"
    QPSK = "qpsk"

def modulator(binary_data, modulation_type):
    if modulation_type == Modulations.BPSK:
        return binary_data*2-1 #0 is mapped to -1 and 1 is mapped to 1.
    elif modulation_type == Modulations.QPSK:
        if np.size(binary_data) % 2 != 0:
            print("ERROR: function modulator: binary data is not a even number")
            return None
        else:
            real_data = binary_data[::2]*2-1 #every even element
            imag_data = binary_data[1::2]*2-1 #every odd element
            return real_data + 1j*imag_data
    else:
        print("ERROR: function modulator: modulation type not supported")
        return None

def demodulator(modulated_data, modulation_type):
    if modulation_type == Modulations.BPSK:
        return modulated_data > 0 #values greather than 0 gives 1, else returns 0
    elif modulation_type == Modulations.QPSK:
        if np.size(modulated_data) % 2 != 0:
            print("ERROR: function modulator: binary data is not a even number")
            return None
        else:
            real_data = np.real(modulated_data) > 0 #converts both branches to binary data
            imag_data = np.imag(modulated_data) > 0
            return np.array([real_data, imag_data]).flatten("F")
    else:
        print("ERROR: function modulator: modulation type not supported")
        return None

#checking all modulations schemes.
data = np.random.randint(0,1,1024)
for mod in Modulations:
    modulaed_data = modulator(data, mod)
    demodlated_data = demodulator(modulaed_data, mod)
    print("Passing test of modulation {}: {}".format(mod, all(demodlated_data==data)))

