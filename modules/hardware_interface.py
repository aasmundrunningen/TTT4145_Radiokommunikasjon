import adi
from config import read_config_parameter
import threading
import queue
import numpy as np
import matplotlib.pyplot as plt
from modulation import demodulator, modulator
from filter import tx_filter, rx_filter
from data_detector import PREAMBLE
import time

class Radio():
    def __init__(self):
        self._sdr = adi.Pluto(read_config_parameter("adalm_pluto", "ip"))

        self.symboles_per_second = int(read_config_parameter("general", "symboles_per_second"))
        self.sps_rx = int(read_config_parameter("filter", "sps_rx"))
        self.sample_rate = self.symboles_per_second*self.sps_rx
        
        self._sdr.sample_rate = self.sample_rate
        print("Radio: sampling rate: {} MsPs".format(self.sample_rate/1e6))
        self._sdr.tx_lo                       = int(float(read_config_parameter("adalm_pluto", "center_freq")))
        self._sdr.tx_hardwaregain_chan0       = int(read_config_parameter("adalm_pluto", "tx_gain"))

        self._sdr.gain_control_mode_chan0     = "manual"
        self._sdr.rx_lo                       = int(float(read_config_parameter("adalm_pluto", "center_freq")))
        self._sdr.rx_rf_bandwidth             = int(self._sdr.sample_rate*0.8) #antialiasing
        self._sdr.rx_buffer_size              = int(float(read_config_parameter("adalm_pluto", "rx_buffer_size")))
        self._sdr.rx_hardwaregain_chan0       = int(read_config_parameter("adalm_pluto", "rx_gain"))

        
        #self._sdr.rx_lo = int(915e6)
        #self._sdr.tx_lo = int(915.5e6)
        
        self.__rx_queue = queue.Queue(maxsize=10) # Limit queue size to prevent huge lag
        self.__tx_queue = queue.Queue(maxsize=10) # Limit queue size to prevent huge lag

        self._fft_queue = queue.Queue(maxsize=1) # Limit queue size to prevent huge lag


        self.rx_lost_packages = 0 #counts number of packages thrown away due to full queue
        
        self.tx_package_counter = 0 #counts number of transmitted packages
        self.rx_package_counter = 0 #counts number of detected packages


        self.stop = False #tells the threads to stop

        #start threads for tx and rx, deamon tells the thread to kil if this thread dies
        
        self.recive_chain_thread = threading.Thread(target=self.recive_chain, daemon=True)
        self.rx_thread = threading.Thread(target=self.rx, daemon=True)
        self.tx_thread = threading.Thread(target=self.tx, daemon=True)
        self.recive_chain_thread.start()
        self.rx_thread.start()
        self.tx_thread.start()

        self.preamble = PREAMBLE()
    
    def enable_fft_plot(self):
        # We don't start a thread here anymore!
        # Instead, we set up the figure and the animation.
        self.fft_fig, self.ax = plt.subplots()
        self.fft_line, = self.ax.plot([], [])
        self.ax.set_ylim(0, 100) # Adjust based on your signal levels
        self.ax.set_xlim(-1, 1)

        from matplotlib.animation import FuncAnimation
        # interval=100 means the plot updates 10 times per second
        self.ani = FuncAnimation(self.fft_fig, self._update_fft, interval=1, cache_frame_data=False)
        plt.show(block=False) # block=False lets the script continue

    def _update_fft(self, frame):
        try:
            # Check the queue for new SDR data
            data = self._fft_queue.get_nowait()
            fft = np.fft.fftshift(np.fft.fft(data))
            mag = 20*np.log10(np.abs(fft))
            
            x = np.linspace(-1, 1, len(mag))
            self.fft_line.set_data(x, mag)
            
            
            # Optional: Dynamic scaling
            # self.ax.set_ylim(0, np.max(mag) * 1.2)
            
            return self.fft_line,
        except queue.Empty:
            return self.fft_line

    def recive_chain(self):
        print("Radio: starts recive chain thread")
        data = np.zeros(int(read_config_parameter("adalm_pluto", "rx_buffer_size"))) #old data, used to look for preamble
        new_data = np.zeros(int(read_config_parameter("adalm_pluto", "rx_buffer_size")))
        while not self.stop:
            data = new_data
            new_data = rx_filter(self.get_rx_package())
            peaks = self.preamble.detector(data, new_data) 
            if len(peaks) > 0:
                self.rx_package_counter += 1
            try:
                self._fft_queue.put_nowait(new_data)
                None
            except:
                continue
        print("Radio: stops recive chain thread")

    def get_rx_package(self):
        return self.__rx_queue.get()

    def send_tx_package(self, data):
        package = tx_filter(modulator(self.preamble.add_preamble(data)))
        self.__tx_queue.put(package)
        self.tx_package_counter += 1

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
                self._sdr.tx(tx_data*(2**14))
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

        print("Radio: transmitted packages {}, recived packages {}".format(self.tx_package_counter, self.rx_package_counter))

        del self._sdr
    
    def __del__(self):
        if self.stop == False:
            self.stop_radio()



if __name__ == "__main__":
    print("started program")
    radio = Radio()
    #radio.enable_fft_plot()
    radio.preamble.enable_correlation_plot()

    package_size = int(read_config_parameter("general", "package_size"))
    data = np.random.randint(0,2,package_size)

    try:
        while True:
            if radio.preamble.calibrated == True: #no point in sending before calibration is finished
                radio.send_tx_package(data)
                print(f"\r transmitted packages {radio.tx_package_counter}, recived packages {radio.rx_package_counter}", end="")
            plt.pause(1)
    except KeyboardInterrupt:
        radio.stop_radio()
        del radio
        print("stoped program")



        





