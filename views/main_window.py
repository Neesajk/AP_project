"""Main window for the EMG signal application."""

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from viewmodels.main_viewmodel import MainViewModel
from views.connection_view import ConnectionView
from views.offline_plot_view import OfflinePlotView  # NEW: Team Member 3
from views.plot_view import PlotView
from views.signal_controls_view import SignalControlsView


class MainWindow(QMainWindow):
    """Display the basic controls needed by the application."""

    def __init__(self, viewmodel: MainViewModel):
        super().__init__()
        self.viewmodel = viewmodel

        self.setWindowTitle("EMG Signal Viewer")
        self.resize(900, 600)

        self.connection_view = ConnectionView()
        self.signal_controls_view = SignalControlsView()
        self.plot_view = PlotView()
        self.status_label = QLabel("Not connected")
        self.offline_plot_view = None  # NEW: Team Member 3

        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        """Arrange the smaller views inside the main window."""
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.connection_view)
        main_layout.addWidget(self.signal_controls_view)
        main_layout.addWidget(self.plot_view)
        main_layout.addWidget(self.status_label)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _connect_signals(self) -> None:
        """Connect signals from the smaller views to the ViewModel."""
        self.connection_view.connect_requested.connect(self.viewmodel.connect_to_server)
        self.connection_view.disconnect_requested.connect(
            self.viewmodel.disconnect_from_server
        )
        self.signal_controls_view.channel_changed.connect(self.viewmodel.select_channel)
        self.signal_controls_view.mode_changed.connect(
            self.viewmodel.select_signal_mode
        )
        self.signal_controls_view.plot_all_requested.connect(
            self.viewmodel.plot_all_channels
        )
        # NEW: Team Member 3 - Offline View
        self.signal_controls_view.offline_view_requested.connect(
            self._open_offline_view
        )

        # The ViewModel updates the visible status without knowing GUI details.
        self.viewmodel.status_changed.connect(self.status_label.setText)
        self.viewmodel.connection_changed.connect(self.connection_view.set_connected)
        self.viewmodel.signal_data_changed.connect(self.plot_view.update_signal)
        self.viewmodel.all_signal_data_changed.connect(
            self.plot_view.update_all_signals
        )

    def _open_offline_view(self) -> None:
        """NEW: Team Member 3 - Open offline inspection window."""
        if self.offline_plot_view is None:
            self.offline_plot_view = OfflinePlotView()
            self.offline_plot_view.set_viewmodel(self.viewmodel)
            self.offline_plot_view.closed.connect(self._on_offline_closed)

        self.offline_plot_view.show()
        self.offline_plot_view.raise_()
        self.offline_plot_view.activateWindow()

    def _on_offline_closed(self) -> None:
        """NEW: Team Member 3 - Cleanup when offline window closes."""
        self.offline_plot_view = None

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release application resources before closing the window."""
        self.viewmodel.shutdown()
        super().closeEvent(event)
