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
def hardware_communication_loop(ip, rx_q, rx_feedback_q, tx_q, monitor_q, stop_event, master):
    rx_q.cancel_join_thread() #Ques sending to main program need to not hang, otherwise it causes issues
    monitor_q.cancel_join_thread()
    rx_feedback_q.cancel_join_thread()
    
    signal.signal(signal.SIGINT, signal.SIG_IGN) #ignores the keyboard interrupt
    print("HARDWARE COMMUNICATION LOOP: started process")
    print(f"HARDWARE COMMUNICATION LOOP: ip address {ip}")
    
    
    data_logger = data_logging.HighSpeedLogger()
    average_rx_power = 0
    sample_rate = config.general.symboles_per_second*config.filter.sps_rx
    print(f"Sampling rate {sample_rate} samples/s")
    print(f"TX lo: {int(config.adalm_pluto.tx_lo_freq)}")

    transmitted_packages = 0

    #setup of ADALM PLUTO
    if not config.general.run_from_file:
        try:
            sdr                             =  adi.Pluto(ip)
        except Exception as e:
            if "No device found" in str(e):
                print(f"[ERROR]: HARDWARE COMMUNICATION LOOP: sdr not found, {ip}")
                print(f"HARDWARE COMMUNICATION LOOP: stops loop")
                return
            else:
                raise e
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
    last_recive_package_timestamp = None
    
    lost_recive_window = 0
    start_point = time.perf_counter()
    rx_power = 0
    slave_recive_lock = False
    last_slave_recive_lock = False
    next_start = time.perf_counter()
    while not stop_event.is_set():
        if time.perf_counter() > next_start + config.TDMA.time_periode:
            print(time.perf_counter() - next_start + config.TDMA.time_periode)
        #calculating new start time
        next_start = start_point + np.ceil((time.perf_counter() - start_point)/config.TDMA.time_periode)*config.TDMA.time_periode
        #Transmittion
        while time.perf_counter() < next_start: #busy wait for transmitt window
            pass
        #check if allowed to transmitt, either master or slave with a recive the last second
        if master or slave_recive_lock:
            try:
                tx_data = tx_q.get_nowait()
                if not config.general.run_from_file:
                    sdr.tx(tx_data*(2**14)) #scales TX data
                    
                    #busy waiting for transmittion to finish
                    t = time.perf_counter() + len(tx_data) / sdr.sample_rate
                    while t > time.perf_counter():
                        pass
                    
                    transmitted_packages = transmitted_packages + 1
            except queue.Empty:
                pass              
        #Reciving
        while time.perf_counter() < next_start + config.TDMA.time_tx + config.TDMA.time_guard: #waiting for recive window
            pass
        if config.general.run_from_file:
            rx_data = data_logger.get_readback_data()
        else:
            sdr.rx()#removes old data
            rx_data = sdr.rx() #makes it normalized to +-1
            #data_logger.log(rx_data.astype(np.complex64))
        try:
            rx_q.put_nowait((rx_data, last_timestamp))
        except queue.Full:
            rx_q.get()
            rx_q.put_nowait((rx_data, last_timestamp))
            lost_rx_raw_data_packages += 1
        rx_power = np.sum(np.abs(rx_data[-10:]))

        #other stuff, doing while in guard interval


        #estimation of slave start point
        last_slave_recive_lock = slave_recive_lock
        if not master: 
            try:
                t = last_recive_package_timestamp
                last_recive_package_timestamp = rx_feedback_q.get_nowait()
                slave_recive_lock = True
                start_point = last_recive_package_timestamp + config.TDMA.time_guard+config.TDMA.time_tx+0.001 #offsetting slave start half of time from master
            except queue.Empty:
                if last_recive_package_timestamp == None or (time.perf_counter() - last_recive_package_timestamp > 1):
                    slave_recive_lock = False
                    start_point = start_point - np.random.rand()*0.001 #randomly moves start point to search for package if no sync has been made
                    #ensuring transmitt queue does not fill up
                    try:
                        tx_q.get_nowait()
                    except queue.Empty:
                        pass
        #---------------Monitoring--------------------------
        #rx_power = float(sdr._ctrl.find_channel('voltage0').attrs['rssi'].value.split()[0])
        #average_rx_power = average_rx_power*0.99 + rx_power*0.01
        
        try:
            #monitor_q.put_nowait(("rx_raw_data", rx_data)) #probably to slow
            monitor_q.put_nowait(("rx_power", rx_power))
            #monitor_q.put_nowait(("rx_average_power", average_rx_power))
            monitor_q.put_nowait(("transmitted pacakges", transmitted_packages))
        except queue.Full:
            pass

    

    del sdr
    print(f"HARDWARE COMMUNICATION LOOP: Lost adalm samplings: {to_slow_loop_counter}")
    print(f"HARDWARE COMMUNICATION LOOP: Lost rx rawdata packages: {lost_rx_raw_data_packages}")
    print("HARDWARE COMMUNICATION LOOP: stoped process")

#class for interacting with the SDR
class HARDWARE_COMMUNICATION(): 
    def __init__(self, ip=None, monitor_q=multiprocessing.Queue(maxsize=100), master=True):
        if ip == None:
            ip = config.adalm_pluto.ip
        
        print(ip)

        self.rx_q = multiprocessing.Queue(maxsize=10)
        self.monitor_q = monitor_q #for plotting of recived power
        self.tx_q = multiprocessing.Queue(maxsize=10)
        self.stop_event = multiprocessing.Event()
        self.rx_feedback_q = multiprocessing.Queue(maxsize=1)
        
        self.hardware_process = multiprocessing.Process(target=hardware_communication_loop, args=(ip, self.rx_q, self.rx_feedback_q, self.tx_q, self.monitor_q, self.stop_event, master), daemon=True)
        self.hardware_process.start()

    def get_monitor_q(self):
        return self.monitor_q

    def get_rx_queue(self):
        return self.rx_q
    
    def get_rx_feedback_queue(self):
        return self.rx_feedback_q

    
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

