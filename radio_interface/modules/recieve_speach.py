import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import queue #Brukes til å lage en FIFO, first in first out kø
import sounddevice as sd #Bruker for å ta imot lyd fra mikrofon og spille av. 
import adi
from radio_interface.config import read_config_parameter
from source_coder import source_decoder, filter


#-------------------------------------------------------
#Adalm_Pluto konfigurasjon
sample_rate = read_config_parameter("adalm_pluto", "sample_rate") # Hz
center_freq = read_config_parameter("adalm_pluto", "center_freq") # Hz
rx_gain = read_config_parameter("adalm_pluto", "rx_gain") # dB, increase to increase the receive gain, but be careful not to saturate the ADC

sdr = adi.Pluto("ip:192.168.2.1")
sdr.sample_rate = int(sample_rate)

sdr.rx_lo = int(center_freq)
sdr.rx_rf_bandwidth = int(sample_rate)
sdr.gain_control_mode_chan0 = 'manual'
sdr.rx_hardwaregain_chan0 = rx_gain # dB, increase to increase the receive gain, but be careful not to saturate the ADC

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

#Dette er bare første test.
#que = queue.Queue(maxsize=50)   #Lager en kø med FIFO. Altså at dataen som kommer først inn,   DET VAR 20
#blir først sendt ut. 

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
    try:
        decoded = out_que.get_nowait()
        outdata[:] = decoded
    except queue.Empty:
        outdata.fill(0)

    # Legg en kopi i kø for plotting/visning
    #try:
    #    que.put_nowait(indata.copy())
    #except queue.Full:
    #    pass


#----------------------------------
#Dette er loopen! 

print("Starter: snakk i mikrofonen. Ctrl+C for å stoppe.")


with sd.Stream(samplerate=fs, blocksize=block, dtype='int16',
            channels=channels, callback=callback):   #callback er da funksjonen som brukes for å håndtere lyden. 
    #bruker with for da starter en å ta opp lyd når en går inn i with, og en slutter å ta opp når en går ut av den. 
    try:
        while True:

            IQ_data = sdr.rx() #Dette er rå IQ data, som må behandles for å få ut lyd.


            data = source_decoder(opus_bits)

            #---------------------------------------
            #Filter for å fjerne støy. Dette er ikke nødvendig, men det gjør at det høres litt bedre ut.    

            pcm_data = filter(data)
            

            #------------------------------------
            #Send lyd til høyttaler
            try:
                out_que.put_nowait(pcm_data)
            except queue.Full:
                pass


    except KeyboardInterrupt:   #Gjør at en kan stoppe med ctrl+C
        print("\nStoppet.")