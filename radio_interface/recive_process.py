import numpy as np
import matplotlib.pyplot as plt

#for threading and multiprocessing
import multiprocessing
import queue
import signal

#custom modules
import modules.config as config
from modules.filter import FILTERS
from modules.modulation import demodulator
from modules.data_detector import PREAMBLE

#for data retrival
import data_logger


def recive_process_loop(rx_q, binary_q, stop_event):
    binary_q.cancel_join_thread()
    signal.signal(signal.SIGINT, signal.SIG_IGN) #ignores the keyboard interrupt
    print("RECIVE PROCESS: started")

    filter = FILTERS()
    preamble = PREAMBLE()

    while not stop_event.is_set():
        try:
            rx_data = rx_q.get(timeout=0.5)
        except queue.Empty:
            pass
    
    print("RECIVE PROCESS: stopped")

class RECIVE_PROCESS:
    def __init__(self, rx_q):
        self.binary_q = multiprocessing.Queue(maxsize=10)
        self.rx_q = rx_q
        self.stop_event = multiprocessing.Event()

        self.recive_process = multiprocessing.Process(target=recive_process_loop, args=(self.rx_q, self.binary_q, self.stop_event))
        self.recive_process.start()

    def stop(self):
        self.stop_event.set()
        self.recive_process.join()

    def __del__(self):
        if not self.stop_event.is_set():
            self.stop()

if __name__ == "__main__":
    data = data_logger.retrieve_data("data_logs/recived_data_1503_01.npz")
    print(data[0].shape)

    plt.plot(data[0])
    plt.show()

    """rx_q = multiprocessing.Queue(maxsize=10)
    recive_process = RECIVE_PROCESS(rx_q)

    recive_process.stop()"""