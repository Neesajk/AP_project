"""TCP client service for receiving EMG signal data."""

import socket

import numpy as np


class TcpClient:
    """Manage the TCP connection and received signal data."""

    CHANNEL_COUNT = 32
    SAMPLES_PER_PACKET = 18
    BYTES_PER_VALUE = 8
    PACKET_SIZE = CHANNEL_COUNT * SAMPLES_PER_PACKET * BYTES_PER_VALUE

    def __init__(self):
        self.is_connected = False
        self.socket = None
        self.byte_buffer = bytearray()

    def connect_to_server(self, host: str, port: int) -> str:
        """Start a TCP connection to the given server."""
        if self.is_connected:
            return "Already connected. Please disconnect first."

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.socket.setblocking(False)
        except OSError as exc:
            self._close_socket()
            return f"Connection failed: {exc}"

        self.is_connected = True
        return f"Connected to {host}:{port}."

    def disconnect_from_server(self) -> str:
        """Close the TCP connection."""
        self.is_connected = False
        self.byte_buffer.clear()
        self._close_socket()
        return "Disconnected."

    def _close_socket(self) -> None:
        """Close the socket without changing buffered packet bytes."""
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None

    def receive_data(self, signal_buffer) -> str:
        """Receive all currently available TCP bytes and process complete packets."""
        if not self.is_connected or self.socket is None:
            return "Not connected to a TCP server."

        received_bytes, error, connection_closed = self._receive_bytes()
        packet_result = self._process_packet_buffer(signal_buffer)

        if connection_closed:
            self.byte_buffer.clear()
            if error:
                return error
            if packet_result:
                return f"{packet_result} Connection closed by server."
            return "Connection closed by server."

        if error:
            return error
        if packet_result:
            return packet_result

        if received_bytes == 0:
            return "No new TCP bytes available right now."

        return "Waiting for more data to form a complete packet."

    def _receive_bytes(self) -> tuple[int, str | None, bool]:
        """Read all currently available bytes from the non-blocking socket."""
        received_bytes = 0
        try:
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    self.is_connected = False
                    self._close_socket()
                    return received_bytes, None, True
                self.byte_buffer.extend(chunk)
                received_bytes += len(chunk)
        except BlockingIOError:
            return received_bytes, None, False
        except OSError as exc:
            self.is_connected = False
            self._close_socket()
            return received_bytes, f"TCP receive error: {exc}", True

    def _process_packet_buffer(self, signal_buffer) -> str | None:
        """Decode and append all complete packets currently in the byte buffer."""
        packets_processed = 0
        while len(self.byte_buffer) >= self.PACKET_SIZE:
            packet_bytes = bytes(self.byte_buffer[: self.PACKET_SIZE])
            del self.byte_buffer[: self.PACKET_SIZE]

            packet_array, error = self._decode_packet(packet_bytes)
            if error:
                return error

            try:
                signal_buffer.append(packet_array)
            except Exception as exc:
                return f"Failed to append decoded packet: {exc}"

            packets_processed += 1

        if packets_processed:
            return f"Received {packets_processed} packet(s)."
        return None

    def _decode_packet(
        self, packet_bytes: bytes
    ) -> tuple[np.ndarray | None, str | None]:
        """Decode a raw packet into a (channels, samples) NumPy array."""
        try:
            packet_array = np.frombuffer(packet_bytes, dtype=np.float64)
            packet_array = packet_array.reshape(
                (self.CHANNEL_COUNT, self.SAMPLES_PER_PACKET),
                order="C",
            )
            return packet_array, None
        except (ValueError, TypeError) as exc:
            return None, f"Packet decoding failed: {exc}"
