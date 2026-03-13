import adi
from radio_interface.config import read_config_parameter
import threading
import multiprocessing
import queue
import numpy as np
import matplotlib.pyplot as plt
from modulation import demodulator, modulator
from filter import FILTERS
from data_detector import PREAMBLE
from syncronisation import SYNCHRONIZATION
import signal
import time

#Hardware communication, must be seperate to make it work with how processes are spawned
def hardware_communication_loop(log_queue, rx_q, tx_q, stop_event):

    signal.signal(signal.SIGINT, signal.SIG_IGN) #makes it ignore keyboard interrupt

    log_queue.put("HARDWARE COMMUNICATION LOOP: started process")
    symboles_per_second = int(read_config_parameter("general", "symboles_per_second"))
    sps_rx = int(read_config_parameter("filter", "sps_rx"))
    sample_rate = symboles_per_second*sps_rx

    #setup of ADALM PLUTO
    _sdr = adi.Pluto(read_config_parameter("adalm_pluto", "ip"))
    _sdr.sample_rate = sample_rate
    _sdr.tx_lo = int(float(read_config_parameter("adalm_pluto", "tx_lo_freq"))) #int(float(read_config_parameter("adalm_pluto", "tx_lo_freq")))
    _sdr.tx_hardwaregain_chan0       = int(read_config_parameter("adalm_pluto", "tx_gain"))

    _sdr.gain_control_mode_chan0     = "manual"
    _sdr.rx_lo = int(float(read_config_parameter("adalm_pluto", "rx_lo_freq")))
    _sdr.rx_rf_bandwidth             = int(_sdr.sample_rate*0.8) #antialiasing
    _sdr.rx_buffer_size              = int(float(read_config_parameter("adalm_pluto", "rx_buffer_size")))
    _sdr.rx_hardwaregain_chan0       = int(read_config_parameter("adalm_pluto", "rx_gain"))


    time_requirment = int(float(read_config_parameter("adalm_pluto", "rx_buffer_size"))) / sample_rate
    log_queue.put(f"HARDWARE COMMUNICATION LOOP: time_requirmenht: {time_requirment}")
    to_slow_loop_counter = 0
    last_timestamp = time.perf_counter()
    lost_rx_raw_data_packages = 0

    while not stop_event.is_set():
        #timing to check that the loop runs fast enough
        if time.perf_counter() - last_timestamp > time_requirment:
            to_slow_loop_counter += 1

        rx_data = _sdr.rx()
        last_timestamp = time.perf_counter()

        try:
            rx_q.put_nowait(rx_data)
        except multiprocessing.queues.Full:
            rx_q.get()
            rx_q.put_nowait(rx_data)
            lost_rx_raw_data_packages += 1
        
        try:
            tx_data = tx_q.get_nowait()
            _sdr.tx(tx_data)
        except multiprocessing.queues.Empty:
            pass
    

    del _sdr
    log_queue.put(f"HARDWARE COMMUNICATION LOOP: Lost adalm samplings: {to_slow_loop_counter}")
    log_queue.put(f"HARDWARE COMMUNICATION LOOP: Lost rx rawdata packages: {lost_rx_raw_data_packages}")
    log_queue.put("HARDWARE COMMUNICATION LOOP: stoped process")

class Radio():
    def __init__(self):
        self.package_size = int(read_config_parameter("general", "package_size"))
        self.symboles_per_second = int(read_config_parameter("general", "symboles_per_second"))
        self.sps_rx = int(read_config_parameter("filter", "sps_rx"))
        self.sample_rate = self.symboles_per_second*self.sps_rx
        
        self._fft_queue = queue.Queue(maxsize=1) # Limit queue size to prevent huge lag
        
        self.tx_package_counter = 0 #counts number of transmitted packages
        self.rx_package_counter = 0 #counts number of detected packages


        self.preamble = PREAMBLE()
        self.synchronization = SYNCHRONIZATION()
        self.filters = FILTERS()

        #sets up the process with hardware communication
        self._rx_queue = multiprocessing.Queue(maxsize=10)
        self._tx_queue = multiprocessing.Queue(maxsize=10) #must be multiprocessing quese as this run in a seperate process
        self._hardware_communication_loop_log_queue = multiprocessing.Queue(maxsize=10)
        self.stop_event = multiprocessing.Event() #used for stopping the hardware process
        self.hardware_communication_process = multiprocessing.Process(target=hardware_communication_loop, args=(self._hardware_communication_loop_log_queue, self._rx_queue, self._tx_queue, self.stop_event), daemon=True)
        self.hardware_communication_process.start()

        #start threads for tx and rx, deamon tells the thread to kil if this thread dies
        self.recive_chain_thread = threading.Thread(target=self.recive_chain, daemon=True)
        self.recive_chain_thread.start()

    def flash_hardware_communication_log_queue(self):
        while True:
            try:
                print(self._hardware_communication_loop_log_queue.get_nowait())
            except:
                break

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
        while not self.stop_event.is_set():
            
            data = new_data
            new_data = self.get_rx_package()
            new_data = self.filters.rx_bandpass_filter(new_data)
            try:
                self._fft_queue.put_nowait(new_data)
            except:
                pass

            new_data = self.synchronization.course_freq_sync(new_data)
            new_data = self.filters.rx_filter(new_data)
            
            peaks = self.preamble.detector(data, new_data) 
            for peak in peaks:
                self.rx_package_counter += 1
                data_package = np.concatenate([data, new_data])[peak:peak + (self.package_size+1)*self.sps_rx] #essentialy add one data length to lett it adjust the spacing
                downsampled_data = self.synchronization.timing_sync_power_selector(data_package)
                self.synchronization.pass_data_to_constalation_plot(downsampled_data)

        print("Radio: stops recive chain thread")

    def get_rx_package(self):
        while not self.stop_event.is_set():
            try:
                return self._rx_queue.get(timeout=0.1)
            except queue.Empty:
                pass

    def send_tx_package(self, data):
        package = self.filters.tx_filter(modulator(self.preamble.add_preamble(data)))
        self._tx_queue.put(package)
        self.tx_package_counter += 1

    def stop_radio(self):
        print("Radio: shutting down")
        self.stop_event.set()
        self.hardware_communication_process.join() #waits to stop the hardware communication
        radio.flash_hardware_communication_log_queue()
        self.recive_chain_thread.join()

        print("Radio: transmitted packages {}, recived packages {}".format(self.tx_package_counter, self.rx_package_counter))
    
    def __del__(self):
        if not self.stop_event.is_set():
            self.stop_radio()



if __name__ == "__main__":
    print("started program")
    radio = Radio()
    time.sleep(0.1)
    radio.flash_hardware_communication_log_queue()

    #radio.enable_fft_plot()
    #radio.preamble.enable_correlation_plot()
    #radio.synchronization.enable_constalation_plot()
    radio.synchronization.enable_eye_plot()

    package_size = int(read_config_parameter("general", "package_size"))
    data = np.random.randint(0,2,package_size)
    
    try:
        while True: 
            if radio.preamble.calibrated == True: #no point in sending before calibration is finished
                radio.send_tx_package(data)
                print(f"\r transmitted packages {radio.tx_package_counter}, recived packages {radio.rx_package_counter}", end="")
            plt.pause(1)
            radio.flash_hardware_communication_log_queue()
    except KeyboardInterrupt:
        radio.stop_radio()
        del radio
        print("stoped program")



        





