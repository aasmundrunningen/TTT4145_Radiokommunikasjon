#Code for generation of filter files.
import numpy as np
import math
import matplotlib.pyplot as plt

path = "RCC_filter.ftr"

def RRcos_filter_2(beta, span, sps):
    #formula from https://engineering.purdue.edu/~ee538/SquareRootRaisedCosine.pdf page 3
    #beta = roll_off_factor
    #span = filter length in symbols
    #sps  = samples per symbol
    #returns filter with normalized symboltime
    N = sps*span #number of taps
    t = np.arange(-N/2, N/2+1)/sps
    
    T_s = 1
    p = lambda t: 2*beta/(np.pi*np.sqrt(T_s)) * (np.cos((1+beta)*np.pi*t/T_s) + np.sin((1-beta)*np.pi*t/T_s)/(4*beta*t/T_s)) / (1-(4*beta*t/T_s)**2)
    
    h_t = p(t)
    for i, h in enumerate(h_t): #handles singularities and undefined points by approximation the value
        if math.isinf(h) or math.isnan:
            h_t[i] = p(t[i] + (t[1] - t[0])*0.0000001)
    h_f = np.fft.fftshift(np.fft.fft(h_t))
    return t, h_t, h_f

def generate_filter_file(taps, tx_gain, rx_gain, interpolation_rate, demodulation_rate, tx_bandwidth, rx_bandwidth, path):
    #making header
    with open(path, "w") as file:
        file.write("TX 3 GAIN {} INT {} #header for TX\n".format(tx_gain,interpolation_rate))
        file.write("RX 3 GAIN {} DEC {} #header for TX\n".format(rx_gain,demodulation_rate))
        file.write("BWTX {}\n".format(tx_bandwidth))
        file.write("BWRX {}\n".format(rx_bandwidth))
        for tap in np.int16(np.round(taps*(2**15-1),decimals=0)):
            file.write("{}, {}\n".format(tap, tap)) #rounds the taps to 16bit signed integer



t, RRC_t, RRC_f = RRcos_filter_2(beta=0.7, span=5, sps=4)

generate_filter_file(taps=RRC_t,
                     tx_gain=0,
                     rx_gain=-6,
                     interpolation_rate=2,
                     demodulation_rate=2,
                     tx_bandwidth=20000,
                     rx_bandwidth=20000,
                     path="test_filter.ftr")


fig, (ax1, ax2) = plt.subplots(2,1)

ax1.plot(np.abs(RRC_f**2), '-', label="RRC2_h_f")
ax1.legend()

ax2.plot(t, RRC_t, '.', label="RRC2_h_t")
ax2.plot(t, np.convolve(RRC_t, RRC_t, "same"), '*', label="RRC2_h_t_conv")
ax2.legend()
ax2.grid()

plt.show()





