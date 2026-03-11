
import scipy as sp
from config import read_config_parameter
from modulation import modulator
from filter import FILTERS
import numpy as np
import matplotlib.pyplot as plt
import queue

class PREAMBLE():
    def __init__(self):    
        self.correlation_treshold = float(read_config_parameter("preamble_detector", "correlation_treshold"))
        
        self.preamble = np.array(list(map(int, list(format(int(read_config_parameter("general", "preamble"), base=16), 'b'))))) #ikke tenkt på det, det funker

        sps_rx = int(read_config_parameter("filter", "sps_rx"))
        sps_tx = int(read_config_parameter("filter", "sps_tx"))
        span = int(read_config_parameter("filter", "span"))
        modulated_preamble = modulator(self.preamble)
        filters = FILTERS()
        self.reference_signal = filters.rx_filter(sp.signal.resample_poly(filters.tx_filter(modulated_preamble), up=sps_rx, down=sps_tx))
        del filters
        
        self.peak_to_start_of_signal = -np.size(self.reference_signal)+1 + sps_rx*span #don't ask, i do not know why it is not sps_rx*span/2

        self.old_data = np.zeros(int(read_config_parameter("adalm_pluto", "rx_buffer_size"))) #old data, used to look for preamble

        package_size = int(read_config_parameter("general", "package_size"))
        self.min_distance_between_peaks = package_size*sps_rx*2
        print("min distance between peaks: {}".format(self.min_distance_between_peaks))


        self.calibration_counter = 0 #ensures calibration before reporting any peaks. Is used to stabilise noise floor estimate
        self.calibrated = False

        #for plotting of correlation
        self.correlation_plot_queue = queue.Queue(maxsize=1) #Queue size of 1 to remove backlog
        self.ylim_plot = 0

    def detector(self, data, new_data):
        conc_data = np.concatenate((data, new_data[:-self.peak_to_start_of_signal])) #ensures that it handles preambles in between packages
        #data_power = np.sqrt(np.sum(np.pow(np.abs(data), 2)) * np.sum(np.pow(np.abs(self.reference_signal),2)))
        noise_floor = np.median(np.abs(conc_data))
        cross_cor = np.abs(sp.signal.correlate(conc_data, self.reference_signal, mode="valid"))
        
        treshold = self.correlation_treshold*noise_floor
        if self.calibration_counter < 10: #calibration of treshold going on
            self.calibration_counter += 1
            if self.calibration_counter == 10:
                self.calibrated = True
                print("PREAMBLE: treshold calibrated, starting package detection")
            return []
        peaks = sp.signal.find_peaks(cross_cor, height=treshold, distance = self.min_distance_between_peaks)[0]

        try:
            self.correlation_plot_queue.put_nowait((treshold, cross_cor, peaks))
        except:
            None

        return peaks
    
    def add_preamble(self, data):
        return np.concatenate((self.preamble, data))
    
    def enable_correlation_plot(self):
        self.corr_fig, self.ax = plt.subplots()
        self.ax.set_title("Correlation plot")
        
        self.corr_line,   = self.ax.plot([], [], label="Correlation")
        self.peak_markers, = self.ax.plot([], [], 'rx', label="Detected Peaks")
        self.thresh_line = self.ax.axhline(y=0, color='r', linestyle='--', label="Threshold")
        self.ax.legend()
        self.ax.set_ylim(0, 100) # Adjust based on your signal levels
        self.ax.set_xlim(-1, 1)

        from matplotlib.animation import FuncAnimation
        # interval=100 means the plot updates 10 times per second
        self.ani = FuncAnimation(self.corr_fig, self.update_correlation_plot, interval=0.5, cache_frame_data=False)
        plt.show(block=False) # block=False lets the script continue
    
    def update_correlation_plot(self, frame):
        try:
            # Check the queue for new SDR data
            treshold, data, peaks = self.correlation_plot_queue.get_nowait()
            x = np.linspace(-1, 1, len(data))

            self.corr_line.set_data(x, data)
            y_peak = np.zeros_like(x)
            x_peak = np.zeros_like(x)
            for i, peak in enumerate(peaks): 
                y_peak[i] = data[peak]
                x_peak[i] = x[peak]
            
            self.peak_markers.set_data(x_peak, y_peak)
            self.thresh_line.set_ydata([treshold, treshold])
            
            
            #Dynamic scaling
            #self.ylim_plot += (np.max(data) - self.ylim_plot)*0.1
            self.ylim_plot = 800
            self.ax.set_ylim(0, self.ylim_plot * 1.5)
            
            return self.corr_line, self.thresh_line, self.peak_markers
        except queue.Empty:
            return self.corr_line, self.thresh_line, self.peak_markers

