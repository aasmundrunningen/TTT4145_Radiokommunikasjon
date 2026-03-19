import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import queue #Brukes til å lage en FIFO, first in first out kø
import numpy as np
import sounddevice as sd #Bruker for å ta imot lyd fra mikrofon og spille av. 
import matplotlib.pyplot as plt
from source_coder import SOURCE_CODER
import config
import sys

class SOUND:
    def __init__(self, in_q, out_q):
        self.fs = int(config.source_coder.fs)  # sample rate. Settes til 48kHz som er standard for PCer ? Satt til 16000 på grunn av opus
        self.channels = int(config.source_coder.channels)        # Setter til 1 slik at vi sender mono lyd. Kan sette til 2 for å ta opp stereo. 
        self.frame_ms = int(config.source_coder.frame_ms)         # Opus-frames (typisk 20 ms)
        self.frame_samples = int(self.fs * self.frame_ms / 1000)  # 320 ved 16 kHz
        self.bitrate = int(config.source_coder.bitrate)        # 6 kb/s target
        self.block = int(self.frame_samples) # Hvor mange samples vi får per callback.

        self.in_que = in_q
        self.out_que = out_q

    def callback_record(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        ## snder data fra mikrofon til in_que
        try:
            self.in_que.put_nowait(indata.copy())
        except queue.Full:
            pass

        
    def callback_play(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        ## snder data til høyttaler
        try:
            self.out_que.get_nowait(outdata.copy())
        
        except queue.Empty:
            pass

        # spill av dekodet PCM fra out_q (hvis tilgjengelig)
        try:
            decoded = self.out_que.get_nowait()
            outdata[:] = decoded
        except queue.Empty:
            outdata.fill(0)