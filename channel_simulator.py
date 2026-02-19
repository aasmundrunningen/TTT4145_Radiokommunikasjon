#from filter_generation import RRcos_filter
import scipy as sp
import numpy as np
from enum import Enum
import matplotlib.pyplot as plt
import math

from modules.modulation import modulator, demodulator, Modulations, modulator_self_test
from modules.filter import get_RRcos_filter_taps, plot_filter, tx_filter, rx_filter
from modules.config import read_config_parameter
from modules.syncronisation import downsampler, freq_sync, course_freq_sync

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


#channel syncronisation
if True:
    N = 160
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data, Modulations.BPSK)
    #adds zeros to middle of datastream
    data_modulated = np.concatenate([data_modulated[:N//2], np.zeros(N//2), data_modulated[N//2:]])
    rx = downsampler(rx_filter(course_freq_sync(channel_simulator(tx_filter(data_modulated)))))
    plot_constalation_diagram(rx)
    rx_adjusted = freq_sync(rx)
    plot_constalation_diagram(rx_adjusted)

    


#check that there is no ISI in ideal circumstances
if False:
    N = 10
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data, Modulations.BPSK)
    for i in range(N):
        d = np.zeros(N)
        d[i] = data_modulated[i]
        rx_d = rx_filter(channel_simulator(tx_filter(d)))
        plt.plot(rx_d, "--")
    rx = rx_filter(channel_simulator(tx_filter(data_modulated)))
    plt.plot(rx, "-")
    plt.grid()
    plt.show()





#eye diagram shit, for package detection
if False:
    N = 100
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data, Modulations.BPSK)
    rx = rx_filter(channel_simulator(tx_filter(data_modulated)))
    down_sampled_rx = downsampler(rx)
    plt.plot(np.abs(down_sampled_rx))
    plt.title("absolute value of samples")
    plt.show()
    #plot_eye_diagram(rx[50:-50], int(read_config_parameter("filter", "sps_rx")))


if False:
    print("input data size: {}".format(np.shape(data)))
    print("tx data size: {}".format(np.shape(tx_data)))
    print("rx data shape: {}".format(np.shape(rx_data)))



    fig, (ax1, ax2, ax3) = plt.subplots(1,3)
    ax1.plot(np.real(tx_data), label="tx")
    ax2.plot(np.real(rx_data), label="rx")
    ax3.plot(np.real(rx_filtered_data), label="rx filtered")

    ax1.legend()
    ax2.legend()
    ax3.legend()
    plt.legend()
    plt.show()
