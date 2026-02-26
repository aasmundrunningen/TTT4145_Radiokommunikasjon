import numpy as np
from modules.config import read_config_parameter
import matplotlib.pyplot as plt

simulation = read_config_parameter("simulator", "simulation")

sps_rx = int(read_config_parameter("filter", "sps_rx"))
symbolrate = int(read_config_parameter("general", "symboles_per_second"))
fs = symbolrate*sps_rx



def downsampler(data):
    sps = int(read_config_parameter("filter", "sps_rx"))
    kp_freq_sync = float(read_config_parameter("downsampler", "kp_symbolsync"))
    ki_freq_sync = float(read_config_parameter("downsampler", "ki_symbolsync"))

    plot_eye = int(read_config_parameter("downsampler", "plot_eye"))
    plot_sampling_error = int(read_config_parameter("downsampler", "plot_sampling_error"))

    if simulation:
        #parameters for simulation purpose
        true_channel_delay = float(read_config_parameter("simulator", "channel_delay")) #normalized to symboltime
        sampling_error = [] #array for calculating sampling error relative to simulator
    
    
    down_sampled_data = []
    time = 0 #normalized to samplingtime, so 1 is one sample periode

    step = sps #Distance to move for next symbol

    integral = 0



    while time < len(data)-sps:
        y_curr = np.interp(time         , range(len(data)),data)
        y_mid  = np.interp(time - step/2, range(len(data)),data)
        y_prev = np.interp(time - step  , range(len(data)),data)
        e = np.real(y_mid)*(np.real(y_curr)-np.real(y_prev)) #Gardner timing error detector algorithm
        integral = integral + e
        step = sps - ki_freq_sync*integral - kp_freq_sync*e #pi controller for step movement
        time = time + step
        
        down_sampled_data.append(y_curr*10) #downsampling and digitalization, adds 10 to increase signal strength to 1 for ideal case
        
        if simulation:
            sampling_error.append((time - true_channel_delay*sps + sps/2)%sps - sps/2) #calculates the error in sampling time

        if plot_eye:
            plt.plot(np.interp(np.linspace(time-sps/2, time+sps/2, 5), range(len(data)), data))
    
    if plot_eye:
        plt.show()
    if plot_sampling_error:
        plt.plot(sampling_error)
        plt.title("sampling error")
        plt.show()
    return np.array(down_sampled_data)

def matched_filter_synchronization(data):
    pilot_code_symboltime = int(read_config_parameter("matched_filter_symbol_sync", "pilot_code"), base=16)
    sps_rx = int(read_config_parameter("filter", "sps_rx"))





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

