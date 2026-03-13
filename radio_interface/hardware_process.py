import config
import adi
import time
import multiprocessing
import signal
import queue
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

#Hardware communication, must be seperate to make it work with how processes are spawned
def hardware_communication_loop(rx_q, tx_q, rx_plot_q, stop_event):
    rx_q.cancel_join_thread() #Ques sending to main program need to not hang, otherwise it causes issues
    rx_plot_q.cancel_join_thread()
    
    signal.signal(signal.SIGINT, signal.SIG_IGN) #ignores the keyboard interrupt
    print("HARDWARE COMMUNICATION LOOP: started process")
    
    sample_rate = config.general.symboles_per_second*config.filter.sps_rx
    print(f"Sampling rate {sample_rate} samples/s")
    print(f"TX lo: {int(config.adalm_pluto.tx_lo_freq)}")

    #setup of ADALM PLUTO
    sdr                             =  adi.Pluto(config.adalm_pluto.ip)
    sdr.sample_rate                 = sample_rate
    sdr.tx_lo                       = int(config.adalm_pluto.tx_lo_freq)
    sdr.tx_hardwaregain_chan0       = int(config.adalm_pluto.tx_gain)

    sdr.gain_control_mode_chan0     = "manual"
    sdr.rx_lo                       = int(config.adalm_pluto.rx_lo_freq)
    sdr.rx_rf_bandwidth             = int(sdr.sample_rate*0.8) #antialiasing
    sdr.rx_buffer_size              = int(config.adalm_pluto.rx_buffer_size)
    sdr.rx_hardwaregain_chan0       = int(config.adalm_pluto.rx_gain)


    time_requirment = config.adalm_pluto.rx_buffer_size / sample_rate
    print(f"HARDWARE COMMUNICATION LOOP: time_requirmenht: {time_requirment}")
    to_slow_loop_counter = 0
    last_timestamp = time.perf_counter()
    lost_rx_raw_data_packages = 0
    while not stop_event.is_set():
        #timing to check that the loop runs fast enough
        if time.perf_counter() - last_timestamp > time_requirment:
            to_slow_loop_counter += 1

        rx_data = sdr.rx()
        last_timestamp = time.perf_counter()

        try:
            rx_q.put_nowait(rx_data)
        except queue.Full:
            rx_q.get()
            rx_q.put_nowait(rx_data)
            lost_rx_raw_data_packages += 1
        
        try:
            rx_plot_q.put_nowait(rx_data)
        except queue.Full:
            pass

        try:
            tx_data = tx_q.get_nowait()
            sdr.tx(tx_data*(2**14)) #scales TX data
        except queue.Empty:
            pass
    

    del sdr
    print(f"HARDWARE COMMUNICATION LOOP: Lost adalm samplings: {to_slow_loop_counter}")
    print(f"HARDWARE COMMUNICATION LOOP: Lost rx rawdata packages: {lost_rx_raw_data_packages}")
    print("HARDWARE COMMUNICATION LOOP: stoped process")

#class for interacting with the SDR
class HARDWARE_COMMUNICATION(): 
    def __init__(self):
        self.rx_q = multiprocessing.Queue(maxsize=10)
        self.rx_plot_q = multiprocessing.Queue(maxsize=10) #for plotting of recived power
        self.tx_q = multiprocessing.Queue(maxsize=10)
        self.stop_event = multiprocessing.Event()
        
        self.hardware_process = multiprocessing.Process(target=hardware_communication_loop, args=(self.rx_q, self.tx_q, self.rx_plot_q, self.stop_event), daemon=True)
        self.hardware_process.start()

    def enable_rx_power_plot(self):
        self.rx_fig, self.rx_ax = plt.subplots()
        N = 100 #number of points
        self.rx_ax.set_xlim(0,N)
        self.rx_line, = self.rx_ax.plot([], [])
        self.rx_ax.set_xlabel("Time [packages]")
        self.rx_ax.set_ylabel("Recived power [dB]")
        self.rx_ax.set_title("Recived power")
        self.power = np.zeros(N)
        self.ani = FuncAnimation(self.rx_fig, self._update_rx_power_plot, cache_frame_data=False)
        plt.show(block=False) # block=False lets the script continue

    def _update_rx_power_plot(self, frame):
        try:
            while not self.rx_plot_q.empty():
                rx_data = self.rx_plot_q.get_nowait()
                pow = 10*np.log10(np.sum(np.pow(np.abs(rx_data), 2)))
                self.power = np.concatenate((self.power[1:], [pow]))
            x = np.arange(np.size(self.power))
            self.rx_line.set_data(x, self.power)
            self.rx_ax.set_ylim(0,100)
            return self.rx_line
        except queue.Empty:
            return self.rx_line

    def get_rx_queue(self):
        return self.rx_q
    
    def get_tx_queue(self):
        return self.tx_q

    def stop(self):
        self.stop_event.set()
        self.hardware_process.join()
    
    def __del__(self):
        if not self.stop_event.is_set():
            self.stop()


if __name__ == "__main__":
    try:
        print("Starting hardware process")
        hardware_process = HARDWARE_COMMUNICATION()
        rx_q = hardware_process.get_rx_queue()
        tx_q = hardware_process.get_tx_queue()
        hardware_process.enable_rx_power_plot()
        tx_data = np.random.random(10000)
        print("Starting while loop")
        while True:
                #print(rx_q.get())
                tx_q.put(tx_data)
                plt.pause(1)

    except KeyboardInterrupt:
        hardware_process.stop()
        del hardware_process

