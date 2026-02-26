import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import queue #Brukes til å lage en FIFO, first in first out kø
import sounddevice as sd #Bruker for å ta imot lyd fra mikrofon og spille av. 
import adi
from config import read_config_parameter
from source_coder import source_encoder


#-------------------------------------------------------
#Adalm_Pluto konfigurasjon
sample_rate = read_config_parameter("adalm_pluto", "sample_rate") # Hz
center_freq = read_config_parameter("adalm_pluto", "center_freq") # Hz
tx_gain = read_config_parameter("adalm_pluto", "tx_gain") # Increase to increase tx power, valid range is -90 to 0 dB

sdr = adi.Pluto("ip:192.168.2.1")
sdr.sample_rate = int(sample_rate)

sdr.tx_rf_bandwidth = int(sample_rate) # filter cutoff, just set it to the same as sample rate
sdr.tx_lo = int(center_freq)
sdr.tx_hardwaregain_chan0 = tx_gain # Increase to increase tx power, valid range is -90 to 0 dB

#-------------------------------------------------------
#Konfigurering


fs = read_config_parameter("source_coder", "fs")      # sample rate. Settes til 48kHz som er standard for PCer ? Satt til 16000 på grunn av opus
channels = read_config_parameter("source_coder", "channels")        # Setter til 1 slik at vi sender mono lyd. Kan sette til 2 for å ta opp stereo. 
frame_ms = read_config_parameter("source_coder", "frame_ms")           # Opus-frames (typisk 20 ms)         
frame_samples = int(fs * frame_ms / 1000)  # 320 ved 16 kHz
bitrate = read_config_parameter("source_coder", "bitrate")         # 6 kb/s target
block = frame_samples # Hvor mange samples vi får per callback.


#--------------------------------------------------------

### QUEs

#DETTE BRUKES! 
#Dette er for å skille data som kommer inn, og data som skal ut! Lager en in-que, og en ut-que.
# #Gjør dette for å ikke kjøre FFT, printing osv i callback funksjonen. Vi legger heller samples i en kø, 
#for så å behandle dem i main loopen som er den "with sd.Stream"
in_que = queue.Queue(maxsize=100)
out_que = queue.Queue(maxsize=100)

#-------------------------------------------------------

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

    # Loopback: send input til in_que. 


    ## Sender data fra mikrofon til in_q
    try:
        in_que.put_nowait(indata.copy())
    except queue.Full:
        # hvis main-loop henger etter, dropper vi blokker (heller enn å stoppe audio)
        pass


    # spill av dekodet PCM fra out_q (hvis tilgjengelig)
    #try:
    #    decoded = out_que.get_nowait()
    #    outdata[:] = decoded
    #except queue.Empty:
    #    outdata.fill(0)

    # Legg en kopi i kø for plotting/visning
    #try:
    #    que.put_nowait(indata.copy())
    #except queue.Full:
    #    pass


#----------------------------------
#Dette er loopen! 
sdr.tx_cyclic_buffer = True # Enable cyclic buffers
print("Starter: snakk i mikrofonen. Ctrl+C for å stoppe.")

with sd.Stream(samplerate=fs, blocksize=block, dtype='int16',
               channels=channels, callback=callback):   #callback er da funksjonen som brukes for å håndtere lyden. 
    #bruker with for da starter en å ta opp lyd når en går inn i with, og en slutter å ta opp når en går ut av den. 
    try:
        while True:
            #------------------------------------
            #Tar inn data fra mikrofonen, og legger i in_que. Dette gjøres i callback funksjonen, som blir kalt av sounddevice hver gang det kommer inn en ny blokk med lyd.
            data = in_que.get()  # Blokkerer, frem til det finnes en block med lyd.

            #------------------------------------
            #Koder dataen, og legger i out_que. Dette gjøres i main loopen, for å ikke gjøre det i callback funksjonen, som skal være så rask som mulig.
            opus_bits = source_encoder(data)

            #-------------------------------------
            #Transmit data

            sdr.tx(data_to_be_transmitted) # start transmitting

            #------------------------------------



    except KeyboardInterrupt:   #Gjør at en kan stoppe med ctrl+C
        print("\nStoppet.")