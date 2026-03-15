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

#for data retrival
import data_logger



fig, ax = plt.subplots(2,2)

plot_line_0, =  ax[0][0].plot([], [])
plot_line_0_data = []


def update_frame(frame):
    plot_line_0.set_data(np.arange(np.size(plot_line_0_data)), plot_line_0_data)
    ax[0][0].set_ylim(0, 1)
    ax[0][0].set_xlim(0, np.size(plot_line_0_data))
    return plot_line_0


animation = FuncAnimation(fig, update_frame, interval=100, cache_frame_data=False) #intervall is time in ms between frames
plt.show(block=False)

#runs trough all data in the file
data = data_logger.retrieve_data("radio_interface/data_logs/recived_data_1503_01.npz")


filter = FILTERS()
preamble = PREAMBLE()

for i, recived_data in enumerate(data):
    print(f"\rreciving data {i}", end="", flush=True)
    
    plot_line_0_data = np.abs(np.real(recived_data)) #prints the recived real power 


    plt.pause(0.2) #lets the frame update


print("")
print(f"real max: {np.max(np.real(data))}, real min {np.min(np.real(data))} imag maks: {np.max(np.imag(data))} imag min {np.min(np.imag(data))}")    
