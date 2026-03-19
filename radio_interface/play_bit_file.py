import os
import numpy as np
import sounddevice as sd
from modules.source_coder import SOURCE_CODER


base_dir = os.path.dirname(__file__)
input_filename = os.path.join(base_dir, "lydtest_bits.txt")

with open(input_filename, "r", encoding="utf-8") as f:
    bit_string = f.read().strip()


all_bits = np.array([int(bit) for bit in bit_string], dtype=np.uint8)

source_coder = SOURCE_CODER()
bits_per_frame = source_coder.encoded_bits_per_frame

print("Leste bitfil:", input_filename)
print("Totalt antall bits:", len(all_bits))
print("Bits per frame:", bits_per_frame)

decoded_frames = []

for start in range(0, len(all_bits), bits_per_frame):
    stop = start + bits_per_frame
    frame_bits = all_bits[start:stop]

    if len(frame_bits) < bits_per_frame:
        print("Ikke mange nok bits. Slutt her. Hopper over siste pakke")
        break

    decoded = source_coder.source_decoder(frame_bits)
    decoded_frames.append(decoded)

if not decoded_frames:
    raise ValueError("Ingenting ble dekodet")

decoded_audio = np.vstack(decoded_frames).astype(np.float32)


max_val = np.max(np.abs(decoded_audio))
if max_val > 0:
    decoded_audio = decoded_audio / max_val

print("Dekodet signal:", decoded_audio.shape)
print("Spiller av")

try:
    sd.play(decoded_audio, source_coder.fs)
    sd.wait()
    print("Ferdig med å spille av")
except Exception as e:
    print(f"Error {e}")