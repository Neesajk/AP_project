from PySide6.QtCore import QObject, Signal

from models.signal_buffer import SignalBuffer
from services.tcp_client import TcpClient


class MainViewModel(QObject):
    """Hold basic UI state and react to actions from the main window."""

    status_changed = Signal(str)

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

    def connect_to_server(self, host: str, port: int) -> None:
        """Ask the TCP service to connect to the server."""
        message = self.tcp_client.connect_to_server(host, port)
        self.status_changed.emit(message)

    def disconnect_from_server(self) -> None:
        """Ask the TCP service to close its connection."""
        message = self.tcp_client.disconnect_from_server()
        self.status_changed.emit(message)

    def select_channel(self, channel_number: int) -> None:
        """Store the selected one-based channel as a zero-based index."""
        self.selected_channel = channel_number - 1
        self.status_changed.emit(f"Selected channel {channel_number}.")

    def select_signal_mode(self, mode: str) -> None:
        """Store the selected signal processing mode."""
        self.signal_mode = mode
        self.status_changed.emit(f"Signal mode: {mode}.")

    def plot_all_channels(self) -> None:
        """Handle the overview request until plotting is implemented."""
        self.status_changed.emit("All-channel plotting comes in a later step.")
