#Code for generation of filter files.
import numpy as np
import math
import matplotlib.pyplot as plt
from scipy.signal import upfirdn
from config import read_config_parameter



path = read_config_parameter("filter", "path")

#from https://github.com/analogdevicesinc/education_tools/blob/master/pluto/python/power_supply_noise_sniffer/libiio-power_supply_noise_sniffer/LTE20_MHz.ftr
#The taps for TX and taps for RX sums up to 84664 so this is probably the scaling of the filter
normalisation_sum_adam_pluto = 84664 



def generate_filter_file(taps, tx_gain, rx_gain, interpolation_rate, demodulation_rate, tx_bandwidth, rx_bandwidth, path):
    #making header

    taps = np.int16(np.round(taps / np.sum(taps) * normalisation_sum_adam_pluto)) #normalisation of filter
    with open(path, "w") as file:
        file.write("TX 3 GAIN {} INT {} #header for TX\n".format(tx_gain,interpolation_rate))
        file.write("RX 3 GAIN {} DEC {} #header for TX\n".format(rx_gain,demodulation_rate))
        file.write("BWTX {}\n".format(tx_bandwidth))
        file.write("BWRX {}\n".format(rx_bandwidth))
        for tap in taps:
            file.write("{}, {}\n".format(tap, tap))




#beta = roll_off_factor
#span = filter length in symbols
#sps  = samples per symbol
#returns filter with normalized symboltime
#formula from https://engineering.purdue.edu/~ee538/SquareRootRaisedCosine.pdf page 3
def get_RRcos_filter_taps(beta, span, sps):
    N = sps*span #number of taps
    t = np.arange(-N/2, N/2+1)/sps
    
    T_s = 1

    
    p = lambda t: 2*beta/(np.pi*np.sqrt(T_s)) * (np.cos((1+beta)*np.pi*t/T_s) + np.sin((1-beta)*np.pi*t/T_s)/(4*beta*t/T_s)) / (1-(4*beta*t/T_s)**2)
    def p_zero_denominator(t):
        t_ = t + 1e-10
        return p(t_)
    
    #includes error handling for zero denominations by shifting the t value by a fraction
    zero_denominator_condition = [np.abs(4*beta*t_/T_s) < 1e-6 or np.abs(1-(4*beta*t_/T_s)**2) < 1e-6 for t_ in t]
    h_t = np.piecewise(t, zero_denominator_condition, [p_zero_denominator, p])
    h_t = h_t / np.sum(np.pow(h_t,2)) #normalization for energy

    h_f = np.fft.fftshift(np.fft.fft(h_t))
    return t, h_t, h_f


def tx_filter(data):
    beta= float(read_config_parameter("filter", "beta"))
    span= float(read_config_parameter("filter", "span"))
    sps = int(read_config_parameter("filter", "sps_tx"))

    t, h_t, h_f = get_RRcos_filter_taps(beta, span, sps)
    return upfirdn(h = h_t,
                   x = data,
                   up = sps,
                   down = 1)

def rx_filter(data):
    beta= float(read_config_parameter("filter", "beta"))
    span= float(read_config_parameter("filter", "span"))
    sps = int(read_config_parameter("filter", "sps_rx"))

    t, h_t, h_f = get_RRcos_filter_taps(beta, span, sps)
    return upfirdn(h = h_t,
                   x = data,
                   up = 1,
                   down = 1)
    


def plot_filter():
    beta = float(read_config_parameter("filter", "beta"))
    span= float(read_config_parameter("filter", "span"))
    sps_rx = int(read_config_parameter("filter", "sps_rx"))
    sps_tx = int(read_config_parameter("filter", "sps_rx"))

    t, h_t_rx, h_f_rx = get_RRcos_filter_taps(beta, span, sps_rx)
    t, h_t_tx, h_f_tx = get_RRcos_filter_taps(beta, span, sps_tx)

    fig, (ax1, ax2) = plt.subplots(1,2)


    ax1.plot(np.linspace(-1, 1, np.size(h_f_tx)), np.abs(h_f_tx), '-', label="tx")
    ax1.plot(np.linspace(-1, 1, np.size(h_f_rx)), np.abs(h_f_rx), '-', label="rx")
    ax1.legend()
    ax1.set_title("Frequency response")
    ax1.set_xlabel("Normalized frequency")
    ax1.set_ylabel("Absolute magnitude")
    ax1.grid()

    ax2.plot(t, h_t_tx, '.', label="tx")
    ax2.plot(t, h_t_rx, '.', label="rx")
    ax2.legend()
    ax2.set_title("Impulse response")
    ax2.set_xlabel("normalized symbol time")
    ax2.set_ylabel("Normalized amplitude")
    ax2.grid()

    plt.show()
