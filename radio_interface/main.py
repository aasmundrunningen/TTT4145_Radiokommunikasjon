from hardware_process   import HARDWARE_COMMUNICATION
from transmitt_process  import TRANSMITT_PROCESS
from recive_process     import RECIVE_PROCESS

import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    try:
        print("Starting hardware process")
        hardware_process = HARDWARE_COMMUNICATION(ip="ip:192.168.2.1")
        tx_q = hardware_process.get_tx_queue()
        rx_q = hardware_process.get_rx_queue()
        rx_plot_q = hardware_process.get_rx_plot_q() #for ploting or storing raw data
        transmitt_process = TRANSMITT_PROCESS(tx_q=tx_q) #starts transmitt process and hook it up to transmitt queue on hardware communication
        recive_process    = RECIVE_PROCESS(rx_q=rx_q)
        bin_tx_q = transmitt_process.get_binary_q()
        bin_rx_q = recive_process.get_binary_q()

        while True:
            while not bin_rx_q.empty():
                bin_rx_q.get()
            bin_tx_q.put(np.random.randint(0,2, 100))
            plt.pause(0.1)

    except KeyboardInterrupt:
        pass

    finally:
        transmitt_process.stop()
        recive_process.stop()
        hardware_process.stop()