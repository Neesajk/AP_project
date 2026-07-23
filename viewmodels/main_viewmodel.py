"""View model for the main EMG visualization window."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from models.signal_buffer import SignalBuffer
from models.signal_processing import LiveSignalProcessor
from services.tcp_client import TcpClient


class MainViewModel(QObject):
    """Hold UI state and coordinate live EMG signal processing."""

    status_changed = Signal(str)
    connection_changed = Signal(bool)
    signal_data_changed = Signal(object, object, int, str)
    all_signal_data_changed = Signal(object, object, str)

    def __init__(
        self,
        signal_buffer: SignalBuffer,
        tcp_client: TcpClient,
    ) -> None:
        super().__init__()

        self.signal_buffer = signal_buffer
        self.tcp_client = tcp_client

        self.selected_channel = 0
        self.signal_mode = "Original"
        self.plot_all_mode = False

        self.signal_processor = LiveSignalProcessor(
            sampling_rate=self.signal_buffer.sampling_rate
        )

        self._last_processed_sample = 0

        self._processed_buffers: dict[str, np.ndarray | None] = {
            "filtered": None,
            "rms": None,
        }

        # Poll the TCP socket frequently.
        self.receive_timer = QTimer(self)
        self.receive_timer.setInterval(10)
        self.receive_timer.timeout.connect(self._receive_data)

        # Update the GUI less frequently to avoid redrawing after every packet.
        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(50)
        self.plot_timer.timeout.connect(self._update_plot)

    def connect_to_server(self, host: str, port: int) -> None:
        """Ask the TCP service to connect to the server."""
        if not host:
            self.status_changed.emit("Please enter a server host.")
            return

        message = self.tcp_client.connect_to_server(host, port)

        self.status_changed.emit(message)
        self.connection_changed.emit(self.tcp_client.is_connected)

        if self.tcp_client.is_connected:
            self.signal_buffer.clear()
            self.signal_processor.reset()

            self._last_processed_sample = 0
            self._processed_buffers = {
                "filtered": None,
                "rms": None,
            }

            self.receive_timer.start()
            self.plot_timer.start()

    def disconnect_from_server(self) -> None:
        """Close the TCP connection and stop live updates."""
        self.receive_timer.stop()
        self.plot_timer.stop()

        message = self.tcp_client.disconnect_from_server()

        self.connection_changed.emit(False)
        self.status_changed.emit(message)

    def select_channel(self, channel_number: int) -> None:
        """Store the selected one-based channel as a zero-based index."""
        self.selected_channel = channel_number - 1
        self.plot_all_mode = False

        self.status_changed.emit(
            f"Selected channel {channel_number}."
        )

        self._emit_selected_signal()

    def select_signal_mode(self, mode: str) -> None:
        """Store the selected signal-processing mode."""
        normalized_mode = mode.lower()

        if normalized_mode not in {"original", "filtered", "rms"}:
            self.status_changed.emit(
                f"Invalid signal mode: {mode}"
            )
            return

        self.signal_mode = mode

        self.status_changed.emit(
            f"Signal mode: {mode}."
        )

        self._update_plot()

    def plot_all_channels(self) -> None:
        """Enable all-channel live plotting."""
        self.plot_all_mode = True
        self._emit_all_signals()

    def shutdown(self) -> None:
        """Stop receiving data and release the TCP connection."""
        self.receive_timer.stop()
        self.plot_timer.stop()

        if self.tcp_client.is_connected:
            self.tcp_client.disconnect_from_server()

    def _receive_data(self) -> None:
        """Poll the TCP service and process only newly received samples."""
        samples_before = self.signal_buffer.total_samples_received

        message = self.tcp_client.receive_data(
            self.signal_buffer
        )

        samples_after = self.signal_buffer.total_samples_received
        has_new_samples = samples_after > samples_before

        # Ignore normal polling messages, but still show errors.
        idle_messages = (
            "No new TCP bytes available right now.",
            "Waiting for more data to form a complete packet.",
        )

        if has_new_samples or message not in idle_messages:
            self.status_changed.emit(message)

        if has_new_samples:
            self._process_new_samples()

        # This must run regardless of whether new samples arrived and
        # regardless of the active plotting mode.
        if not self.tcp_client.is_connected:
            self.receive_timer.stop()
            self.plot_timer.stop()

            self.connection_changed.emit(False)

    def _process_new_samples(self) -> None:
        """Process only samples not previously passed to the live processor."""
        data = self.signal_buffer.get_data()

        if data.ndim != 2:
            self.status_changed.emit(
                "Expected signal data with shape "
                "(channels, samples)."
            )
            return

        total_buffered_samples = data.shape[-1]
        new_sample_count = (
            self.signal_buffer.total_samples_received
            - self._last_processed_sample
        )

        if new_sample_count <= 0:
            return

        # The rolling buffer may contain fewer samples than the total number
        # received, so never index farther back than its current length.
        new_sample_count = min(
            new_sample_count,
            total_buffered_samples,
        )

        new_data = data[..., -new_sample_count:]

        try:
            processed = self.signal_processor.process_chunk(
                new_data
            )
        except ValueError as error:
            self.status_changed.emit(str(error))
            return

        self._append_processed_data(
            mode="filtered",
            new_data=processed["filtered"],
        )

        self._append_processed_data(
            mode="rms",
            new_data=processed["rms"],
        )

        self._last_processed_sample = (
            self.signal_buffer.total_samples_received
        )

    def _append_processed_data(
        self,
        mode: str,
        new_data: np.ndarray,
    ) -> None:
        """Append processed samples while retaining the rolling window size."""
        if new_data.shape[-1] == 0:
            return

        existing_data = self._processed_buffers[mode]

        if existing_data is None:
            combined_data = new_data.copy()
        else:
            combined_data = np.concatenate(
                (existing_data, new_data),
                axis=-1,
            )

        maximum_samples = self.signal_buffer.get_data().shape[-1]

        if combined_data.shape[-1] > maximum_samples:
            combined_data = combined_data[
                ...,
                -maximum_samples:
            ]

        self._processed_buffers[mode] = combined_data

    def _update_plot(self) -> None:
        """Publish the latest signal at the GUI refresh frequency."""
        if not self.signal_buffer.has_data():
            return

        if self.plot_all_mode:
            self._emit_all_signals()
        else:
            self._emit_selected_signal()

    def _get_display_data(self) -> np.ndarray | None:
        """Return the rolling data for the currently selected mode."""
        mode = self.signal_mode.lower()

        if mode == "original":
            return self.signal_buffer.get_data()

        return self._processed_buffers.get(mode)

    def _emit_selected_signal(self) -> None:
        """Publish the selected channel's current signal window."""
        if not self.signal_buffer.has_data():
            return

        try:
            data = self._get_display_data()

            if data is None or data.shape[-1] == 0:
                self.status_changed.emit(
                    f"Waiting for enough samples to display "
                    f"{self.signal_mode} data."
                )
                return

            if self.selected_channel >= data.shape[0]:
                raise ValueError(
                    f"Channel {self.selected_channel + 1} "
                    "is not available."
                )

            channel_data = data[self.selected_channel]
            x = self._get_current_time_axis(
                channel_data.shape[-1]
            )

            self.signal_data_changed.emit(
                x,
                channel_data,
                self.selected_channel + 1,
                self.signal_mode,
            )

        except ValueError as error:
            self.status_changed.emit(str(error))

    def _emit_all_signals(self) -> None:
        """Publish all channels using already processed rolling data."""
        if not self.signal_buffer.has_data():
            self.status_changed.emit(
                "No signal data available for all-channel plot."
            )
            return

        try:
            data = self._get_display_data()

            if data is None or data.shape[-1] == 0:
                self.status_changed.emit(
                    f"Waiting for enough samples to display "
                    f"{self.signal_mode} data."
                )
                return

            x = self._get_current_time_axis(
                data.shape[-1]
            )

            self.all_signal_data_changed.emit(
                x,
                data,
                self.signal_mode,
            )

        except ValueError as error:
            self.status_changed.emit(str(error))

    def _get_current_time_axis(
        self,
        number_of_samples: int,
    ) -> np.ndarray:
        """Return a time axis aligned with the latest received sample."""
        first_sample = (
            self.signal_buffer.total_samples_received
            - number_of_samples
        )

        return (
            first_sample + np.arange(number_of_samples)
        ) / self.signal_buffer.sampling_rate
