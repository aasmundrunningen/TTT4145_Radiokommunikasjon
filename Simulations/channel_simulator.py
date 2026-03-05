#from filter_generation import RRcos_filter
import scipy as sp
import numpy as np
from enum import Enum
import matplotlib.pyplot as plt
import math

from modules.modulation import modulator, demodulator
from modules.filter import get_RRcos_filter_taps, plot_filter, tx_filter, rx_filter
from modules.config import read_config_parameter
from modules.syncronisation import downsampler, freq_sync, course_freq_sync
from modules.data_detector import add_preamble_to_data, preamble_detector

simulation = int(read_config_parameter("simulator", "simulation")) #True if simulation is running


def channel_simulator(tx_data):
    sps_rx = int(read_config_parameter("filter", "sps_rx"))
    sps_tx = int(read_config_parameter("filter", "sps_tx"))
    channel_delay = float(read_config_parameter("simulator", "channel_delay")) #normalized to symboltime
    phase_offsett = float(read_config_parameter("simulator", "phase_offsett"))
    frequency_accuracy_ppm = float(read_config_parameter("simulator", "frequency_accuracy_ppm"))
    symboles_per_second = float(read_config_parameter("general", "symboles_per_second"))
    carrier_frequency = float(read_config_parameter("general", "carrier_frequency"))
    noise_level = float(read_config_parameter("simulator", "noise_level"))
    channel_data = sp.signal.resample_poly(tx_data, up=sps_rx, down=sps_tx) #resamples the data to correct rx sampling rate
    
    
    #adds delay
    samples_delay = math.floor(channel_delay * sps_rx)
    sub_sample_delay = channel_delay * sps_rx - samples_delay #the rest delay
    channel_data = np.concatenate((np.zeros(samples_delay), channel_data)) #adds zeros to the front to add delay
    channel_data = np.interp(np.linspace(sub_sample_delay, np.size(channel_data)+sub_sample_delay, np.size(channel_data)),
                             np.linspace(0, np.size(channel_data), np.size(channel_data)),
                             channel_data)
    
    #adds phase and frequency error
    t = np.linspace(0,np.size(channel_data)/(sps_rx*symboles_per_second), np.size(channel_data))
    channel_data = channel_data * np.exp(1j*(phase_offsett + 2*np.pi*frequency_accuracy_ppm*(1e-6)*carrier_frequency*t))

    #adds AWGN
    channel_data = channel_data + np.random.normal(0, noise_level, np.size(channel_data)) + 1j*np.random.normal(0, noise_level, np.size(channel_data))



    return channel_data

def plot_eye_diagram(data, sps):
    data_splitted = np.transpose(data[0:sps*(np.size(data)//sps)].reshape(-1, sps))
    plt.plot(np.real(data_splitted), "-")
    plt.show()

def plot_constalation_diagram(data):
    lim = np.max([np.real(data), np.imag(data)])*1.2
    plt.plot(np.real(data),np.imag(data), ".")
    plt.xlim((-lim,lim))
    plt.ylim((-lim,lim))
    plt.title("Constalation diagram")
    plt.grid()
    plt.show()

def make_modulated_data():
    N = int(read_config_parameter("simulator", "data_points_in_package"))
    M = int(read_config_parameter("simulator", "number_of_data_packages"))
    r = float(read_config_parameter("simulator", "sending_factor"))
    data = []
    for i in range(M):
        data = np.concatenate((data, modulator(np.random.randint(0,2,N)), np.zeros(int(N/r))))
    
    return data

    

#checking the preamble detector
if False:
    data_package = np.random.randint(0,2,500)
    data_with_preamble = add_preamble_to_data(data_package)
    modulated_tx = modulator(data_with_preamble)
    rx_data = rx_filter(course_freq_sync(channel_simulator(tx_filter(modulated_tx))))
    preambled_data = preamble_detector(rx_data)
    plt.plot(np.linspace(0, np.size(preambled_data)/int(read_config_parameter("filter", "sps_rx")),np.size(preambled_data)), np.real(preambled_data))
    plt.plot(np.linspace(0, np.size(preambled_data)/int(read_config_parameter("filter", "sps_rx")),np.size(preambled_data)), np.imag(preambled_data))
    plt.grid()
    plt.show()
    downsampled_data = downsampler(preambled_data)




#printing data
if False:
    data = make_modulated_data()
    plt.plot(np.abs(data))
    plt.show()


#course frequency compensation test
if False:
    data_modulated = make_modulated_data()
    rx = rx_filter(course_freq_sync(channel_simulator(tx_filter(data_modulated))))

#channel syncronisation
if False:
    N = 160
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data, Modulations.BPSK)
    #adds zeros to middle of datastream
    data_modulated = np.concatenate([data_modulated[:N//2], np.zeros(N//2), data_modulated[N//2:]])
    rx = downsampler(rx_filter(course_freq_sync(channel_simulator(tx_filter(data_modulated)))))
    plot_constalation_diagram(rx)
    rx_adjusted = freq_sync(rx)
    plot_constalation_diagram(rx_adjusted)

    


#check that there is no ISI in ideal circumstances, works for QPSK
if True:
    N = 100
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data)
    rx = rx_filter(channel_simulator(tx_filter(data_modulated)))
    fig, ax = plt.subplots(1, 2)
    t = np.linspace(0, np.size(rx)/int(read_config_parameter("filter", "sps_rx")),np.size(rx)) #time points in symboltime
    for i in range(N//2):
        d = np.zeros(N//2, dtype=complex)
        d[i] = data_modulated[i]
        rx_d = rx_filter(channel_simulator(tx_filter(d)))
        ax[0].plot(t, np.real(rx_d), "--")
        ax[1].plot(t, np.imag(rx_d), "--")
    ax[0].plot(t, np.real(rx), "-")
    ax[1].plot(t, np.imag(rx), "-")
    ax[0].set_title("Real part")
    ax[1].set_title("Imaginary part")
    plt.grid()
    plt.show()