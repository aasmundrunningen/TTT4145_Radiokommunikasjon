import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

#for threading and multiprocessing
import multiprocessing
import queue
import signal

#custom modules
import modules.config as config
from modules.filter import FILTERS
from modules.modulation import demodulator
from modules.data_detector import PREAMBLE
from modules.syncronisation import SYNCHRONIZATION

#for data retrival
import data_logger


def recive_process_loop(rx_q, binary_q, stop_event):
    binary_q.cancel_join_thread()
    rx_q.cancel_join_thread()
    signal.signal(signal.SIGINT, signal.SIG_IGN) #ignores the keyboard interrupt
    print("RECIVE PROCESS: started")

    filter = FILTERS()
    preamble = PREAMBLE()
    sync = SYNCHRONIZATION()

    number_of_recived_packages = 0
    number_of_false_preamble   = 0

    RC_filt_data = np.zeros(config.adalm_pluto.rx_buffer_size)

    while not stop_event.is_set():
        try:
            rx_data = rx_q.get(timeout=0.5)
            #data handling of recived data
            bandpassed_data                 = filter.rx_bandpass_filter(rx_data)
            course_freq_sync_data           = sync.course_freq_sync(bandpassed_data)
            old_rc_filt_data                = RC_filt_data
            RC_filt_data                    = filter.rx_filter(course_freq_sync_data)
            detected_start_of_packages      = preamble.detector(old_rc_filt_data, RC_filt_data)

            
            #data handling on detected packages
            for sop in detected_start_of_packages:
                data_package                = np.concatenate([old_rc_filt_data, RC_filt_data])[sop:sop + (config.general.package_size//2)*config.filter.sps_rx]
                downsampled_data            = sync.timing_sync_power_selector(data_package)
                phase_synced_data           = sync.data_driven_phase_sync(downsampled_data)
                binary_data_with_preamble   = demodulator(phase_synced_data)
                binary_data, result_code    = preamble.remove_preamble(binary_data_with_preamble)
                if result_code == 1: #correct preamble detected
                    number_of_recived_packages += 1
                    try:
                        binary_q.put(binary_data, timeout=0.1)
                    except queue.Full:
                        print("RECIVER PROCESS: binary que full, discarded old data")
                        binary_q.get()
                        binary_q.put(binary_data)
                else:
                    number_of_false_preamble += 1
        except queue.Empty:
            pass
    
    print(f"RECIVE PROCESS: correct detected preambles {number_of_recived_packages}")
    print(f"RECIVE PROCESS: false detected preambles {number_of_false_preamble}")
    print("RECIVE PROCESS: stopped")

class RECIVE_PROCESS:
    def __init__(self, rx_q):
        self.binary_q = multiprocessing.Queue(maxsize=10)
        self.rx_q = rx_q
        self.stop_event = multiprocessing.Event()

        self.recive_process = multiprocessing.Process(target=recive_process_loop, args=(self.rx_q, self.binary_q, self.stop_event))
        self.recive_process.start()
    
    def get_binary_q(self):
        return self.binary_q

    def stop(self):
        print("Trying to stop recive process")
        self.stop_event.set()
        self.recive_process.join()

    def __del__(self):
        if not self.stop_event.is_set():
            self.stop()

if __name__ == "__main__":
    try: 
        fig, ax = plt.subplots(4)

        rx_q = multiprocessing.Queue(10)
        rx_q.cancel_join_thread()
        recive_process = RECIVE_PROCESS(rx_q)
        bin_q = recive_process.get_binary_q()
        binary_data = []
        data = data_logger.retrieve_data("radio_interface/data_logs/recived_data_1903_01_sound.npz")
        i = 0
        while i < len(data):
            try:
                rx_q.put_nowait(data[i])
                i += 1
            except queue.Full:
                pass

            while not bin_q.empty():
                binary_data.extend(bin_q.get())

            
        with open("radio_interface/data_logs/recived_binary_data_6.txt", "w") as file:
            binary_string = ""
            binary_string = binary_string.join(np.array(binary_data).astype(str))
            file.write(binary_string)
    except KeyboardInterrupt:
        pass
    
    finally:
        recive_process.stop()
