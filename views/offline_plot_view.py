"""Offline signal inspection view using Matplotlib."""

import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class OfflinePlotView(QWidget):
    """Matplotlib-based offline signal inspection window."""

    closed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Offline Signal Inspection")
        self.resize(1000, 600)

        # Sampling rate from the application
        self.sampling_rate = 2000

        # Controls
        self.channel_spinbox = QSpinBox()
        self.channel_spinbox.setRange(1, 32)
        self.channel_spinbox.setValue(1)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Original", "RMS", "Filtered"])

        self.plot_button = QPushButton("Plot/Update")
        self.close_button = QPushButton("Close")

        # Matplotlib figure
        self.figure = Figure(figsize=(10, 5), dpi=100)
        self.figure.patch.set_facecolor("#f0f0f0")
        self.canvas = FigureCanvasQTAgg(self.figure)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Channel:"))
        controls_layout.addWidget(self.channel_spinbox)
        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.mode_combo)
        controls_layout.addWidget(self.plot_button)
        controls_layout.addWidget(self.close_button)
        controls_layout.addStretch()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.canvas)

        # Connect signals
        self.plot_button.clicked.connect(self._on_plot_clicked)
        self.close_button.clicked.connect(self._on_close_clicked)
        # Auto-update when controls change
        self.channel_spinbox.valueChanged.connect(self._on_plot_clicked)
        self.mode_combo.currentTextChanged.connect(self._on_plot_clicked)

    def set_viewmodel(self, viewmodel) -> None:
        """Store reference to ViewModel for data access."""
        self.viewmodel = viewmodel

    def _on_plot_clicked(self) -> None:
        """Fetch signal from ViewModel and plot."""
        if not hasattr(self, "viewmodel"):
            return

        channel = self.channel_spinbox.value()
        mode = self.mode_combo.currentText()

        try:
            x, y = self.viewmodel.get_offline_signal(channel, mode)
            self._plot_signal(x, y, channel, mode)
        except ValueError as e:
            self._show_error(str(e))

    def _plot_signal(
        self,
        x: np.ndarray,
        y: np.ndarray,
        channel: int,
        mode: str,
    ) -> None:
        """Plot the signal using Matplotlib."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.plot(x, y, color="blue", linewidth=1.5, label=mode)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        ax.set_title(f"Channel {channel} - {mode} Signal")
        ax.grid(True, alpha=0.3)
        ax.legend()

        self.canvas.draw()

    def _show_error(self, message: str) -> None:
        """Display error message in plot area."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(
            0.5,
            0.5,
            f"Error: {message}",
            ha="center",
            va="center",
            fontsize=12,
            color="red",
            transform=ax.transAxes,
        )
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw()

    def _on_close_clicked(self) -> None:
        """Close the offline inspection window."""
        self.closed.emit()
        self.close()
