import numpy as np
import opuslib
import scipy.signal as sig
import config as config


import numpy as np
import opuslib
import scipy.signal as sig
import config as config


class SOURCE_CODER:
    def __init__(self):
        self.fs = int(config.source_coder.fs)               # f.eks. 16000
        self.channels = int(config.source_coder.channels)   # 1
        self.frame_ms = int(config.source_coder.frame_ms)   # 20
        self.frame_samples = int(self.fs * self.frame_ms / 1000)
        self.bitrate = int(config.source_coder.bitrate)     # f.eks. 6000

        self.lowpass_filter = sig.butter(4, 0.45, btype='low', output='sos')
        self.highpass_filter = sig.butter(4, 0.01, btype='high', output='sos')

        self.enc = opuslib.Encoder(self.fs, self.channels, opuslib.APPLICATION_AUDIO)
        self.enc.bitrate = self.bitrate

        self.dec = opuslib.Decoder(self.fs, self.channels)

        # Fast pakkelengde i bytes for lagring/overføring i ditt oppsett
        self.encoded_bytes_per_frame = int(self.bitrate * self.frame_ms / 1000 / 8)
        self.encoded_bits_per_frame = self.encoded_bytes_per_frame * 8

    def source_encoder(self, data):
        """
        data: numpy-array med shape (frame_samples, channels)
        returnerer: numpy-array av bits (uint8), fast lengde
        """
        data = np.asarray(data)

        if data.ndim != 2:
            raise ValueError(f"data må ha shape (samples, channels), fikk {data.shape}")

        if data.shape[0] != self.frame_samples:
            raise ValueError(
                f"Forventet {self.frame_samples} samples per frame, fikk {data.shape[0]}"
            )

        if data.shape[1] < 1:
            raise ValueError("Fant ingen kanaler i input-data")

        # Bruk første kanal (mono)
        x = data[:, 0]

        # Konverter til PCM16
        if np.issubdtype(x.dtype, np.floating):
            x = np.clip(x, -1.0, 1.0)
            x = (x * 32767.0).astype(np.int16)
        else:
            x = x.astype(np.int16)

        x_bytes = x.tobytes()

        # Opus encode
        encoded = self.enc.encode(x_bytes, self.frame_samples)

        # Tving til fast lengde
        encoder_bytes = bytearray(encoded)

        if len(encoder_bytes) < self.encoded_bytes_per_frame:
            encoder_bytes.extend([0] * (self.encoded_bytes_per_frame - len(encoder_bytes)))
        else:
            encoder_bytes = encoder_bytes[:self.encoded_bytes_per_frame]

        opus_bits = np.unpackbits(np.frombuffer(encoder_bytes, dtype=np.uint8))
        return opus_bits.astype(np.uint8)

    def source_decoder(self, opus_bits):

        opus_bits = np.asarray(opus_bits, dtype=np.uint8)

        if opus_bits.ndim != 1:
            raise ValueError("opus_bits må være en 1D-array")

        if len(opus_bits) != self.encoded_bits_per_frame:
            raise ValueError(
                f"Forventet {self.encoded_bits_per_frame} bits, fikk {len(opus_bits)}"
            )

        opus_bytes = np.packbits(opus_bits).tobytes()

        decoded_bytes = self.dec.decode(opus_bytes, self.frame_samples)
        decoded = np.frombuffer(decoded_bytes, dtype=np.int16).reshape(-1, 1)

        decoded = self.filter(decoded.astype(np.float32))
        return decoded

    def filter(self, decoded):
        decoded = sig.sosfilt(self.lowpass_filter, decoded, axis=0)
        decoded = sig.sosfilt(self.highpass_filter, decoded, axis=0)
        return decoded

#-------------------------------------------------------
#Konfigurering

"""
fs = read_config_parameter("source_coder", "fs")
channels = read_config_parameter("source_coder", "channels")
frame_ms = read_config_parameter("source_coder", "frame_ms")
frame_samples = read_config_parameter("source_coder", "frame_samples")
bitrate = read_config_parameter("source_coder", "bitrate")
block = read_config_parameter("source_coder", "block")
"""

#-------------------------------------------------------
#Lavpass og høypass filter for å fjerne støy fra sluttsignalet. 

#lowpass_filter = sig.butter(4, 0.45, btype='low', output='sos')
#highpass_filter = sig.butter(4, 0.01, btype='high', output='sos')

#----------------------------------------------------------------------


#Lager encoder
#enc = opuslib.Encoder(fs, channels, opuslib.APPLICATION_AUDIO)
#enc.bitrate = bitrate  # 6 kbps
#enc.opus_encoder_ctl(enc, enc.OPUS_SET_VBR(1),enc.OPUS_SET_PACKET_LOSS_PERC(5))  # Disables VBR, for å få fast bitrate. Dette gjør at hver frame har samme størrelse, som gjør det enklere å håndtere på mottakersiden.

#--------------------------------------------------------

#Lager decoder
#dec = opuslib.Decoder(fs, channels)


#----------------------------------------------------------------------
"""
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
"""

#----------------------------------------------------------------------

"""
def source_decoder(opus_bits):
    opus_bytes = np.packbits(opus_bits).tobytes()

    # Decode tilbake til PCM16 bytes
    decoder = dec.decode(opus_bytes, frame_samples)
    decoded = np.frombuffer(decoder, dtype=np.int16).reshape(-1, 1)
    return decoded
"""

#------------------------------------------------------------------------------

"""
def filter(decoded):
    decoded = sig.sosfilt(lowpass_filter, decoded, axis=0)
    decoded = sig.sosfilt(highpass_filter, decoded, axis=0)
    return decoded


"""








