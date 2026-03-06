import adi
import numpy as np

sdr = adi.Pluto("ip:192.168.2.1")
sdr.tx_lo = int(914999998)
#sdr.gain_control_mode_chan0 = "manual"
sdr.tx_hardwaregain_chan0 = 0
sdr.sample_rate = int(2399999)


data = np.random.randint(-1, 1, 1024)
print("start program")
try:
    while True:
        sdr.tx(data*(2**14))
except KeyboardInterrupt:
    del sdr
print("stops program")


