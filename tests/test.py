import numpy as np
tx_data = ""
rx_data = ""



a = np.array([[12,3,5], [123,556,6]])
print(len(a))

"""
with open("radio_interface/data_logs/lydtest_bits.txt", "r") as tx_file:
    tx_data = tx_file.read()
with open("radio_interface/data_logs/recived_binary_data_5.txt", "r") as rx_file:
    rx_data = rx_file.read()



a = np.fromiter(tx_data, dtype=int)
b = np.fromiter(rx_data, dtype=int)

print(np.size(a))
print(np.size(b))

similarity = np.mean(a == b)
print(f"Similarity: {similarity * 100:.2f}%") # Output: 66.67%

"""
