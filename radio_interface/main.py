from hardware_process import HARDWARE_COMMUNICATION
from transmitt_process import TRANSMITT_PROCESS
import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    try:
        print("Starting hardware process")
        hardware_process1 = HARDWARE_COMMUNICATION(ip="ip:192.168.3.1")
        hardware_process2 = HARDWARE_COMMUNICATION(ip="ip:192.168.2.1")
        hardware_process1.enable_rx_power_plot()
        hardware_process2.enable_rx_power_plot()
        tx_q1 = hardware_process1.get_tx_queue()

        transmitt_process = TRANSMITT_PROCESS(tx_q=tx_q1) #starts transmitt process and hook it up to transmitt queue on hardware communication
        
        binary_tx_data = np.random.randint(0,2,1000)
        

        print("Starting while loop")
        while True:
                transmitt_process.binary_q.put(binary_tx_data)
                plt.pause(1)

    except KeyboardInterrupt:
        transmitt_process.stop()
        hardware_process1.stop()
        hardware_process2.stop()