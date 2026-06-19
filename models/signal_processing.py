"""Signal processing functions for EMG data."""

import numpy as np
from scipy import signal


def process_signal(data: np.ndarray, mode: str, sampling_rate: float) -> np.ndarray:
    """Return the signal according to the selected mode."""
    if data is None or data.size == 0:
        raise ValueError("No signal data available.")

    mode = mode.lower()

    if mode == "original":
        return np.asarray(data, dtype=np.float64)

    if mode == "filtered":
        return bandpass_filter(data, sampling_rate)

    if mode == "rms":
        filtered = bandpass_filter(data, sampling_rate)
        return compute_rms(filtered, sampling_rate)

    raise ValueError(f"Invalid signal mode: {mode}")


def bandpass_filter(
    data: np.ndarray,
    sampling_rate: float,
    low_cut: float = 20.0,
    high_cut: float = 450.0,
    order: int = 4,
) -> np.ndarray:
    """Apply a Butterworth bandpass filter to one channel or all channels."""
    data = np.asarray(data, dtype=np.float64)

    nyquist = sampling_rate / 2

    if low_cut <= 0:
        raise ValueError("Low cutoff frequency must be greater than 0 Hz.")

    if high_cut >= nyquist:
        high_cut = nyquist * 0.95

    if low_cut >= high_cut:
        raise ValueError("Low cutoff frequency must be smaller than high cutoff frequency.")

    low = low_cut / nyquist
    high = high_cut / nyquist

    b, a = signal.butter(order, [low, high], btype="band")

    min_samples = max(len(a), len(b)) * 3
    if data.shape[-1] <= min_samples:
        return data

    return signal.filtfilt(b, a, data, axis=-1)


def compute_rms(
    data: np.ndarray,
    sampling_rate: float,
    window_ms: float = 100.0,
) -> np.ndarray:
    """Compute RMS using a moving 100 ms window."""
    data = np.asarray(data, dtype=np.float64)

    window_size = int((window_ms / 1000) * sampling_rate)

    if window_size < 1:
        raise ValueError("RMS window size is too small.")

    if data.shape[-1] < window_size:
        return data

    kernel = np.ones(window_size) / window_size
    squared = data ** 2

    if data.ndim == 1:
        mean_squared = np.convolve(squared, kernel, mode="same")
        return np.sqrt(mean_squared)

    rms_data = np.zeros_like(data)

    for channel_index in range(data.shape[0]):
        mean_squared = np.convolve(
            squared[channel_index],
            kernel,
            mode="same",
        )
        rms_data[channel_index] = np.sqrt(mean_squared)

    return rms_data