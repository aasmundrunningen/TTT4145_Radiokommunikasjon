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
from source_coder import SOURCE_CODER



class SOUND:
    def __init__(self, in_q, out_q):
        self.fs = int(config.source_coder.fs)  # sample rate. Settes til 48kHz som er standard for PCer ? Satt til 16000 på grunn av opus
        self.channels = int(config.source_coder.channels)        # Setter til 1 slik at vi sender mono lyd. Kan sette til 2 for å ta opp stereo. 
        self.frame_ms = int(config.source_coder.frame_ms)         # Opus-frames (typisk 20 ms)
        self.frame_samples = int(self.fs * self.frame_ms / 1000)  # 320 ved 16 kHz
        self.bitrate = int(config.source_coder.bitrate)        # 6 kb/s target
        self.block = int(self.frame_samples) # Hvor mange samples vi får per callback.
        
        self.source_coder = SOURCE_CODER()

        self.in_que = in_q
        self.out_que = out_q

    def callback_record(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        ## snder data fra mikrofon til in_que
        if self.in_que is None:
            return
        
        try:
            self.in_que.put_nowait(self.source_coder.source_encoder(indata.copy()))

        except queue.Full:
            pass


    def callback_play(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)

        # spill av dekodet PCM fra out_q (hvis tilgjengelig)
        try:
            
            encoded_data = self.out_que.get_nowait()
            decoded_data = self.source_coder.source_decoder(encoded_data)
            outdata[:] = decoded_data
        except queue.Empty:
            outdata.fill(0)

    def record(self):
        self.record_audio = sd.InputStream(samplerate=self.fs, blocksize = self.block, dtype='int16', channels=self.channels, callback=self.callback_record)
        self.record_audio.start()


    def play(self):
        self.play_sound = sd.OutputStream(samplerate=self.fs, blocksize = self.block, dtype='int16', channels=self.channels, callback=self.callback_play)
        self.play_sound.start()

    def stop_record(self):
        if self.input_stream is not None:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None

    def stop_play(self):
        if self.output_stream is not None:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None

    def stop_all(self):
        self.stop_record()
        self.stop_play()



if __name__ == "__main__":
    #Dette er slik vi setter opp for å recorde lyd fra mikrofon, for så å sende videre. Yiha. 
    if False:
        print('Started recording')
        tx_que = queue.Queue(maxsize=100)
        rx_que = queue.Queue(maxsize=100)
        sound = SOUND(in_q=tx_que, out_q=rx_que)
        sound.record()

        try:
            while True:
                data = tx_que.get()

                print(data)
                #Dette er her vi putter inn data for å kjøre

        except KeyboardInterrupt:
            sound.stop_all()

    #Dette er slik vi setter opp for å lytte. Altså må mottaker siden. 
    if True:
        print('Started playing')
        tx_que = queue.Queue(maxsize=100)
        rx_que = queue.Queue(maxsize=100)
        sound = SOUND(in_q=tx_que,out_q=rx_que)
        sound.play()
        
        try:
            while True:
                decoded_signal = 0 #Dette skal være det dekodede signalet som vi putter inn i out_que for å spille av! 
                rx_que.put(decoded_signal)

        except KeyboardInterrupt:
            sound.stop_all()





