#Code for generation of filter files.
import numpy as np
import math
import matplotlib.pyplot as plt
from scipy.signal import upfirdn, butter, lfilter, lfiltic, freqz
from config import read_config_parameter


class FILTERS():
    def __init__(self):
        path = read_config_parameter("filter", "path")

        #from https://github.com/analogdevicesinc/education_tools/blob/master/pluto/python/power_supply_noise_sniffer/libiio-power_supply_noise_sniffer/LTE20_MHz.ftr
        #The taps for TX and taps for RX sums up to 84664 so this is probably the scaling of the filter
        normalisation_sum_adam_pluto = 84664 


        tx_beta= float(read_config_parameter("filter", "beta"))
        tx_span= float(read_config_parameter("filter", "span"))
        self.tx_sps = int(read_config_parameter("filter", "sps_tx"))
        t, self.tx_filter_taps, h_f = self.get_RRcos_filter_taps(tx_beta, tx_span, self.tx_sps)

        rx_beta= float(read_config_parameter("filter", "beta"))
        rx_span= float(read_config_parameter("filter", "span"))
        rx_sps = int(read_config_parameter("filter", "sps_rx"))
        t, self.rx_filter_taps, h_f = self.get_RRcos_filter_taps(rx_beta, rx_span, rx_sps)
        self.rx_filter_state = lfiltic(b=self.rx_filter_taps, a=[1], y=0) #initial state of filter

        rx_recive_freq = float(read_config_parameter("adalm_pluto", "rx_recive_freq"))
        rx_lo_freq = float(read_config_parameter("adalm_pluto", "rx_lo_freq"))
        max_freq_offset_ppm = float(read_config_parameter("adalm_pluto", "max_freq_offset_ppm"))
        symboles_per_second = float(read_config_parameter("general", "symboles_per_second"))
        sps_rx = float(read_config_parameter("filter", "sps_rx"))
        self.fs = symboles_per_second*sps_rx
        center_f = np.abs(rx_recive_freq - rx_lo_freq)
        low_freq = center_f - max_freq_offset_ppm*(1e-6)*rx_lo_freq*3
        high_freq = center_f + max_freq_offset_ppm*(1e-6)*rx_lo_freq*3 #two times is the worst case of both adam pluto and 4 times gives margine
        print("Butterwort freq range {}, {}".format(low_freq, high_freq))
        self.bandpass_b_coeff, self.bandpass_a_coeff = butter(N=4, Wn=[low_freq, high_freq], btype="bandpass", output="ba", fs=self.fs)
        self.bandpass_state = lfiltic(b=self.bandpass_b_coeff, a=self.bandpass_a_coeff, y=0) #initial state of filter
            
    def generate_filter_file(self, taps, tx_gain, rx_gain, interpolation_rate, demodulation_rate, tx_bandwidth, rx_bandwidth, path):
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
    def get_RRcos_filter_taps(self, beta, span, sps):
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


    def tx_filter(self, data):
        return upfirdn(h = self.tx_filter_taps,
                    x = data,
                    up = self.tx_sps,
                    down = 1)

    def rx_filter(self, data):
        #the memory handle is for ensuring that the filter can work on continous data which is packed into packages, essentialy combining the results from the previous and new datapackage
        filtdata, self.rx_filter_state = lfilter(self.rx_filter_taps, [1.0], data, zi=self.rx_filter_state)
        return filtdata
    
    def rx_bandpass_filter(self, data):
        #the memory handle is for ensuring that the filter can work on continous data which is packed into packages, essentialy combining the results from the previous and new datapackage
        filtdata, self.bandpass_state = lfilter(self.bandpass_b_coeff, self.bandpass_a_coeff, data, zi=self.bandpass_state)
        return filtdata

    def plot_filter(self):
        beta = float(read_config_parameter("filter", "beta"))
        span= float(read_config_parameter("filter", "span"))
        sps_rx = int(read_config_parameter("filter", "sps_rx"))
        sps_tx = int(read_config_parameter("filter", "sps_rx"))

        t, h_t_rx, h_f_rx = self.get_RRcos_filter_taps(beta, span, sps_rx)
        t, h_t_tx, h_f_tx = self.get_RRcos_filter_taps(beta, span, sps_tx)

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


if __name__ == "__main__":
    filters = FILTERS()

    random_test_data = np.random.randint(0, 2, 1024)*2 - 1
    filters.tx_filter(random_test_data)
    filters.rx_filter(random_test_data)
    print("RX filter: size incoming data {}, size outgoing data, {}".format(np.size(random_test_data), np.size(filters.rx_filter(random_test_data))))

    print("Butterwort filter: size incoming data {}, size outgoing data, {}".format(np.size(random_test_data), np.size(filters.rx_bandpass_filter(random_test_data))))

    filters.plot_filter()

    w, h = freqz(filters.bandpass_b_coeff, filters.bandpass_a_coeff, worN=8000, fs=filters.fs)
    plt.plot(w, 20 * np.log10(np.maximum(abs(h), 1e-5)))
    plt.title("Butterworth Filter Response")
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Amplitude [dB]')
    plt.grid(True)
    plt.show()

