import numpy as np
from enum import Enum
from config import read_config_parameter

modulation_scheme = str(read_config_parameter("general", "modulation_scheme"))

def modulator(binary_data):
    if modulation_scheme == "BPSK":
        return binary_data*2-1 #0 is mapped to -1 and 1 is mapped to 1.
    elif modulation_scheme == "QPSK":
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

def demodulator(modulated_data):
    if modulation_scheme == "BPSK":
        return modulated_data > 0 #values greather than 0 gives 1, else returns 0
    elif modulation_scheme == "QPSK":
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