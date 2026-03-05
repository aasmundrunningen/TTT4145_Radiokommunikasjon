import numpy as np
from config import read_config_parameter
import matplotlib.pyplot as plt
import scipy as sp

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

def downsampler(data):
    if data is None: #no data in package
        return None

    if simulation:
        #parameters for simulation purpose
        steps = []
        times = []

    integral = 0    
    data_interp = np.interp(np.linspace(0, np.size(data), np.size(data)*downsampler_interpolation_rate), range(np.size(data)), data)
    downsampled_data[0] = data_interp[0]
    step = sps*downsampler_interpolation_rate
    time = step #normalized to samplingtime, so 1 is one sample periode
    for i in range(1, package_size): #goes trough the number of datapoints expected
        y_mid  = data_interp[int(time - step/2)]
        downsampled_data[i] = data_interp[int(time)]
        
        e = np.real(y_mid)*(np.real(downsampled_data[i])-np.real(downsampled_data[i-1])) #Gardner timing error detector algorithm
        integral = integral + e
        step = sps*downsampler_interpolation_rate - ki_downsampler*integral - kp_downsampler*e #pi controller for step movement
        time = time + step
        
        steps.append(step)
        times.append(int(time))

        if plot_eye and i < 40:
            plt.plot(data_interp[int(time - step/2):int(time+step/2)])
    
    if plot_eye:
        plt.show()
    plt.plot(steps)
    plt.show()
    return downsampled_data


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



plot_course_freq_sync = int(read_config_parameter("course_freq_sync", "plot_freq_spectrum"))
def course_freq_sync(data):
    
    psd = np.abs(np.fft.fftshift(np.fft.fft(np.pow(data,4)))) #to power of 4 to remove modulation for QPSK
    f = np.linspace(-fs/2.0, fs/2.0, len(psd))
    t = np.linspace(0, 1/fs * np.size(data), np.size(data))
    max_freq = f[np.argmax(psd)]
    data = data * np.exp(-1j*2*np.pi*t*max_freq/4) #quarter of maxfreq due to squaring moving peak to 4*delta_f
    
    if plot_course_freq_sync:
        psd_corrected = np.fft.fftshift(np.fft.fft(np.pow(data,4))) #squared bpsk removes the modulation, only carrier ramains. Need to be cubed for qpsk
        plt.plot(f, np.abs(psd), label="Original PSD")
        plt.plot(f, np.abs(psd_corrected), label="Adjusted PSD")
        plt.xlabel("Frequency [Hz]")
        plt.ylabel("|PSD|")
        plt.legend()
        #plt.vlines(max_freq, 0, )
        plt.title("Power density spectrum of recived signal")
        plt.show()
    return data

