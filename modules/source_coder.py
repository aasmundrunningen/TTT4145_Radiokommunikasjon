import os
os.environ["SD_ENABLE_ASIO"] = "1"   #Dette må skrives før en importerer sounddevice. Denne linjen
#gjør at sounddevice bruker ASIO på windows, som gjør at det blir "kanskje litt" mindre latency. 
import numpy as np
import opuslib
import scipy.signal as sig
from config import read_config_parameter

#-------------------------------------------------------
#Konfigurering


fs = read_config_parameter("source_coder", "fs")
channels = read_config_parameter("source_coder", "channels")
frame_ms = read_config_parameter("source_coder", "frame_ms")
frame_samples = read_config_parameter("source_coder", "frame_samples")
bitrate = read_config_parameter("source_coder", "bitrate")
block = read_config_parameter("source_coder", "block")


#-------------------------------------------------------
#Lavpass og høypass filter for å fjerne støy fra sluttsignalet. 

lowpass_filter = sig.butter(4, 0.45, btype='low', output='sos')
highpass_filter = sig.butter(4, 0.01, btype='high', output='sos')

#----------------------------------------------------------------------


#Lager encoder
enc = opuslib.Encoder(fs, channels, opuslib.APPLICATION_AUDIO)
enc.bitrate = bitrate  # 6 kbps
#enc.opus_encoder_ctl(enc, enc.OPUS_SET_VBR(1),enc.OPUS_SET_PACKET_LOSS_PERC(5))  # Disables VBR, for å få fast bitrate. Dette gjør at hver frame har samme størrelse, som gjør det enklere å håndtere på mottakersiden.

#--------------------------------------------------------

#Lager decoder
dec = opuslib.Decoder(fs, channels)


#----------------------------------------------------------------------

def source_encoder(data):
    x = data[:, 0]  #Dette er på formen (240,1). Samples x channel. Lagrer lyd, så det er en array med lengde 1024
    # int16 til bytes 

    x_bytes = x.tobytes()
    encoder = enc.encode(x_bytes, frame_samples) #Her endres den! 

    # Sørger for fast lengde
    expected_encoded_len = int(bitrate * frame_ms / 1000 / 8) 

    # Gjør om til byte
    encoder_bytes = bytearray(encoder)

    #Legger på 0, om ikke nok bytes, eller kutter av om det er for mye. Dette gjør at vi alltid sender like mange bytes, som gjør det enklere å håndtere på mottakersiden.
    if len(encoder_bytes) < expected_encoded_len:
        encoder_bytes.extend([0] * (expected_encoded_len - len(encoder_bytes)))
    else:
        encoder_bytes = encoder_bytes[:expected_encoded_len]
    
    #Gjør om til bits
    opus_bits = np.unpackbits(np.frombuffer(encoder_bytes, dtype=np.uint8)) ###DETTO ER DATAEN VI SKAL SENDE
    #Denne har 160 bits i lengde

    return opus_bits


#----------------------------------------------------------------------


def source_decoder(opus_bits):
    opus_bytes = np.packbits(opus_bits).tobytes()

    # Decode tilbake til PCM16 bytes
    decoder = dec.decode(opus_bytes, frame_samples)
    decoded = np.frombuffer(decoder, dtype=np.int16).reshape(-1, 1)
    return decoded


#------------------------------------------------------------------------------

def filter(decoded):
    decoded = sig.sosfilt(lowpass_filter, decoded, axis=0)
    decoded = sig.sosfilt(highpass_filter, decoded, axis=0)
    return decoded








