import numpy as np
import scipy as sp
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
from modules.syncronisation import SYNCHRONIZATION

#for data retrival
import data_logger


#file overview
#1603_01 transmitting and reciving across Per's room
#1603_02 reciving without other adam connected, weird shit with visible LO at recive freq
#1503_01 transmitt recive acroos Åsmund's room


#for doing live drawing
plt.ion()#for doing updating plots
fig, ax = plt.subplots(3,3)
plot_lines = []
for j in range(3):
    plot_lines.append([])
    for i in range(3):
        line, = ax[j][i].plot([], [])
        plot_lines[j].append(line)

#runs trough all data in the file
data = data_logger.retrieve_data("radio_interface/data_logs/recived_data_1903_01_sound.npz")


filter = FILTERS()
preamble = PREAMBLE()
sync = SYNCHRONIZATION()
#sync.enable_constalation_plot()
#sync.enable_eye_plot()

RC_filt_data = np.zeros(config.adalm_pluto.rx_buffer_size)

recived_binary_data = []

for i, recived_data in enumerate(data):
    #print(f"\rreciving data {i}", end="", flush=True)
    
    #data handling of recived data
    bandpassed_data       = filter.rx_bandpass_filter(recived_data)
    course_freq_sync_data = sync.course_freq_sync(bandpassed_data)
    old_rc_filt_data      = RC_filt_data
    RC_filt_data          = filter.rx_filter(course_freq_sync_data)
    detected_start_of_packages        = preamble.detector(old_rc_filt_data, RC_filt_data)

    

    for sop in detected_start_of_packages:
        data_package = np.concatenate([old_rc_filt_data, RC_filt_data])[sop:sop + (config.general.package_size+1)*config.filter.sps_rx]
        downsampled_data = sync.timing_sync_power_selector(data_package)
        sync.pass_data_to_constalation_plot(downsampled_data)
        phase_synced_data = sync.data_driven_phase_sync(downsampled_data)
        binary_data = demodulator(phase_synced_data)
        #print(f"lenght of lists: phase_synced_data: {np.shape(phase_synced_data)}, downsampled_data: {np.size(downsampled_data)}, data_package: {np.size(data_package)}")
        
        binary_data_without_preamble, result_code = preamble.remove_preamble(binary_data)
        if result_code == 1:
            print("Success!! detected correct preamble")
        else:
            print("Nooooo! wrong preamble code")

        recived_binary_data.extend(binary_data_without_preamble)

        plot_lines[2][1].set_data(np.real(phase_synced_data), np.imag(phase_synced_data))
        plot_lines[2][1].set_marker(".")
        plot_lines[2][1].set_linestyle("None")
        ax[2][1].set_xlim(-1,1)
        ax[2][1].set_ylim(-1,1)


    #ploting
    data_size = np.size(recived_data)
    data_range = np.arange(np.size(recived_data))
    freq = np.fft.fftfreq(data_size, 1/(config.general.symboles_per_second*config.filter.sps_rx))*1e-3
    plot_lines[0][0].set_data(data_range, np.abs(np.real(recived_data))) #recived real power
    plot_lines[1][0].set_data(freq, 10*np.log10(np.abs(np.fft.fft(recived_data))))
    plot_lines[1][1].set_data(freq, 10*np.log10(np.abs(np.fft.fft(bandpassed_data))))
    plot_lines[1][2].set_data(freq, 10*np.log10(np.abs(np.fft.fft(course_freq_sync_data))))



    upsampled_data = sp.signal.resample_poly(bandpassed_data, 4, 1) #upsample to increase bandwidth and not get aliasing
    fft_up_4_times = 10*np.log10(np.abs(np.fft.fft(np.pow(upsampled_data,4))))
    freq_up = np.fft.fftfreq(data_size*4, 1/(4*config.general.symboles_per_second*config.filter.sps_rx))*1e-3
    plot_lines[2][0].set_data(freq_up, fft_up_4_times)
    ax[0][0].set_xlim(0, data_size)
    ax[0][0].set_ylim(0, 1)
    for i in range(3):
        ax[1][i].set_ylim(0, 30)
        ax[1][i].set_xlim(np.min(freq), np.max(freq))
        ax[2][0].set_ylim(-100, 30)
        ax[2][0].set_xlim(np.min(freq_up), np.max(freq_up))
    
    
    plt.draw()
    plt.pause(0.2) #lets the frame update

with open("radio_interface/data_logs/recived_binary_data.txt", "w") as file:
    string = ""
    string = string.join(np.array(recived_binary_data).astype(str))
    file.write(string)

print("")
print(f"real max: {np.max(np.real(data))}, real min {np.min(np.real(data))} imag maks: {np.max(np.imag(data))} imag min {np.min(np.imag(data))}")    
