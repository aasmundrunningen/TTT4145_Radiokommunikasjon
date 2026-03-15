import multiprocessing
import numpy as np
import modules.config as config
import signal
import queue
from modules.filter import FILTERS
from modules.modulation import modulator
from modules.data_detector import PREAMBLE
import matplotlib.pyplot as plt


def transmitt_process_loop(binary_q, tx_q, stop_event):
    tx_q.cancel_join_thread() #stops queue from binding thread under stop
    signal.signal(signal.SIGINT, signal.SIG_IGN) #ignores the keyboard interrupt
    print("TRANSMITT PROCESS: started")
    
    filter = FILTERS()
    preamble = PREAMBLE()

    while not stop_event.is_set():
        try:
            data = binary_q.get(timeout=0.5)
            tx_data = filter.tx_filter(modulator(preamble.add_preamble(data)))
            try:
                tx_q.put(tx_data, timeout=1)
            except queue.Full:
                print("ERROR! TRANSMITT PROCESS: transmitt queue will not clear")

        except queue.Empty:
            pass
    print("TRANSMITT PROCESS: stops")

class TRANSMITT_PROCESS:
    def __init__(self, tx_q):
        self.binary_q = multiprocessing.Queue(maxsize=10)
        self.tx_q = tx_q
        self.stop_event = multiprocessing.Event()

        self.transmitt_process = multiprocessing.Process(target=transmitt_process_loop, args=(self.binary_q, self.tx_q, self.stop_event))
        self.transmitt_process.start()


    def stop(self):
        self.stop_event.set()
        self.transmitt_process.join()
    
    def __del__(self):
        if not self.stop_event.is_set():
            self.stop()

if __name__ == "__main__":
    tx_q = multiprocessing.Queue(maxsize=10)
    transmitt_process = TRANSMITT_PROCESS(tx_q)
    binary_data = np.random.randint(0,2,100)
    transmitt_process.binary_q.put(binary_data)
    print(f"binary data: {binary_data}")
    tx_data = tx_q.get()
    print(f"tx data: {tx_data}")
    plt.plot(tx_data)
    plt.title("Transmitt data")
    plt.show()
    transmitt_process.stop()
