#from filter_generation import RRcos_filter
import scipy as sp
import numpy as np
from enum import Enum
import matplotlib.pyplot as plt

from modules.modulation import modulator, demodulator, Modulations, modulator_self_test
from modules.filter import get_RRcos_filter_taps, plot_filter, tx_filter, rx_filter
from modules.config import read_config_parameter


def channel_simulator(tx_data):
    sps_rx = int(read_config_parameter("filter", "sps_rx"))
    sps_tx = int(read_config_parameter("filter", "sps_tx"))
    delay_in_samples = float(read_config_parameter("simulator", "delay_in_samples"))
    phase_offsett = float(read_config_parameter("simulator", "phase_offsett"))
    frequency_offsett = float(read_config_parameter("simulator", "frequency_offsett"))
    symboles_per_second = float(read_config_parameter("general", "symboles_per_second"))
    
    channel_data = sp.signal.resample_poly(tx_data, up=sps_rx, down=sps_tx) #resamples the data to correct rx sampling rate
    
    
    #adds delay
    total_samples_delay = delay_in_samples // sps_rx
    channel_data = np.concatenate()
    rest_delay = delay_in_samples % sps_rx
    

    return channel_data

def plot_eye_diagram(data, sps):
    data_splitted = np.transpose(data[0:sps*(np.size(data)//sps)].reshape(-1, sps))
    plt.plot(np.real(data_splitted), "-")
    plt.show()

def plot_constalation_diagram(data):
    plt.plot(np.real(data),np.imag(data), ".")
    plt.xlim((-2,2))
    plt.ylim((-2,2))
    plt.title("Constalation diagram")
    plt.show()


#channel syncronisation
if False:
    N = 10
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data, Modulations.BPSK)
    rx = rx_filter(channel_simulator(tx_filter(data_modulated)))
    FFT_rx = sp.fft.fftshift(sp.fft.fft(rx))
    FFT_freq = sp.fft.fftshift(sp.fft.fftfreq(np.size(rx)))
    plt.plot(FFT_freq, FFT_rx)
    plt.show()



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


def downsampler(data):
    sps = int(read_config_parameter("filter", "sps_rx"))
    down_sampled_data = []
    
    time = 0 #normalized to symboltime, so 1 is one sample periode

    step = sps #Distance to move for next symbol

    kp = 0.01
    ki = 0.01
    integral = 0

    while time < len(data)-sps:
        y_curr = np.interp(time         , range(len(data)),data)
        y_mid  = np.interp(time - step/2, range(len(data)),data)
        y_prev = np.interp(time - step  , range(len(data)),data)
        e = np.real(y_mid)*(np.real(y_curr)-np.real(y_prev)) #Gardner timing error detector algorithm
        integral = integral + e
        step = sps + ki*integral + kp*e #pi controller for step movement
        time = time + step
        print(time)
        down_sampled_data.append(y_curr)

    return np.array(down_sampled_data)


#eye diagram shit, for package detection
if True:
    N = 10
    data = np.random.randint(0,2,N)
    data_modulated = modulator(data, Modulations.BPSK)
    rx = rx_filter(channel_simulator(tx_filter(data_modulated)))
    down_sampled_rx = downsampler(rx)
    plt.plot(np.abs(down_sampled_rx))
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
