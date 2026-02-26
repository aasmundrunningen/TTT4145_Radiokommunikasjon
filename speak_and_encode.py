import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import queue #Brukes til å lage en FIFO, first in first out kø
import numpy as np
import sounddevice as sd #Bruker for å ta imot lyd fra mikrofon og spille av. 
import matplotlib.pyplot as plt
import opuslib
import scipy.signal as sig



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
#Lavpass og høypass filter for å fjerne støy fra sluttsignalet. 

lowpass_filter = sig.butter(4, 0.45, btype='low', output='sos')
highpass_filter = sig.butter(4, 0.01, btype='high', output='sos')

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




#----------------------------------------------------------------------



#Lager encoder
enc = opuslib.Encoder(fs, channels, opuslib.APPLICATION_AUDIO)
enc.bitrate = bitrate  # 6 kbps
enc.opus_encoder_ctl(enc, enc.OPUS_SET_VBR(1),enc.OPUS_SET_PACKET_LOSS_PERC(5))  # Disables VBR, for å få fast bitrate. Dette gjør at hver frame har samme størrelse, som gjør det enklere å håndtere på mottakersiden.



#-----------------------------------


#Lager decoder
dec = opuslib.Decoder(fs, channels)


#----------------------------------
#Dette er loopen! 

print("Starter: snakk i mikrofonen. Ctrl+C for å stoppe.")

with sd.Stream(samplerate=fs, blocksize=block, dtype='int16',
               channels=channels, callback=callback):   #callback er da funksjonen som brukes for å håndtere lyden. 
    #bruker with for da starter en å ta opp lyd når en går inn i with, og en slutter å ta opp når en går ut av den. 
    try:
        while True:
            data = in_que.get()  # Blokkerer, frem til det finnes en block med lyd.
            x = data[:, 0]  #Dette er på formen (240,1). Samples x channel. Lagrer lyd, så det er en array med lengde 1024
            # int16 til bytes 
            x_bytes = x.tobytes()

            

            #----------------------------------------------------------
            #Encoder

            # Encode én opus-pakke (20ms)
            encoder = enc.encode(x_bytes, frame_samples) #Her endres den! 



            # Sørger for fast lengde
            expected_encoded_len = int(bitrate * frame_ms / 1000 / 8)  # Convert bps to bytes
            
            # Gjør om til byte
            encoder_bytes = bytearray(encoder)
            
            #Legger på 0, om ikke nok bytes, eller kutter av om det er for mye. Dette gjør at vi alltid sender like mange bytes, som gjør det enklere å håndtere på mottakersiden.
            if len(encoder_bytes) < expected_encoded_len:
                encoder_bytes.extend([0] * (expected_encoded_len - len(encoder_bytes)))
            else:
                encoder_bytes = encoder_bytes[:expected_encoded_len]

            #------------------------------------------------------


            #Her gjør vi om fra bits til bytes, og fra bytes til bits, for å teste

            opus_bits = np.unpackbits(np.frombuffer(encoder_bytes, dtype=np.uint8)) ###DETTO ER DATAEN VI SKAL SENDE
            #Denne har 160 bits i lengde



            #-----------------------------------
            #Channel

            #Simulering av biterror using Poisson distribution
            #Forventet antall bitfeil i en frame på 160 samples ved 1% feilrate er 1.6, så vi bruker lambda=1 for å få en realistisk simulering.
            poisson_error = np.random.poisson(1, len(opus_bits)) #Genererer et array med lengde 160, hvor hver verdi er antall bitfeil i den aktuelle biten. De fleste vil være 0, noen vil være 1, og veldig få vil være 2 eller mer.
            error_mask = np.random.rand(len(opus_bits)) < (error_rate / 100)  # Lager en mask som bestemmer hvilke bits som faktisk blir feil, basert på error_rate. Dette er en array med True/False verdier, hvor True indikerer at biten skal feiles.
            final_error_mask = (poisson_error > 0) & error_mask  # Kombinerer poisson_error og error_mask for å få en endelig mask som bestemmer hvilke bits som faktisk blir feil. Dette sikrer at vi får realistiske bitfeil basert på både Poisson-distribusjonen og den angitte feilraten.
            opus_bits_noisy = np.bitwise_xor(opus_bits, final_error_mask.astype(np.uint8))  # Bruker XOR for å flippe de bits som skal feiles i opus_bits, basert på final_error_mask. Dette gir oss det endelige arrayet av bits som simulerer overføringen gjennom en støyende kanal.     





            #---------------------------------------------------
            #Her er channel over, og vi gjør om til bytes igjen


            
            opus_bytes = np.packbits(opus_bits_noisy).tobytes()

            #print(len(opus_bytes))
            #print(len(opus_bits))


            #---------------------------------------

            # Decode tilbake til PCM16 bytes
            decoder = dec.decode(opus_bytes, frame_samples)
            decoded = np.frombuffer(decoder, dtype=np.int16).reshape(-1, 1)


            #---------------------------------------
            #Filter for å fjerne støy. Dette er ikke nødvendig, men det gjør at det høres litt bedre ut.    

            decoded = sig.sosfilt(lowpass_filter, decoded, axis=0)
            decoded = sig.sosfilt(highpass_filter, decoded, axis=0)
            
            #------------------------------------
            #Send lyd til høyttaler

            try:
                out_que.put_nowait(decoded)
            except queue.Full:
                pass


    except KeyboardInterrupt:   #Gjør at en kan stoppe med ctrl+C
        print("\nStoppet.")