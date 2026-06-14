"""Live plot area for the main window."""

import numpy as np
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlotView(QWidget):
    """Display the live signal plot when VisPy is added."""

    def __init__(self):
        super().__init__()

        # This label will be replaced by a VisPy canvas later.
        self.placeholder = QLabel("Waiting for signal data")
        self.placeholder.setMinimumHeight(350)
        self.placeholder.setStyleSheet(
            "border: 1px solid gray; color: gray; padding: 20px;"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.placeholder)

    def update_signal(
        self,
        x: np.ndarray,
        y: np.ndarray,
        channel_number: int,
        mode: str,
    ) -> None:
        """Render a summary until the VisPy chart is implemented."""
        duration = x[-1] - x[0] if x.size > 1 else 0
        self.placeholder.setText(
            f"Channel {channel_number} - selected mode: {mode}\n"
            "Raw data preview (signal processing pending)\n"
            f"{y.size} samples ({duration:.3f} seconds)\n"
            f"Range: {y.min():.3f} to {y.max():.3f}"
        )
