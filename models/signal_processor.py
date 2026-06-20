"""Signal processing for offline inspection."""

import numpy as np
from scipy import signal


def compute_rms(data: np.ndarray, window_size: int = 200) -> np.ndarray:
    """
    Compute RMS with sliding window.
    
    Args:
        data: 1D signal array
        window_size: Number of samples per RMS window (200 = 0.1s at 2000 Hz)
    
    Returns:
        RMS-smoothed signal
    """
    data = np.asarray(data, dtype=np.float64)
    rms_values = []
    
    for i in range(0, len(data), window_size):
        window = data[i : i + window_size]
        if len(window) > 0:
            rms = np.sqrt(np.mean(window ** 2))
            rms_values.append(rms)
    
    # Expand RMS values back to original length
    rms_expanded = np.repeat(rms_values, window_size)[: len(data)]
    
    # Pad if needed
    if len(rms_expanded) < len(data):
        rms_expanded = np.pad(
            rms_expanded,
            (0, len(data) - len(rms_expanded)),
            mode="edge",
        )
    
    return rms_expanded


def apply_lowpass_filter(
    data: np.ndarray,
    cutoff_hz: float = 500,
    sampling_rate: float = 2000,
    order: int = 4,
) -> np.ndarray:
    """
    Apply Butterworth low-pass filter.
    
    Args:
        data: 1D signal array
        cutoff_hz: Cutoff frequency in Hz (default: 500)
        sampling_rate: Sampling rate in Hz (default: 2000)
        order: Filter order (default: 4)
    
    Returns:
        Filtered signal
    """
    data = np.asarray(data, dtype=np.float64)
    
    nyquist = sampling_rate / 2
    normalized_cutoff = cutoff_hz / nyquist
    
    b, a = signal.butter(order, normalized_cutoff, btype="low")
    filtered = signal.filtfilt(b, a, data)
    
    return filtered


def process_offline_signal(
    data: np.ndarray,
    mode: str,
) -> np.ndarray:
    """
    Apply signal processing mode to offline data.
    
    Args:
        data: 1D signal array
        mode: "Original", "RMS", or "Filtered"
    
    Returns:
        Processed signal
    
    Raises:
        ValueError: If mode is unknown
    """
    if mode == "Original":
        return np.asarray(data, dtype=np.float64)
    elif mode == "RMS":
        return compute_rms(data)
    elif mode == "Filtered":
        return apply_lowpass_filter(data)
    else:
        raise ValueError(f"Unknown signal mode: {mode}")
