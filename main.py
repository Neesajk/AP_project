"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from models.signal_buffer import SignalBuffer
from services.tcp_client import TcpClient
from viewmodels.main_viewmodel import MainViewModel
from views.main_window import MainWindow

# This must match the sampling rate of the provided EMG recording.
SAMPLING_RATE = 2_000


def main() -> int:
    """Create and start the desktop application."""
    app = QApplication(sys.argv)

    # Build the application from Model -> ViewModel -> View.
    signal_buffer = SignalBuffer(sampling_rate=SAMPLING_RATE)
    tcp_client = TcpClient()
    viewmodel = MainViewModel(signal_buffer, tcp_client)
    window = MainWindow(viewmodel)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
