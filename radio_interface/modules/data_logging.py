import numpy as np
import os
import modules.config as config
import time

class HighSpeedLogger:
    def __init__(self, dtype=np.complex64):
        if config.general.run_from_file:
            self.filename = f"radio_interface/data_logs/raw_rx_data_{config.general.data_file_index}.raw"
            print(f"Running from file: {self.filename}")
            self.readback_init()

        if config.general.enable_logging:
            index = 0
            while True:
                self.filename = f"radio_interface/data_logs/raw_rx_data_{index:03d}.raw"
                if os.path.exists(self.filename):
                    index = index + 1
                else:
                    break
            self.dtype = dtype
            # Open in 'wb' (write binary) mode
            self._file = open(self.filename, 'wb')

        

    def log(self, data):
        """Call this in your hardware loop. Extremely fast."""
        if config.general.enable_logging:
            self._file.write(data.tobytes())

    def close(self):
        self._file.close()

    def readback_init(self , dtype=np.complex64):
        # Use memory mapping to read 'huge' files without crashing RAM
        self.readback_data = np.memmap(self.filename, dtype=dtype, mode='r')
        self.readback_index = 0
    
    def get_readback_data(self):
        chunk_size=config.adalm_pluto.rx_buffer_size
        if self.readback_index > self.readback_data.shape[0] - chunk_size:
            print("Readback finished, starting from begining")
            self.readback_index = 0
        
        data = self.readback_data[self.readback_index:self.readback_index+chunk_size]
        self.readback_index = self.readback_index + chunk_size
        time.sleep(0.01)
        return data    

# --- HOW TO USE ---
# sim = simulator_generator("capture.raw")
# for i in range(100):
#     chunk = next(sim)
#     # Push 'chunk' into your processing/plotting logic