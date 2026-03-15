import numpy as np
from hardware_process import HARDWARE_COMMUNICATION
from transmitt_process import TRANSMITT_PROCESS
import matplotlib.pyplot as plt
import queue
import multiprocessing
import time

def log_data(filename, array_list):
    """
    Stores a list of numpy arrays to a file using numpy.savez.
    Args:
        filename (str): Path to the file where data will be stored.
        array_list (list of np.ndarray): List of numpy arrays to store.
    """
    np.savez(filename, *array_list)

def retrieve_data(filename):
    """
    Loads a list of numpy arrays from a file created by log_data.
    Args:
        filename (str): Path to the file to load data from.
    Returns:
        list of np.ndarray: List of numpy arrays retrieved from the file.
    """
    with np.load(filename) as data:
        return [data[key] for key in data.files]
    
#run main to log data
if __name__ == "__main__":
    path = "data_logs/recived_data_1503_02.npz"
    print("Starting hardware process")
    hardware_process1 = HARDWARE_COMMUNICATION(ip="ip:192.168.3.1")
    hardware_process2 = HARDWARE_COMMUNICATION(ip="ip:192.168.2.1")
    
    #hardware_process2.enable_rx_power_plot()
    tx_q1 = hardware_process1.get_tx_queue()
    rx_q2 = hardware_process2.get_rx_queue()
    transmitt_process = TRANSMITT_PROCESS(tx_q=tx_q1) #starts transmitt process and hook it up to transmitt queue on hardware communication
    
    binary_tx_data = np.random.randint(0,2,1000)

    recive_data = []
    N = 10 #number of packages to transmitt



    print("Starting while loop")
    i = 0

    time_between_transmitt = 1 #in seconds
    last_transmitt_time = 0

    while i < N:
            #tries to transmitt a sequence
            if last_transmitt_time + time_between_transmitt < time.perf_counter():
                try:
                    transmitt_process.binary_q.put_nowait(binary_tx_data)
                    i += 1
                    last_transmitt_time = time.perf_counter()
                except queue.Full:
                        pass
                
            #empties recive buffer 
            while True:
                try:
                    data = rx_q2.get_nowait()
                    recive_data.append(data)
                except queue.Empty:
                    break
                    
            #plt.pause(0.2)
    
    print("Finished transmitt and recive, storing data")
    log_data(path, recive_data)


    transmitt_process.stop()
    hardware_process1.stop()
    hardware_process2.stop()
    print("stops program")