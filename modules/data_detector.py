
import scipy as sp
from modules.config import read_config_parameter
from modules.modulation import modulator
from modules.filter import rx_filter, tx_filter
import numpy as np
import matplotlib.pyplot as plt

correlation_treshold = float(read_config_parameter("preamble_detector", "correlation_treshold"))
sps_rx = int(read_config_parameter("filter", "sps_rx"))
sps_tx = int(read_config_parameter("filter", "sps_tx"))

preamble = np.array(list(map(int, list(format(int(read_config_parameter("general", "preamble"), base=16), 'b'))))) #ikke tenkt på det, det funker
modulated_preamble = modulator(preamble)
reference_signal = rx_filter(sp.signal.resample_poly(tx_filter(modulated_preamble), up=sps_rx, down=sps_tx))


#takes in the data after rx_filter and returns index of start of preamble or None if no data was detected
def preamble_detector(data):
    normalization_constant = np.sqrt(np.sum(np.abs(data)**2) * np.sum(np.abs(reference_signal)**2))
    norm_cross_cor = np.abs(sp.signal.correlate(data, reference_signal, mode="full") / normalization_constant)
    peak_correlation = np.argmax(norm_cross_cor) #peak in cross correlation
    
    if norm_cross_cor[peak_correlation] > correlation_treshold:
        start_of_data_package = peak_correlation - np.size(reference_signal)+1
        return start_of_data_package
    else:
        return None


#adds the preamble to the binary bitstream
def add_preamble_to_data(data):
    return np.concatenate((preamble, data))

