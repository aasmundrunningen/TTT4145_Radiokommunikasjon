import numpy as np
from modules.config import read_config_parameter
import matplotlib.pyplot as plt

simulation = read_config_parameter("simulator", "simulation")

def downsampler(data):
    sps = int(read_config_parameter("filter", "sps_rx"))
    kp = float(read_config_parameter("downsampler", "kp_symbolsync"))
    ki = float(read_config_parameter("downsampler", "ki_symbolsync"))

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
        step = sps - ki*integral - kp*e #pi controller for step movement
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


def freq_sync(data):
    #costas loop
    plot_error = int(read_config_parameter("freq_sync", "plot_error"))
    if plot_error:
        e2_array = np.zeros_like(data)
        true_phase_offsett = float(read_config_parameter("simulator", "phase_offsett"))
    kp = float(read_config_parameter("freq_sync", "kp"))
    ki = float(read_config_parameter("freq_sync", "ki"))
    e1_int = 0
    e2 = 0
    data_out = np.zeros_like(data)
    for i, d in enumerate(data):
        data_out[i] = d*np.exp(-1j*e2)
        e1 = np.real(data_out[i]) * np.imag(data_out[i])
        e1_int = e1_int + e1
        e2 = kp*e1 + ki*e1_int
        if plot_error:
            e2_array[i] = e2
    
    if plot_error:
        plt.plot(e2_array)
        plt.plot(np.zeros_like(e2_array)+true_phase_offsett)
        plt.show()

    return data_out

def course_freq_sync(data):
    power_in_out_of_band = 0.05 # percentage of power outside of bandwidth 
    sps_rx = int(read_config_parameter("filter", "sps_rx"))
    symbolrate = int(read_config_parameter("general", "symboles_per_second"))
    
    time_per_sample = 1/(symbolrate*sps_rx)

    data_pds = np.pow(np.fft.fft(data), 2)
    cumulative_power = np.cumsum(data_pds)
    total_power = cumulative_power[-1]
    f_low = np.where(cumulative_power > cumulative_power[-1]*power_in_out_of_band)[0][0]
    f_high = np.where(cumulative_power > cumulative_power[-1]*(1-power_in_out_of_band))[0][0]
    center_frequency = f_high - f_low
    t = np.linspace(0, time_per_sample*np.size(data), np.size(data))
    data = data * np.exp(-1j*2*np.pi*center_frequency*t)
    return data
