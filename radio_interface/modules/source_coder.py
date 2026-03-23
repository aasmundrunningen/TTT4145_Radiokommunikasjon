import numpy as np
import opuslib
import scipy.signal as sig
import config as config


class SOURCE_CODER:
    def __init__(self):
        self.fs = int(config.source_coder.fs)              
        self.channels = int(config.source_coder.channels)   
        self.frame_ms = int(config.source_coder.frame_ms)  
        self.frame_samples = int(self.fs * self.frame_ms / 1000)
        self.bitrate = int(config.source_coder.bitrate)  

        self.lowpass_filter = sig.butter(4, 0.45, btype='low', output='sos')
        self.highpass_filter = sig.butter(4, 0.01, btype='high', output='sos')

        self.enc = opuslib.Encoder(self.fs, self.channels, opuslib.APPLICATION_AUDIO)
        self.enc.bitrate = self.bitrate

        self.dec = opuslib.Decoder(self.fs, self.channels)

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

        x = data[:, 0]

        if np.issubdtype(x.dtype, np.floating):
            x = np.clip(x, -1.0, 1.0)
            x = (x * 32767.0).astype(np.int16)
        else:
            x = x.astype(np.int16)

        x_bytes = x.tobytes()

        encoded = self.enc.encode(x_bytes, self.frame_samples)

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
