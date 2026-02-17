import numpy as np
from enum import Enum

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


#self test of modulator
#checks if demodulator reproduces the data before the modulator
def modulator_self_test():
    #checking all modulations schemes.
    data = np.random.randint(0,2,1024)
    for mod in Modulations:
        modulaed_data = modulator(data, mod)
        demodlated_data = demodulator(modulaed_data, mod)
        print("Passing test of {}: {}".format(mod, all(demodlated_data==data)))