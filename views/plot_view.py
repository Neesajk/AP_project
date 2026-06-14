"""Live plot area for the main window."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlotView(QWidget):
    """Display the live signal plot when VisPy is added."""

    def __init__(self):
        super().__init__()

        # This label will be replaced by a VisPy canvas later.
        placeholder = QLabel("Live signal plot will appear here")
        placeholder.setMinimumHeight(350)
        placeholder.setStyleSheet(
            "border: 1px solid gray; color: gray; padding: 20px;"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(placeholder)
