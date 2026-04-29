import modules.config as config
import modules.data_logging as data_logging
import adi
import time
import multiprocessing
import signal
import queue
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

#Hardware communication, must be seperate to make it work with how processes are spawned
def hardware_communication_loop(ip, rx_q, tx_q, monitor_q, stop_event):
    rx_q.cancel_join_thread() #Ques sending to main program need to not hang, otherwise it causes issues
    monitor_q.cancel_join_thread()
    
    signal.signal(signal.SIGINT, signal.SIG_IGN) #ignores the keyboard interrupt
    print("HARDWARE PROCESS: started process")
    
    
    data_logger = data_logging.HighSpeedLogger()
    average_rx_power = 0
    sample_rate = config.general.symboles_per_second*config.filter.sps_rx

    transmitted_packages = 0

    #setup of ADALM PLUTO
    if not config.general.run_from_file:
        try:
            sdr                             =  adi.Pluto(ip)
        except Exception as e:
            if "No device found" in str(e):
                print(f"[ERROR]: HARDWARE PROCESS: sdr not found, {ip}")
                print(f"HARDWARE PROCESS: stops loop")
                return
            else:
                raise e
        sdr.sample_rate                 = sample_rate
        sdr.tx_lo                       = int(config.adalm_pluto.tx_lo_freq)
        sdr.tx_hardwaregain_chan0       = int(config.adalm_pluto.tx_gain)
        sdr.tx_cyclic_buffer = True

        sdr.gain_control_mode_chan0     = "manual"
        sdr.rx_lo                       = int(config.adalm_pluto.rx_lo_freq)
        sdr.rx_rf_bandwidth             = int(sdr.sample_rate*0.8) #antialiasing
        sdr.rx_buffer_size              = int(config.adalm_pluto.rx_buffer_size)
        sdr.rx_hardwaregain_chan0       = int(config.adalm_pluto.rx_gain)


    time_requirment = config.adalm_pluto.rx_buffer_size / sample_rate
    print(f"HARDWARE PROCESS: time_requirmenht: {time_requirment}")
    to_slow_loop_counter = 0
    last_timestamp = time.perf_counter()
    lost_rx_raw_data_packages = 0

    t = False
    while not stop_event.is_set():
        #timing to check that the loop runs fast enough
        if time.perf_counter() - last_timestamp > time_requirment:
            to_slow_loop_counter += 1

        rx_power = float(sdr._ctrl.find_channel('voltage0').attrs['rssi'].value.split()[0])
        average_rx_power = average_rx_power*0.99 + rx_power*0.01

        try:
            tx_data = tx_q.get_nowait()
            if not config.general.run_from_file:
                if not t:
                    sdr.tx(tx_data*(2**14)) #scales TX data
                    t = True
                transmitted_packages = transmitted_packages + 1
        except queue.Empty:
            pass

        
        if config.general.run_from_file:
            rx_data = data_logger.get_readback_data()
        else:
            rx_data = sdr.rx()/2048 #makes it normalized to +-1
            data_logger.log(rx_data.astype(np.complex64))

        last_timestamp = time.perf_counter()

        try:
            rx_q.put_nowait(rx_data)
        except queue.Full:
            rx_q.get()
            rx_q.put_nowait(rx_data)
            lost_rx_raw_data_packages += 1

        try:
            monitor_q.put_nowait(("rx_raw_data", rx_data))
            monitor_q.put_nowait(("rx_power", rx_power))
            monitor_q.put_nowait(("rx_average_power", average_rx_power))
            monitor_q.put_nowait(("transmitted pacakges", transmitted_packages))    
        except queue.Full:
            pass
        
    del sdr
    print(f"HARDWARE PROCESS: Lost adalm samplings: {to_slow_loop_counter}")
    print(f"HARDWARE PROCESS: Lost rx rawdata packages: {lost_rx_raw_data_packages}")
    print("HARDWARE PROCESS: stoped process")

#class for interacting with the SDR
class HARDWARE_COMMUNICATION(): 
    def __init__(self, ip=None, monitor_q=multiprocessing.Queue(maxsize=100)):
        if ip == None:
            ip = config.adalm_pluto.ip
        
        print(ip)

        self.rx_q = multiprocessing.Queue(maxsize=10)
        self.monitor_q = monitor_q #for plotting of recived power
        self.tx_q = multiprocessing.Queue(maxsize=10)
        self.stop_event = multiprocessing.Event()
        
        self.hardware_process = multiprocessing.Process(target=hardware_communication_loop, args=(ip, self.rx_q, self.tx_q, self.monitor_q, self.stop_event), daemon=True)
        self.hardware_process.start()

    def get_monitor_q(self):
        return self.monitor_q

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
        hardware_process = HARDWARE_COMMUNICATION(ip="ip:192.168.3.1")
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

