import adi
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as sig



# Koble til pluto
sdr = adi.Pluto("ip:192.168.2.1")


# Config
sdr.sample_rate = int(20e6)      # 2 MSPS
sdr.rx_rf_bandwidth = int(20e6) #Båndbredde, 2MHz
sdr.rx_lo = int(2.4e9)           #Senterfrekvens,  2 GHz
sdr.gain_control_mode = "slow_attack"
sdr.rx_enabled_channels = [0]




#Motta samples
fs = int(sdr.sample_rate)
data = sdr.rx() 


#FFT
f, Pxx_den = sig.periodogram(data, fs)

Pxx_den = np.maximum(Pxx_den, 1e-20)
dc_idx = np.argmin(np.abs(f))   # bin nærmest 0 Hz
Pxx_den[dc_idx] = np.nan        # eller sett lik naboverdi


# Plot
plt.figure()

plt.plot(f, 10*np.log10(Pxx_den))
plt.xlabel("Frekvens (MHz)")
plt.ylabel("Effekt (dB)")
plt.title("Pluto RX Spektrum")
plt.grid()
plt.show()