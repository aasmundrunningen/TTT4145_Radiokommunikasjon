from hardware_process import HARDWARE_COMMUNICATION
from transmitt_process import TRANSMITT_PROCESS
import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    try:
        print("Starting hardware process")
        #hardware_process1 = HARDWARE_COMMUNICATION(ip="ip:192.168.3.1")
        hardware_process2 = HARDWARE_COMMUNICATION(ip="ip:192.168.2.1")
        #hardware_process1.enable_rx_power_plot()
        #hardware_process2.enable_rx_power_plot()
        tx_q1 = hardware_process2.get_tx_queue()

        transmitt_process = TRANSMITT_PROCESS(tx_q=tx_q1) #starts transmitt process and hook it up to transmitt queue on hardware communication
        
        with open("radio_interface/data_logs/lydtest_bits.txt", "r") as file:
            binary_audio_data = file.read()
            print(f"binary data size {np.size(binary_audio_data)}")
            data_packages = []
            for i in range(np.size(binary_audio_data)//120):
                 data_packages.append(binary_audio_data[i*120:(i+1)*120])
        
        plt.pause(2)
        input("Write start to start transmitting")
        print(np.shape(data_packages))
        for binary_tx_data in data_packages:
                transmitt_process.binary_q.put(binary_tx_data)
                plt.pause(0.02)
        print("Stopped transmitting!")
        transmitt_process.stop()
        hardware_process2.stop()

    except KeyboardInterrupt:
        transmitt_process.stop()
        #hardware_process1.stop()
        hardware_process2.stop()