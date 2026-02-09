import numpy as np
import matplotlib.pyplot as plt

def rrc_filter(beta, span, sps):
    """
    beta: roll-off factor
    span: filter length in symbols
    sps: samples per symbol
    """
    T = 1
    N = span * sps
    t = np.arange(-N/2, N/2 + 1) / sps

    h = np.zeros_like(t)

    for i, ti in enumerate(t):
        if ti == 0:
            h[i] = 1 - beta + 4*beta/np.pi
        elif abs(ti) == T/(4*beta):
            h[i] = (beta/np.sqrt(2)) * (
                (1 + 2/np.pi) * np.sin(np.pi/(4*beta)) +
                (1 - 2/np.pi) * np.cos(np.pi/(4*beta))
            )
        else:
            num = (np.sin(np.pi*ti*(1-beta)/T) +
                   4*beta*ti/T *
                   np.cos(np.pi*ti*(1+beta)/T))
            den = np.pi*ti*(1-(4*beta*ti/T)**2)/T
            h[i] = num / den

    return h

# Example
h = rrc_filter(beta=0.35, span=8, sps=8)

# Frequency response
H = np.fft.fftshift(np.fft.fft(h))
f = np.linspace(-0.5, 0.5, len(H))

plt.figure()
plt.plot(h)
plt.title("RRC impulse response")

plt.figure()
plt.plot(f, np.abs(H))
plt.title("Frequency response")
plt.show()
