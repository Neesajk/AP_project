import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from models.signal_processing import process_signal
from models.signal_buffer import SignalBuffer
from services.tcp_client import TcpClient


class MainViewModel(QObject):
    """Hold basic UI state and react to actions from the main window."""

    status_changed = Signal(str)
    connection_changed = Signal(bool)
    signal_data_changed = Signal(object, object, int, str)
    all_signal_data_changed = Signal(object, object, str)

    def __init__(
        self,
        signal_buffer: SignalBuffer,
        tcp_client: TcpClient,
    ):
        super().__init__()
        self.signal_buffer = signal_buffer
        self.tcp_client = tcp_client
        self.selected_channel = 0
        self.signal_mode = "Original"
        self.plot_all_mode = False

        self.receive_timer = QTimer(self)
        self.receive_timer.setInterval(10)
        self.receive_timer.timeout.connect(self._receive_data)

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
            self.receive_timer.start()

    def disconnect_from_server(self) -> None:
        """Ask the TCP service to close its connection."""
        self.receive_timer.stop()
        message = self.tcp_client.disconnect_from_server()
        self.connection_changed.emit(False)
        self.status_changed.emit(message)

    def select_channel(self, channel_number: int) -> None:
        """Store the selected one-based channel as a zero-based index."""
        self.selected_channel = channel_number - 1
        self.status_changed.emit(f"Selected channel {channel_number}.")
        self._emit_selected_signal()
        self.plot_all_mode = False

    def select_signal_mode(self, mode: str) -> None:
        """Store the selected signal processing mode."""
        self.signal_mode = mode
        self.status_changed.emit(f"Signal mode: {mode}.")

        if self.plot_all_mode:
            self.plot_all_channels()
        else:
            self._emit_selected_signal()

    def plot_all_channels(self) -> None:
        """Enable all-channel live plotting and publish all processed channels."""
        self.plot_all_mode = True
        self._emit_all_signals()

    def shutdown(self) -> None:
        """Stop receiving data and release the TCP connection."""
        self.receive_timer.stop()
        if self.tcp_client.is_connected:
            self.tcp_client.disconnect_from_server()

    def _receive_data(self) -> None:
        """Poll the TCP service and publish newly buffered model data."""
        samples_before = self.signal_buffer.total_samples_received
        message = self.tcp_client.receive_data(self.signal_buffer)
        has_new_samples = (
            self.signal_buffer.total_samples_received > samples_before
        )

        if has_new_samples:
            self.status_changed.emit(message)

            if self.plot_all_mode:
                self._emit_all_signals()
            else:
                self._emit_selected_signal()
                if not self.tcp_client.is_connected:
                    self.receive_timer.stop()
                    self.connection_changed.emit(False)
                    self.status_changed.emit(message)

    def _emit_selected_signal(self) -> None:
        """Publish the selected channel's current processed signal window."""
        if not self.signal_buffer.has_data():
            return

        try:
            x, y = self.signal_buffer.get_window(self.selected_channel)

            processed_y = process_signal(
                y,
                self.signal_mode,
                self.signal_buffer.sampling_rate,
            )

            self.signal_data_changed.emit(
                x,
                processed_y,
                self.selected_channel + 1,
                self.signal_mode,
            )

        except ValueError as error:
            self.status_changed.emit(str(error))

    def _get_current_time_axis(self, number_of_samples: int):
        """Return the time axis for the current rolling buffer."""
        first_sample = (
            self.signal_buffer.total_samples_received - number_of_samples
        )
        return (
            first_sample + np.arange(number_of_samples)
        ) / self.signal_buffer.sampling_rate
    
    def _emit_all_signals(self) -> None:
        """Publish all channels for live all-channel plotting."""
        if not self.signal_buffer.has_data():
            self.status_changed.emit("No signal data available for all-channel plot.")
            return

        try:
            data = self.signal_buffer.get_data()

            processed_data = process_signal(
                data,
                self.signal_mode,
                self.signal_buffer.sampling_rate,
            )

            x = self._get_current_time_axis(processed_data.shape[1])

            self.all_signal_data_changed.emit(
                x,
                processed_data,
                self.signal_mode,
            )

            self.status_changed.emit(
                f"Showing all 32 channels in {self.signal_mode} mode."
            )

        except ValueError as error:
            self.status_changed.emit(str(error))