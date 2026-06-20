from PySide6.QtCore import QObject, QTimer, Signal

import numpy as np

from models.signal_buffer import SignalBuffer
from models.signal_processor import process_offline_signal
from services.tcp_client import TcpClient


class MainViewModel(QObject):
    """Hold basic UI state and react to actions from the main window."""

    status_changed = Signal(str)
    connection_changed = Signal(bool)
    signal_data_changed = Signal(object, object, int, str)

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

    def select_signal_mode(self, mode: str) -> None:
        """Store the selected signal processing mode."""
        self.signal_mode = mode
        self.status_changed.emit(f"Signal mode: {mode}.")
        self._emit_selected_signal()

    def plot_all_channels(self) -> None:
        """Handle the overview request until plotting is implemented."""
        self.status_changed.emit("All-channel plotting comes in a later step.")

    def shutdown(self) -> None:
        """Stop receiving data and release the TCP connection."""
        self.receive_timer.stop()
        if self.tcp_client.is_connected:
            self.tcp_client.disconnect_from_server()

    def get_offline_signal(
        self,
        channel_number: int,
        mode: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Get processed signal data for offline inspection.
        
        Args:
            channel_number: 1-based channel index (1-32)
            mode: "Original", "RMS", or "Filtered"
        
        Returns:
            Tuple of (time_array, signal_array) both as numpy arrays
        
        Raises:
            ValueError: If buffer empty, channel invalid, or mode unknown
        """
        # Check if buffer has data
        if not self.signal_buffer.has_data():
            raise ValueError("No recorded data available.")
        
        # Validate channel
        if not 1 <= channel_number <= 32:
            raise ValueError(f"Invalid channel: {channel_number}. Must be 1-32.")
        
        # Convert to zero-based index
        channel_idx = channel_number - 1
        
        # Get raw data from buffer
        try:
            x, y = self.signal_buffer.get_window(channel_idx)
        except (IndexError, ValueError) as e:
            raise ValueError(f"Cannot get channel data: {e}")
        
        # Apply signal processing
        try:
            y_processed = process_offline_signal(y, mode)
        except ValueError as e:
            raise ValueError(f"Signal processing failed: {e}")
        
        # Ensure no empty data
        if len(x) == 0 or len(y_processed) == 0:
            raise ValueError("Signal data is empty.")
        
        return x, y_processed

    def _receive_data(self) -> None:
        """Poll the TCP service and publish newly buffered model data."""
        samples_before = self.signal_buffer.total_samples_received
        message = self.tcp_client.receive_data(self.signal_buffer)
        has_new_samples = (
            self.signal_buffer.total_samples_received > samples_before
        )

        if has_new_samples:
            self.status_changed.emit(message)
            self._emit_selected_signal()

        if not self.tcp_client.is_connected:
            self.receive_timer.stop()
            self.connection_changed.emit(False)
            self.status_changed.emit(message)

    def _emit_selected_signal(self) -> None:
        """Publish the selected channel's current model window."""
        if not self.signal_buffer.has_data():
            return

        x, y = self.signal_buffer.get_window(self.selected_channel)
        self.signal_data_changed.emit(
            x,
            y,
            self.selected_channel + 1,
            self.signal_mode,
        )
