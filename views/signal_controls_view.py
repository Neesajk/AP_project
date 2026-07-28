"""Controls for selecting the displayed signal."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)


class SignalControlsView(QWidget):
    """Let the user select a channel and signal mode."""

    channel_changed = Signal(int)
    mode_changed = Signal(str)
    plot_all_requested = Signal()
    offline_view_requested = Signal()

    def __init__(self):
        super().__init__()

        self.channel_input = QSpinBox()
        self.channel_input.setRange(1, 32)

        self.mode_input = QComboBox()
        self.mode_input.addItems(["Original", "RMS", "Filtered"])

        self.plot_all_button = QPushButton("Plot All Channels")
        self.offline_view_button = QPushButton("Offline View")

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Channel:"))
        layout.addWidget(self.channel_input)
        layout.addWidget(QLabel("Signal mode:"))
        layout.addWidget(self.mode_input)
        layout.addWidget(self.plot_all_button)
        layout.addWidget(self.offline_view_button)

        self.channel_input.valueChanged.connect(self.channel_changed.emit)
        self.mode_input.currentTextChanged.connect(self.mode_changed.emit)
        self.plot_all_button.clicked.connect(self.plot_all_requested.emit)
        self.offline_view_button.clicked.connect(
            self.offline_view_requested.emit
        )
