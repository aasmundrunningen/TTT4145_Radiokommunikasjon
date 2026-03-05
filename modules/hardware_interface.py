import adi
from config import read_config_parameter
import threading
import queue
import numpy as np
import matplotlib.pyplot as plt
from modulation import demodulator, modulator
from filter import tx_filter, rx_filter
from data_detector import preamble_detector, add_preamble_to_data
import time

class Radio():
    def __init__(self):
        
        self._sdr = adi.Pluto("ip:192.168.2.1")

        self.symboles_per_second = int(read_config_parameter("general", "symboles_per_second"))
        self.sps_rx = int(read_config_parameter("filter", "sps_rx"))
        self.sample_rate = self.symboles_per_second*self.sps_rx
        
        self._sdr.sample_rate = self.sample_rate
        self._sdr.rx_lo                       = int(float(read_config_parameter("adalm_pluto", "center_freq")))
        self._sdr.tx_lo                       = int(float(read_config_parameter("adalm_pluto", "center_freq")))
        self._sdr.rx_rf_bandwidth             = int(self._sdr.sample_rate*0.8) #antialiasing
        self._sdr.rx_buffer_size              = int(float(read_config_parameter("adalm_pluto", "rx_buffer_size")))
        self._sdr.gain_control_mode_chan0 = "manual"
        self._sdr.rx_hardwaregain_chan0       = int(read_config_parameter("adalm_pluto", "rx_gain"))
        self._sdr.tx_hardwaregain_chan0       = int(read_config_parameter("adalm_pluto", "tx_gain"))

        
        self.__rx_queue = queue.Queue(maxsize=10) # Limit queue size to prevent huge lag
        self.__tx_queue = queue.Queue(maxsize=10) # Limit queue size to prevent huge lag



        self.rx_lost_packages = 0 #counts number of packages thrown away due to full queue
        
        self.stop = False #tells the threads to stop

        #start threads for tx and rx, deamon tells the thread to kil if this thread dies
        
        self.recive_chain_thread = threading.Thread(target=self.recive_chain, daemon=True)
        self.rx_thread = threading.Thread(target=self.rx, daemon=True)
        self.tx_thread = threading.Thread(target=self.tx, daemon=True)
        self.recive_chain_thread.start()
        self.rx_thread.start()
        self.tx_thread.start() 


    def recive_chain(self):
        print("Radio: starts recive chain thread")
        new_package = self.get_rx_package()
        while not self.stop:
            old_package = new_package
            new_package = self.get_rx_package()
            preamble_detector(np.concatenate)
        print("Radio: stops recive chain thread")

    def get_rx_package(self):
        return self.__rx_queue.get()

    def send_tx_package(self, data):
        package = tx_filter(modulator(add_preamble_to_data(data)))
        self.__tx_queue.put(package)

    #recives data from adam pluto and stores in rx_queu
    def rx(self):
        print("Radio: starts rx thread")
        while not self.stop:
            data = self._sdr.rx()
            try:
                self.__rx_queue.put_nowait(data)
            except queue.Full:
                #Queue is full, drops last element and insert new element
                self.__rx_queue.get()
                self.__rx_queue.put_nowait(data)
                self.rx_lost_packages = self.rx_lost_packages + 1
        print("Radio: stops rx thread")

    #transmits data to adam pluto from tx_queue
    def tx(self):
        print("Radio: start tx thread")
        while not self.stop:
            try:
                tx_data = self.__tx_queue.get(timeout=0.5) #timeout in seconds
                self._sdr.tx(tx_data)
            except queue.Empty:
                continue
        print("Radio: stops tx thread")

    def stop_radio(self):
        print("Radio: shutting down")
        print("Radio: lost rx packages: {}".format(self.rx_lost_packages))
        self.stop = True
        self.tx_thread.join() #waits untill the threads are finished
        self.rx_thread.join()
        self.recive_chain_thread.join()
        del self._sdr
    
    def __del__(self):
        if self.stop == False:
            self.stop_radio()



if __name__ == "__main__":
    print("started program")
    radio = Radio()
    
    data = np.random.randint(0,2,250)
    stop = False
    for i in range(10):
        radio.send_tx_package(data)

    radio.stop_radio()
    del radio
    print("stoped program")



        





