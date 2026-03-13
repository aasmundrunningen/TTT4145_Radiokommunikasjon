import numpy as np
from radio_interface.config import read_config_parameter
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.collections import LineCollection
import scipy as sp
from numba import njit
import queue

#for self test of the system
import modulation
import filter



simulation = read_config_parameter("simulator", "simulation")

sps_rx = int(read_config_parameter("filter", "sps_rx"))
symbolrate = int(read_config_parameter("general", "symboles_per_second"))
fs = symbolrate*sps_rx



sps = int(read_config_parameter("filter", "sps_rx"))
kp_downsampler = float(read_config_parameter("downsampler", "kp_symbolsync"))
ki_downsampler = float(read_config_parameter("downsampler", "ki_symbolsync"))
plot_eye = int(read_config_parameter("downsampler", "plot_eye"))
plot_sampling_error = int(read_config_parameter("downsampler", "plot_sampling_error"))
package_size = int(read_config_parameter("general", "package_size"))
downsampled_data = np.zeros(package_size, dtype=complex)
downsampler_interpolation_rate = int(read_config_parameter("downsampler", "interpolation_rate"))


plot_error_freq_sync = int(read_config_parameter("freq_sync", "plot_error"))
kp_freq_sync = float(read_config_parameter("freq_sync", "kp"))
ki_freq_sync = float(read_config_parameter("freq_sync", "ki"))
def freq_sync(data):
    #costas loop
    if plot_error_freq_sync:
        e2_array = np.zeros_like(data)
        true_phase_offsett = float(read_config_parameter("simulator", "phase_offsett"))
    e1_int = 0
    e2 = 0
    data_out = np.zeros_like(data)
    for i, d in enumerate(data):
        data_out[i] = d*np.exp(-1j*e2)
        e1 = np.real(data_out[i]) * np.imag(data_out[i])
        e1_int = e1_int + e1
        e2 = kp_freq_sync*e1 + ki_freq_sync*e1_int
        if plot_error_freq_sync:
            e2_array[i] = e2
    
    if plot_error_freq_sync:
        plt.plot(e2_array)
        plt.plot(np.zeros_like(e2_array)+true_phase_offsett)
        plt.show()

    return data_out


class SYNCHRONIZATION():
    def __init__(self):
        buffer_size = int(read_config_parameter("adalm_pluto", "rx_buffer_size"))
        symboles_per_second = float(read_config_parameter("general", "symboles_per_second"))
        self.sps_rx = int(read_config_parameter("filter", "sps_rx"))
        self.fs = symboles_per_second*self.sps_rx
        self.package_size = int(read_config_parameter("general", "package_size"))

        self.f_for_course_freq_sync = np.fft.fftfreq(buffer_size, d=1/self.fs) #np.linspace(-self.fs/2.0, self.fs/2.0, buffer_size)
        self.t_for_course_freq_sync = np.linspace(0, 1/self.fs * buffer_size, buffer_size)

        self.time_sync_ki = float(read_config_parameter("downsampler", "ki_symbolsync"))
        self.time_sync_kp = float(read_config_parameter("downsampler", "kp_symbolsync"))
        self.time_sync_sampling_steps_queue = queue.Queue(maxsize=1) #Used for plotting eye diagram
        self.time_sync_sampling_times_queue = queue.Queue(maxsize=1) #Used for plotting eye diagram
        self.time_sync_data_queue = queue.Queue(maxsize=1) ##Used for plotting eye diagram
        self.time_sync_outdata_queue = queue.Queue(maxsize=1) ##Used for plotting eye diagram

        self.constalation_data_queue = queue.Queue(maxsize=1) ##Used for plotting constalation

    def course_freq_sync(self, data):
        psd = np.abs(np.fft.fft(np.pow(data,4))) #to power of 4 to remove modulation for QPSK
        max_freq = self.f_for_course_freq_sync[np.argmax(psd)]
        data = data * np.exp(1j*2*np.pi*self.t_for_course_freq_sync*max_freq/2) #quarter of maxfreq due to squaring moving peak to 4*delta_f
        return data

    #@njit #precompiles this section to not have the for loop overhead
    def timing_sync_gardner(self, data):
        outdata_real = np.zeros(self.package_size)
        outdata_imag = np.zeros(self.package_size)
        outdata = np.zeros(self.package_size, dtype=complex)
        outdata[0] = data[0]
        step = self.sps_rx
        steps = np.zeros_like(outdata_real) #for plotting
        time = step
        times = np.zeros(self.package_size)
        times[0] = time
        data_times = range(len(data))
        integral = 0
        real_data = np.real(data)
        imag_data = np.imag(data)
        for i in range(1, self.package_size):
            [outdata_real[i], y_mid_real] = np.interp([time, time - step/2], data_times, real_data)
            [outdata_imag[i], y_mid_imag] = np.interp([time, time - step/2], data_times, imag_data)
            e = y_mid_real*(outdata_real[i] - outdata_real[i-1]) + y_mid_imag*(outdata_imag[i] - outdata_imag[i-1])
            integral += e
            step -= self.time_sync_kp*e + self.time_sync_ki*integral
            steps[i] = step
            time += step
            times[i] = time
        
        outdata = outdata_real + 1j*outdata_imag

        try:
            self.time_sync_sampling_steps_queue.put_nowait(steps)
            self.time_sync_sampling_times_queue.put_nowait(times)
            self.time_sync_data_queue.put_nowait(data)
            self.time_sync_outdata_queue.put_nowait(outdata)
        except: 
            pass

        return outdata

    def timing_sync_power_selector(self, data):
        power = np.zeros(self.sps_rx)
        for i in range(self.sps_rx):
            power[i] = np.sum(np.abs(data[i:i+package_size:self.sps_rx]))
        
        i = np.argmax(power)
        outdata = data[i:i+package_size:self.sps_rx]
        try:
            self.time_sync_sampling_steps_queue.put_nowait(np.zeros(np.size(outdata))+self.sps_rx)
            self.time_sync_sampling_times_queue.put_nowait(np.arange(np.size(outdata))*self.sps_rx + i)
            self.time_sync_data_queue.put_nowait(data)
            self.time_sync_outdata_queue.put_nowait(outdata)
        except queue.Full:
            pass
        return outdata
        
    def enable_eye_plot(self):
        self.eye_fig, [self.ax1, self.ax2, self.ax3] = plt.subplots(1,3)
        self.eye_line, = self.ax1.plot([], [])
        self.ax1.set_ylim(-2, 2) # Adjust based on your signal levels
        self.ax1.set_xlim(-self.sps_rx/2, self.sps_rx/2)

        self.eye_segments = LineCollection([], linewidths=0.5, alpha=0.5)
        self.ax1.add_collection(self.eye_segments)

        self.steps_line, = self.ax2.plot([], [])
        self.ax2.set_ylim(self.sps_rx*0.5, self.sps_rx*2) # Adjust based on your signal levels
        self.ax2.set_xlim(0, self.package_size)

        self.power_line, = self.ax3.plot([], [])
        self.ax3.set_ylim(0, 1) # Adjust based on your signal levels
        self.ax3.set_xlim(0, self.package_size)




        self.ani = FuncAnimation(self.eye_fig, self.update_eye_diagram, interval=1, cache_frame_data=False)
        plt.show(block=False) # block=False lets the script continue

    def update_eye_diagram(self, frame):
        try:
            # Check the queue for new SDR data
            N = 10
            data = self.time_sync_data_queue.get_nowait()
            steps = self.time_sync_sampling_steps_queue.get_nowait()
            times = self.time_sync_sampling_times_queue.get_nowait()
            outdata = self.time_sync_outdata_queue.get_nowait()

            data_times = range(len(data))
            interp_data = []
            x = np.linspace(-self.sps_rx/2, self.sps_rx/2, N)
            for i, step in enumerate(steps):
                y_segment = np.real(np.interp(np.linspace(times[i]-step/2, times[i]+step/2, N), data_times, data))
                interp_data.append(np.column_stack([x, y_segment]))
            
            self.eye_segments.set_segments(interp_data)


            
            self.steps_line.set_data(range(len(steps)), steps)
            self.ax2.set_xlim(0, len(steps))
            self.power_line.set_data(range(len(outdata)), np.abs(outdata))
            self.ax3.set_xlim(0, len(outdata))


            return self.eye_segments, self.steps_line, self.power_line
        

            
        except queue.Empty:
            return self.eye_segments, self.steps_line, self.power_line

    def enable_constalation_plot(self):
         # We don't start a thread here anymore!
        # Instead, we set up the figure and the animation.
        self.constalation_fig, self.ax = plt.subplots()
        self.constalation_line, = self.ax.plot([], [], ".")
        self.ax.set_ylim(-2,2) # Adjust based on your signal levels
        self.ax.set_xlim(-2, 2)

        from matplotlib.animation import FuncAnimation
        # interval=100 means the plot updates 10 times per second
        self.ani = FuncAnimation(self.constalation_fig, self.update_constalation_plot, interval=1, cache_frame_data=False)
        plt.show(block=False) # block=False lets the script continue


    def pass_data_to_constalation_plot(self, data):
        try:
                sync.constalation_data_queue.put_nowait(data)
        except queue.Full:
            pass

    def update_constalation_plot(self, frame):
        try:
            data = self.constalation_data_queue.get_nowait()
            self.constalation_line.set_data(np.real(data), np.imag(data))
        except queue.Empty:
            pass
    
        return self.constalation_line

    
if __name__ == "__main__":
    filter = filter.FILTERS()

    filter_remove = int(read_config_parameter("filter", "span"))*int(read_config_parameter("filter", "sps_rx"))
    
    plt.show()

    sync = SYNCHRONIZATION()
    
    #indata = np.concatenate([np.zeros(50), indata, np.zeros(50)]) #zeropad to empty tx filter
    
    sync.enable_eye_plot()
    #sync.enable_constalation_plot()

    try:
        while plt.fignum_exists(sync.eye_fig.number):
            package_size = int(read_config_parameter("general", "package_size"))
            indata = np.random.randint(0, 2, package_size*2)
            indata = modulation.modulator(indata)
            indata = filter.tx_filter(indata)
            indata = filter.rx_filter(indata)[filter_remove:-filter_remove] #removes start and end of filter    
            
            time_offsett = 1
            clock_speed_relation = 1.01 #fraction between recive and transmitt clock, 1 is equal clock speeds
            time_jitter = 0 #std of timing jitter
            sampling_times = np.linspace(time_offsett, time_offsett + clock_speed_relation*sync.sps_rx*package_size, package_size*sync.sps_rx) + np.random.normal(loc=0, scale=time_jitter, size = package_size*sync.sps_rx)
            sampled_data = np.interp(sampling_times, range(len(indata)), indata)
            
            time_synced_data = sync.timing_sync_power_selector(sampled_data)
            sync.pass_data_to_constalation_plot(time_synced_data)
            plt.pause(1.5)


    except KeyboardInterrupt:
        del filter
        del sync