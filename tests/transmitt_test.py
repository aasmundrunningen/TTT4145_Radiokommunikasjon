import numpy as np
import adi
import time

sample_rate = 1e6 # Hz
center_freq = 915e6 # Hz

sdr = adi.Pluto("ip:192.168.2.1")
sdr.sample_rate = int(sample_rate)
sdr.tx_rf_bandwidth = int(sample_rate) # filter cutoff, just set it to the same as sample rate
sdr.tx_lo = int(center_freq)
sdr.tx_hardwaregain_chan0 = -10 # Increase to increase tx power, valid range is -90 to 0 dB




#loading filter
#with open('filter.ftr', 'r') as filter_file:
#    filter_data = filter_file.read()
#    sdr.filter(filter_data)
sdr.filter = "filter.ftr"



N = 10000 # number of samples to transmit at once
t = np.arange(N)/sample_rate
#samples = 0.5*np.exp(2.0j*np.pi*100e3*t) # Simulate a sinusoid of 100 kHz, so it should show up at 915.1 MHz at the receiver
#samples = np.random.uniform(-1, 1, N)
samples = np.random.standard_normal(N) #sending white noise to see the filter design
samples *= np.max(np.absolute(samples))

samples *= 2**14 # The PlutoSDR expects samples to be between -2^14 and +2^14, not -1 and +1 like some SDRs

# Transmit our batch of samples 100 times, so it should be 1 second worth of samples total, if USB can keep up
#for i in range(1000):
sdr.tx_cyclic_buffer = True    
sdr.tx(samples) # transmit the batch of samples once
time.sleep(5)