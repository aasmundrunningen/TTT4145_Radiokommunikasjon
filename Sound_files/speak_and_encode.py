import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import queue #Brukes til å lage en FIFO, first in first out kø
import numpy as np
import sounddevice as sd #Bruker for å ta imot lyd fra mikrofon og spille av. 
import matplotlib.pyplot as plt
import opuslib
import scipy.signal as sig
from source_coder import SOURCE_CODER


#-------------------------------------------------------
#Konfigurering


fs = 16000      # sample rate. Settes til 48kHz som er standard for PCer ? Satt til 16000 på grunn av opus
channels = 1        # Setter til 1 slik at vi sender mono lyd. Kan sette til 2 for å ta opp stereo. 
frame_ms = 20           # Opus-frames (typisk 20 ms)
frame_samples = int(fs * frame_ms / 1000)  # 320 ved 16 kHz
bitrate = 6000         # 6 kb/s target
block = frame_samples # Hvor mange samples vi får per callback.
error_rate = 0.05  # 1% error rate

#--------------------------------------------------------

in_que = queue.Queue(maxsize=100)
out_que = queue.Queue(maxsize=100)


#Kode funnet her: https://python-sounddevice.readthedocs.io/en/0.5.3/usage.html
def callback(indata, outdata, frames, time, status):
    if status:
        print(status)


    ## Sender data fra mikrofon til in_q
    try:
        in_que.put_nowait(indata.copy())
    except queue.Full:
        # hvis main-loop henger etter, dropper vi blokker (heller enn å stoppe audio)
        pass


    # spill av dekodet PCM fra out_q (hvis tilgjengelig)
    try:
        decoded = out_que.get_nowait()
        outdata[:] = decoded
    except queue.Empty:
        outdata.fill(0)


#----------------------------------
#Dette er loopen! 

source_coder = SOURCE_CODER()

print("Starter: snakk i mikrofonen. Ctrl+C for å stoppe.")

with sd.Stream(samplerate=fs, blocksize=block, dtype='int16',
               channels=channels, callback=callback):   #callback er da funksjonen som brukes for å håndtere lyden. 
    #bruker with for da starter en å ta opp lyd når en går inn i with, og en slutter å ta opp når en går ut av den. 
    try:
        while True:
            data = in_que.get()  # Blokkerer, frem til det finnes en block med lyd.
            
            encoded_data = source_coder.source_encoder(data)
            
            #-----------------------------------
            #Channel

            #Simulering av biterror using Poisson distribution
            #Forventet antall bitfeil i en frame på 160 samples ved 1% feilrate er 1.6, så vi bruker lambda=1 for å få en realistisk simulering.
            #poisson_error = np.random.poisson(1, len(data)) #Genererer et array med lengde 160, hvor hver verdi er antall bitfeil i den aktuelle biten. De fleste vil være 0, noen vil være 1, og veldig få vil være 2 eller mer.
            #error_mask = np.random.rand(len(data)) < (error_rate / 100)  # Lager en mask som bestemmer hvilke bits som faktisk blir feil, basert på error_rate. Dette er en array med True/False verdier, hvor True indikerer at biten skal feiles.
            #final_error_mask = (poisson_error > 0) & error_mask  # Kombinerer poisson_error og error_mask for å få en endelig mask som bestemmer hvilke bits som faktisk blir feil. Dette sikrer at vi får realistiske bitfeil basert på både Poisson-distribusjonen og den angitte feilraten.
            #opus_bits_noisy = np.bitwise_xor(data, final_error_mask.astype(np.uint8))  # Bruker XOR for å flippe de bits som skal feiles i opus_bits, basert på final_error_mask. Dette gir oss det endelige arrayet av bits som simulerer overføringen gjennom en støyende kanal.     

            #---------------------------------- Channel over


            decoded_data = source_coder.source_decoder(encoded_data)


            filtered_data = source_coder.filter(decoded_data)
            
            try:
                out_que.put_nowait(filtered_data)
            except queue.Full:
                pass


    except KeyboardInterrupt:   #Gjør at en kan stoppe med ctrl+C
        print("\nStoppet.")