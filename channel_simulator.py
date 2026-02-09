SIMULATOR = True
IDEAL_CHANNEL = True
SNR = 20
import adi
import numpy as np
import time

NO_LOOPBACK = 0
DIGITAL_LOOPBACK = 1
RF_LOOPBACK = 2



def simulator():
    # Koble til pluto
    sdr = adi.Pluto("ip:192.168.2.1")

    # Config
    sdr.sample_rate = int(20e6)      # Baseband sampling rate for tx and rx frontend 2 MSPS
    sdr.loopback = NO_LOOPBACK
    center_frequency = 2.4e9


    #rx config
    sdr.rx_rf_bandwidth = sdr.sample_rate #Båndbredde, 2MHz
    sdr.rx_lo = int(center_frequency)           #Senterfrekvens,  2 GHz
    sdr.rx_buffer_size = int(sdr.sample_rate * 0.2) #size of buffer, 0.2 is number of seconds with buffer
    gain = 50 #in db, range from 0 to 74.5dB
    sdr.gain_control_mode = "manual" #"slow_attack"
    sdr.rx_hardwaregain_chan0 = gain
    #sdr._get_iio_attr('voltage0','hardwaregain', False) #gets the current gain level in realtime
    sdr.rx_enabled_channels = [0]

    #tx config
    #sdr.tx_enabled_channels = [0]
    sdr.tx_rf_bandwidth = sdr.sample_rate
    sdr.tx_lo = int(center_frequency)
    

    
    #generating data for transmitt
    num_symbols = 1000 #number of symbols to transmitt
    x_int = np.random.randint(0,3, num_symbols)
    x_rad = x_int * 2*np.pi/4 #generates QPSK angles
    symbols = np.cos(x_rad) + 1j*np.sin(x_rad) #generates symboles as complex angles
    symbols *= 2**14 #adam pluto expects values in range -2^14 to 2^14

    #continus data transmittion
    sdr.tx_hardwaregain_chan0 = -20 #gain in dB, range from -90dB to 0dB
    sdr.tx_destroy_buffer()
    sdr.tx_cyclic_buffer = False #cyclic buffer, causes continous transmittion
    
    for i in range(10):
        sdr.tx(symbols)
    


    """
    #reciving data
    for i in range(2):
        raw_data = sdr.rx() #cleares buffer
    
    raw_data = sdr.rx()
    print(raw_data[0:10])

    # Stop transmitting
    time.sleep(5)
    sdr.tx_destroy_buffer()
    """
simulator()
