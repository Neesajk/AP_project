"""TCP client service for receiving EMG signal data."""

class TcpClient:
    """Manage the TCP connection and received signal data.

    The real socket and receiving loop will be added in a later step.
    Keeping them here prevents networking code from entering the ViewModel.
    """

    CHANNEL_COUNT = 32
    SAMPLES_PER_PACKET = 18
    BYTES_PER_VALUE = 8
    PACKET_SIZE = CHANNEL_COUNT * SAMPLES_PER_PACKET * BYTES_PER_VALUE

    def __init__(self):
        self.is_connected = False

    def connect_to_server(self, host: str, port: int) -> str:
        """Start a TCP connection to the given server.

        This method is currently a placeholder for the socket connection.
        """
        return f"Ready to connect to {host}:{port}. TCP logic comes next."

    def disconnect_from_server(self) -> str:
        """Close the TCP connection.

        This method will later stop the receiving loop and close the socket.
        """
        self.is_connected = False
        return "Disconnected."
