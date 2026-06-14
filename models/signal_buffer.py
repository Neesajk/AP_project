"""Rolling buffer for received EMG signal samples."""

import numpy as np


class SignalBuffer:
    """Store the newest signal samples for a fixed time window.

    This contains the rolling-buffer behavior from the provided TCP model.
    TCP byte collection and packet reconstruction remain in ``TcpClient``.
    """

    def __init__(
        self,
        sampling_rate: float,
        channels: int = 32,
        window_seconds: float = 10,
    ):
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.window_seconds = window_seconds
        self.dtype = np.float64

        self.window_size = int(self.sampling_rate * self.window_seconds)
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)

        # Used to calculate the total elapsed signal time.
        self.total_samples_received = 0

    @property
    def sample_count(self) -> int:
        """Return the number of currently stored samples per channel."""
        return self.data_buffer.shape[1]

    def append(self, new_data: np.ndarray) -> None:
        """Append data with shape ``(channels, samples)`` to the buffer."""
        new_data = np.asarray(new_data, dtype=self.dtype)

        if new_data.ndim != 2:
            raise ValueError("Data must be a two-dimensional array.")
        if new_data.shape[0] != self.channels:
            raise ValueError(
                f"Expected {self.channels} channels, "
                f"but received {new_data.shape[0]}."
            )

        self.data_buffer = np.concatenate(
            (self.data_buffer, new_data),
            axis=1,
        )
        self.total_samples_received += new_data.shape[1]

        # Keep only the newest samples that fit in the time window.
        if self.sample_count > self.window_size:
            self.data_buffer = self.data_buffer[:, -self.window_size :]

    def get_data(self) -> np.ndarray:
        """Return a copy of all buffered data."""
        return self.data_buffer.copy()

    def get_channel(self, channel_index: int) -> np.ndarray:
        """Return a copy of one channel using a zero-based index."""
        if not 0 <= channel_index < self.channels:
            raise ValueError("Channel index is out of range.")
        return self.data_buffer[channel_index].copy()

    def has_data(self) -> bool:
        """Return True when enough samples are available for plotting."""
        return self.sample_count >= 2

    def get_window(self, channel_index: int) -> tuple[np.ndarray, np.ndarray]:
        """Return the time axis and data for one selected channel."""
        y = self.get_channel(channel_index)
        first_sample = self.total_samples_received - y.shape[0]
        x = (first_sample + np.arange(y.shape[0])) / self.sampling_rate
        return x, y

    def get_signal_time_seconds(self) -> float:
        """Return the total duration of all received samples in seconds."""
        return self.total_samples_received / self.sampling_rate

    def clear(self) -> None:
        """Remove all samples from the buffer."""
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)
        self.total_samples_received = 0
