"""Connection controls for the main window."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ConnectionView(QWidget):
    """Let the user enter server details and manage the connection."""

    connect_requested = Signal(str, int)
    disconnect_requested = Signal()

    def __init__(self):
        super().__init__()

        self.host_input = QLineEdit("localhost")

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65_535)
        self.port_input.setValue(12_345)

        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")

        form_layout = QFormLayout()
        form_layout.addRow("Host:", self.host_input)
        form_layout.addRow("Port:", self.port_input)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        self.connect_button.clicked.connect(self._request_connection)
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)

    def _request_connection(self) -> None:
        """Send the entered host and port to the main window."""
        self.connect_requested.emit(
            self.host_input.text().strip(),
            self.port_input.value(),
        )
