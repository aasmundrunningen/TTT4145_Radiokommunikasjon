import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import queue #Brukes til å lage en FIFO, first in first out kø
import numpy as np
import sounddevice as sd #Bruker for å ta imot lyd fra mikrofon og spille av. 
import matplotlib.pyplot as plt

#-------------------------------------------------------
fs = 48000          # sample rate. Settes til 48kHz som er standard for PCer ? 
block = 1024        # Hvor mange samples vi får per callback. 
                    #1024 samples ved 48kHz = 1024/48000 = 0.0213s = 21ms 
channels = 1        # Setter til 1 slik at vi sender mono lyd. Kan sette til 2 for å ta opp stereo. 

que = queue.Queue(maxsize=20)   #Lager en kø med FIFO. Altså at dataen som kommer først inn, 
#blir først sendt ut. 
#Gjør dette for å ikke kjøre FFT, printing osv i callback funksjonen. Vi legger heller samples i en kø, 
#for så å behandle dem i main loopen. 


#--------------------------------------------------------

#Callback blir kalt på av sounddevice sd.Stream. Dette skjer hver gang en ny blokk 
# med input er klar, og output trenger data

#indata - Nympy array med input fra mic. 
#outdata - numpy array med output samples, som sender til høyttaler(eller radio?)
#frames - antall samples, ofte block
#time - tidsinfo, latency
#status - varsler om underflow/overflow
#Kode funnet her: https://python-sounddevice.readthedocs.io/en/0.5.3/usage.html
def callback(indata, outdata, frames, time, status):
    if status:
        print(status)

    # Loopback: send input rett ut til høyttaler. Så alt som skal sendes ut, er det samme som
    #kommer inn. Dette er dataen vi sender til radio? 
    outdata[:] = indata

    # Legg en kopi i kø for plotting/visning
    try:
        que.put_nowait(indata.copy())
    except queue.Full:
        pass

#-----------------------------------

print("Starter: snakk i mikrofonen. Ctrl+C for å stoppe.")

with sd.Stream(samplerate=fs, blocksize=block, dtype='int16',
               channels=channels, callback=callback):   #callback er da funksjonen som brukes for å håndtere lyden. 
    #bruker with for da starter en å ta opp lyd når en går inn i with, og en slutter å ta opp når en går ut av den. 
    try:
        while True:
            data = que.get()  # Blokkerer, frem til det finnes en block med lyd.
            x = data[:, 0]  #Dette er på formen (1024,1). Samples x channel. Lagrer lyd, så det er en array med lengde 1024

            # int16 til bytes 
            x_bytes = x.tobytes()
            # bytes til bits
            x_bits = np.unpackbits(np.frombuffer(x_bytes, dtype=np.uint8)) ###DETTE ER DATAEN VI SKAL SENDE
            
            #print("Antall bits:", len(x_bits))
            #print("Første 32 bits:", x_bits[:32])


    except KeyboardInterrupt:   #Gjør at en kan stoppe med ctrl+C
        print("\nStoppet.")