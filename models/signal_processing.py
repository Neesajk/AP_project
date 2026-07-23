"""Signal-processing functions for EMG data."""

from __future__ import annotations

import numpy as np
from scipy import signal


def _validate_data(data: np.ndarray) -> np.ndarray:
    """Convert signal data to float64 and validate its shape."""
    if data is None:
        raise ValueError("No signal data available.")

    data = np.asarray(data, dtype=np.float64)

    if data.ndim == 0 or data.size == 0:
        raise ValueError("No signal data available.")

    return data


def _empty_signal(data: np.ndarray) -> np.ndarray:
    """Return an empty signal while retaining channel dimensions."""
    return np.empty(data.shape[:-1] + (0,), dtype=np.float64)


def _design_bandpass_filter(
    sampling_rate: float,
    low_cut: float,
    high_cut: float,
    order: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Create Butterworth bandpass-filter coefficients."""
    if sampling_rate <= 0:
        raise ValueError("Sampling rate must be greater than 0 Hz.")

    if low_cut <= 0:
        raise ValueError("Low cutoff frequency must be greater than 0 Hz.")

    nyquist = sampling_rate / 2.0

    if high_cut >= nyquist:
        high_cut = nyquist * 0.95

    if low_cut >= high_cut:
        raise ValueError(
            "Low cutoff frequency must be smaller than high cutoff frequency."
        )

    low = low_cut / nyquist
    high = high_cut / nyquist

    return signal.butter(order, [low, high], btype="band")


def process_signal(
    data: np.ndarray,
    mode: str,
    sampling_rate: float,
) -> np.ndarray:
    """
    Process a complete signal for offline review.

    This function uses zero-phase filtering and should not be used repeatedly
    on a growing live-data buffer.
    """
    data = _validate_data(data)
    mode = mode.lower()

    if mode == "original":
        return data.copy()

    filtered = bandpass_filter(data, sampling_rate)

    if mode == "filtered":
        return filtered

    if mode == "rms":
        return compute_rms(filtered, sampling_rate)

    raise ValueError(f"Invalid signal mode: {mode}")


def bandpass_filter(
    data: np.ndarray,
    sampling_rate: float,
    low_cut: float = 20.0,
    high_cut: float = 450.0,
    order: int = 4,
) -> np.ndarray:
    """
    Apply zero-phase bandpass filtering to a complete offline signal.

    If the signal is too short for filtfilt, an empty array is returned rather
    than incorrectly displaying the unfiltered signal as filtered.
    """
    data = _validate_data(data)

    b, a = _design_bandpass_filter(
        sampling_rate=sampling_rate,
        low_cut=low_cut,
        high_cut=high_cut,
        order=order,
    )

    pad_length = 3 * max(len(a), len(b))

    if data.shape[-1] <= pad_length:
        return _empty_signal(data)

    return signal.filtfilt(b, a, data, axis=-1)


def compute_rms(
    data: np.ndarray,
    sampling_rate: float,
    window_ms: float = 100.0,
) -> np.ndarray:
    """
    Compute RMS using a moving window.

    For short offline signals, all currently available samples are used.
    Therefore, the result remains a valid non-negative RMS signal.
    """
    data = _validate_data(data)

    window_size = int(round((window_ms / 1000.0) * sampling_rate))

    if window_size < 1:
        raise ValueError("RMS window size is too small.")

    sample_count = data.shape[-1]
    effective_window = min(window_size, sample_count)

    kernel = np.ones(effective_window, dtype=np.float64) / effective_window
    squared = np.square(data)

    rms_data = np.empty_like(data)

    if data.ndim == 1:
        mean_squared = np.convolve(squared, kernel, mode="same")
        return np.sqrt(np.maximum(mean_squared, 0.0))

    for channel_index in range(data.shape[0]):
        mean_squared = np.convolve(
            squared[channel_index],
            kernel,
            mode="same",
        )
        rms_data[channel_index] = np.sqrt(
            np.maximum(mean_squared, 0.0)
        )

    return rms_data


class LiveSignalProcessor:
    """
    Stateful processor for incoming live EMG chunks.

    Each incoming chunk must be passed to this processor exactly once.
    Filter and RMS states are retained between calls.
    """

    def __init__(
        self,
        sampling_rate: float,
        low_cut: float = 20.0,
        high_cut: float = 450.0,
        order: int = 4,
        rms_window_ms: float = 100.0,
    ) -> None:
        self.sampling_rate = sampling_rate

        self._b, self._a = _design_bandpass_filter(
            sampling_rate=sampling_rate,
            low_cut=low_cut,
            high_cut=high_cut,
            order=order,
        )

        self._filter_warmup_samples = 3 * max(
            len(self._a),
            len(self._b),
        )

        self._rms_window_size = int(
            round((rms_window_ms / 1000.0) * sampling_rate)
        )

        if self._rms_window_size < 1:
            raise ValueError("RMS window size is too small.")

        self._rms_kernel = (
            np.ones(self._rms_window_size, dtype=np.float64)
            / self._rms_window_size
        )

        self.reset()

    def reset(self) -> None:
        """Reset filter and RMS states, for example after reconnecting."""
        self._filter_state: np.ndarray | None = None
        self._rms_state: np.ndarray | None = None
        self._channel_shape: tuple[int, ...] | None = None

        self._filter_samples_seen = 0
        self._rms_samples_seen = 0

    def process_chunk(
        self,
        data: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """
        Process one newly received live-data chunk.

        Returns original, filtered and RMS data. Filtered and RMS outputs may
        initially be empty while their required history is being collected.
        """
        data = _validate_data(data)

        self._ensure_states(data)

        filtered_chunk, self._filter_state = signal.lfilter(
            self._b,
            self._a,
            data,
            axis=-1,
            zi=self._filter_state,
        )

        filtered_ready = self._remove_filter_warmup(filtered_chunk)
        rms_ready = self._process_rms_chunk(filtered_ready)

        return {
            "original": data.copy(),
            "filtered": filtered_ready,
            "rms": rms_ready,
        }

    def _ensure_states(self, data: np.ndarray) -> None:
        """Initialize state arrays and verify the channel layout."""
        channel_shape = data.shape[:-1]

        if self._channel_shape is not None:
            if channel_shape != self._channel_shape:
                raise ValueError(
                    "Signal channel layout changed. Reset the live "
                    "processor before processing the new layout."
                )
            return

        self._channel_shape = channel_shape

        filter_state_length = max(
            len(self._a),
            len(self._b),
        ) - 1

        self._filter_state = np.zeros(
            channel_shape + (filter_state_length,),
            dtype=np.float64,
        )

        rms_state_length = self._rms_window_size - 1

        self._rms_state = np.zeros(
            channel_shape + (rms_state_length,),
            dtype=np.float64,
        )

    def _remove_filter_warmup(
        self,
        filtered_chunk: np.ndarray,
    ) -> np.ndarray:
        """Hide filter output until sufficient samples have arrived."""
        chunk_size = filtered_chunk.shape[-1]

        remaining_warmup = max(
            0,
            self._filter_warmup_samples - self._filter_samples_seen,
        )

        skipped_samples = min(chunk_size, remaining_warmup)
        self._filter_samples_seen += chunk_size

        return filtered_chunk[..., skipped_samples:]

    def _process_rms_chunk(
        self,
        filtered_chunk: np.ndarray,
    ) -> np.ndarray:
        """Calculate causal moving RMS while retaining window state."""
        if filtered_chunk.shape[-1] == 0:
            return _empty_signal(filtered_chunk)

        squared = np.square(filtered_chunk)

        if self._rms_window_size == 1:
            return np.sqrt(squared)

        mean_squared, self._rms_state = signal.lfilter(
            self._rms_kernel,
            [1.0],
            squared,
            axis=-1,
            zi=self._rms_state,
        )

        chunk_size = filtered_chunk.shape[-1]

        incomplete_samples = max(
            0,
            (self._rms_window_size - 1) - self._rms_samples_seen,
        )

        skipped_samples = min(chunk_size, incomplete_samples)
        self._rms_samples_seen += chunk_size

        mean_squared = mean_squared[..., skipped_samples:]

        return np.sqrt(np.maximum(mean_squared, 0.0))
