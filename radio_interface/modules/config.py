from types import SimpleNamespace

# --- General Settings ---
# preamble: length 28 hex optimal code from NASA 
# https://ntrs.nasa.gov/api/citations/19800017860/downloads/19800017860.pdf
general = SimpleNamespace(
    symboles_per_second = 80000, 
    preamble = 0xB30FDD4, 
    package_size = 228,
    modulation_scheme = "QPSK"
)

# --- ADALM Pluto Hardware ---
adalm_pluto = SimpleNamespace(
    ip = "ip:192.168.2.1", #ips is 192.168.2.1 and 192.168.3.1
    rx_recive_freq = 920e6,
    rx_lo_freq = 919.8e6, # Nyquist limit is 320kHz
    tx_lo_freq = 920e6,
    rx_gain = 0,          # Range: 0 to 74.5dB
    tx_gain = 0,          # Range: -90 to 0dB
    rx_buffer_size = 2**16, 
    max_freq_offset_ppm = 25
)

# --- Signal Processing Filters ---
filter = SimpleNamespace(
    path = "rrc_filter.ftr",
    tx_bandwidth = 20000,
    rx_bandwidth = 20000,
    beta = 0.7,
    span = 5,
    sps_tx = 8,
    sps_rx = 8
)

# --- Synchronization Blocks ---
downsampler = SimpleNamespace(
    kp_symbolsync = 0.1,
    ki_symbolsync = 0.0,
    plot_eye = True,
    plot_sampling_error = True,
    interpolation_rate = 10
)

freq_sync = SimpleNamespace(
    kp = 0.5,
    ki = 0.1,
    plot_error = True
)

course_freq_sync = SimpleNamespace(
    plot_freq_spectrum = False
)

preamble_detector = SimpleNamespace(
    correlation_treshold = 200 # Height over noise floor
)

# --- Simulation Parameters ---
simulator = SimpleNamespace(
    channel_delay = 10.5,
    phase_offsett = 0,
    frequency_accuracy_ppm = 0,
    simulation = True,
    noise_level = 0.0,
    data_points_in_package = 100,
    number_of_data_packages = 5,
    sending_factor = 0.1
)

# --- Audio / Source Coding ---
_fs = 16000
_frame_ms = 20

source_coder = SimpleNamespace(
    fs = _fs,
    channels = 1,
    frame_ms = _frame_ms,
    frame_samples = int(_fs * _frame_ms / 1000), # 320 @ 16kHz
    bitrate = 6000,
    block = int(_fs * _frame_ms / 1000)
)