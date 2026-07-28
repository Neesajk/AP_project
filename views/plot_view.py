"""Live plot area for the main window."""

import numpy as np
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)
from vispy import scene


class PlotView(QWidget):
    """Display a live, interactive plot of the selected signal channel."""

    DEFAULT_VISIBLE_CHANNEL_COUNT = 32
    MIN_VISIBLE_CHANNEL_COUNT = 2
    CHANNEL_LABEL_WIDTH = 90
    Y_AXIS_WIDTH = 75
    X_AXIS_HEIGHT = 55
    GRID_MARGIN = 10

    def __init__(self):
        super().__init__()

        self.title_label = QLabel("Waiting for signal data")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "font-weight: 600; padding: 6px; color: #d1d5db; " "background: #111827;"
        )

        self.canvas = scene.SceneCanvas(
            keys="interactive",
            bgcolor="#111827",
            show=False,
        )
        self.canvas.native.setMinimumHeight(350)
        self.canvas.native.installEventFilter(self)
        self.canvas.events.mouse_press.connect(self._pause_auto_fit)
        self.canvas.events.mouse_wheel.connect(self._pause_auto_fit)
        self.canvas.events.mouse_double_click.connect(self._restore_auto_fit)

        self._active_plot = None
        self._auto_fit = True
        self._latest_camera_range = None
        self._all_channel_x_bounds = None
        self._all_channel_y_bounds = []
        self._visible_channel_count = self.DEFAULT_VISIBLE_CHANNEL_COUNT

        self.grid = self.canvas.central_widget.add_grid(
            margin=10,
            spacing=0,
        )

        axis_style = {
            "axis_color": "#9ca3af",
            "tick_color": "#6b7280",
            "text_color": "#d1d5db",
            "tick_font_size": 8,
            "axis_font_size": 9,
        }

        self.y_axis = scene.AxisWidget(
            orientation="left",
            axis_label="Amplitude",
            axis_label_margin=42,
            **axis_style,
        )
        self.y_axis.width_max = self.Y_AXIS_WIDTH

        self.x_axis = scene.AxisWidget(
            orientation="bottom",
            axis_label="Time (s)",
            axis_label_margin=32,
            **axis_style,
        )
        self.x_axis.height_max = self.X_AXIS_HEIGHT

        self.view = self.grid.add_view(
            row=0,
            col=1,
            border_color="#374151",
        )
        self.view.camera = scene.PanZoomCamera(aspect=None)
        self.view.camera.interactive = True

        self.grid.add_widget(self.y_axis, row=0, col=0)
        self.grid.add_widget(self.x_axis, row=1, col=1)

        self.y_axis.link_view(self.view)
        self.x_axis.link_view(self.view)

        self.grid_lines = scene.GridLines(
            color=(0.35, 0.4, 0.48, 0.25),
            parent=self.view.scene,
        )

        self.line = scene.Line(
            pos=np.empty((0, 2), dtype=np.float32),
            color="#22d3ee",
            width=1,
            method="gl",
            antialias=True,
            parent=self.view.scene,
        )

        self.channel_label_widget = QWidget(self.canvas.native)
        self.channel_label_widget.setFixedWidth(self.CHANNEL_LABEL_WIDTH)
        self.channel_label_widget.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self.channel_label_widget.setStyleSheet(
            "background: #111827; color: #e5e7eb;"
        )
        channel_label_layout = QVBoxLayout(self.channel_label_widget)
        channel_label_layout.setContentsMargins(4, 0, 4, 0)
        channel_label_layout.setSpacing(0)

        self.channel_labels = []
        self._channel_label_layout = channel_label_layout
        self.channel_label_widget.hide()

        self.visible_channel_label = QLabel()
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_in_button.clicked.connect(self._zoom_in_all_channels)
        self.zoom_out_button.clicked.connect(self._zoom_out_all_channels)

        self.all_channel_controls = QWidget()
        all_channel_controls_layout = QHBoxLayout(
            self.all_channel_controls
        )
        all_channel_controls_layout.setContentsMargins(8, 2, 8, 2)
        all_channel_controls_layout.addWidget(self.visible_channel_label)
        all_channel_controls_layout.addStretch()
        all_channel_controls_layout.addWidget(self.zoom_in_button)
        all_channel_controls_layout.addWidget(self.zoom_out_button)
        self.all_channel_controls.hide()

        self.channel_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.channel_scrollbar.valueChanged.connect(
            self._update_all_channel_camera
        )
        self.channel_scrollbar.hide()

        plot_layout = QHBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.canvas.native, stretch=1)
        plot_layout.addWidget(self.channel_scrollbar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_label)
        layout.addWidget(self.all_channel_controls)
        layout.addLayout(plot_layout, stretch=1)

    def update_signal(
        self,
        x: np.ndarray,
        y: np.ndarray,
        channel_number: int,
        mode: str,
    ) -> None:
        """Update the line and follow the latest buffered signal window."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
            self.clear()
            return

        valid = np.isfinite(x) & np.isfinite(y)

        if not np.any(valid):
            self.clear()
            return

        x = x[valid]
        y = y[valid]

        positions = np.column_stack((x, y)).astype(
            np.float32,
            copy=False,
        )

        self._activate_plot(("single", channel_number, mode))

        # Reset the connection mode after displaying all channels.
        self.line.set_data(
            pos=positions,
            connect="strip",
        )
        self._set_channel_labels_visible(False)
        self.all_channel_controls.hide()
        self.channel_scrollbar.hide()

        self.title_label.setText(f"Channel {channel_number} - {mode}")

        self._fit_camera(x, y)
        self.canvas.update()

    def clear(self) -> None:
        """Reset the plot to its empty state."""
        self.line.set_data(
            pos=np.empty((0, 2), dtype=np.float32),
            connect="strip",
        )
        self._set_channel_labels_visible(False)
        self.all_channel_controls.hide()
        self.channel_scrollbar.hide()
        self._active_plot = None
        self._auto_fit = True
        self._latest_camera_range = None
        self._all_channel_x_bounds = None
        self._all_channel_y_bounds = []

        self.title_label.setText("Waiting for signal data")
        self.canvas.update()

    def eventFilter(self, watched, event) -> bool:
        """Use the mouse wheel to scroll channels in the all-channel view."""
        if (
            watched is self.canvas.native
            and event.type() == QEvent.Type.Resize
            and hasattr(self, "channel_label_widget")
        ):
            self._position_channel_labels()

        is_all_channel_wheel = (
            watched is self.canvas.native
            and event.type() == QEvent.Type.Wheel
            and self._active_plot is not None
            and self._active_plot[0] == "all"
        )

        if not is_all_channel_wheel:
            return super().eventFilter(watched, event)

        wheel_delta = event.angleDelta().y()

        if wheel_delta == 0:
            wheel_delta = event.pixelDelta().y()

        if wheel_delta != 0:
            direction = -1 if wheel_delta > 0 else 1
            self.channel_scrollbar.setValue(
                self.channel_scrollbar.value() + direction
            )

        event.accept()
        return True

    def _set_channel_labels_visible(self, visible: bool) -> None:
        """Show or collapse the fixed channel-label column."""
        self.channel_label_widget.setVisible(visible)

        if visible:
            self._position_channel_labels()
            self.channel_label_widget.raise_()

    def _ensure_channel_labels(self, channel_count: int) -> None:
        """Create reusable labels for every available channel."""
        while len(self.channel_labels) < channel_count:
            label = QLabel()
            label.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )
            label.setStyleSheet(
                "font-size: 11px; padding-right: 4px;"
            )
            self._channel_label_layout.addWidget(label, stretch=1)
            self.channel_labels.append(label)

    def _zoom_in_all_channels(self) -> None:
        """Show fewer channels at a larger vertical scale."""
        self._set_visible_channel_count(
            max(
                self.MIN_VISIBLE_CHANNEL_COUNT,
                self._visible_channel_count // 2,
            )
        )

    def _zoom_out_all_channels(self) -> None:
        """Show more channels at a smaller vertical scale."""
        self._set_visible_channel_count(
            self._visible_channel_count * 2
        )

    def _set_visible_channel_count(self, requested_count: int) -> None:
        """Apply an all-channel zoom level within the available range."""
        channel_count = len(self._all_channel_y_bounds)

        if channel_count == 0:
            return

        self._visible_channel_count = min(
            max(requested_count, self.MIN_VISIBLE_CHANNEL_COUNT),
            channel_count,
        )
        self._configure_all_channel_navigation()
        self._update_all_channel_camera(self.channel_scrollbar.value())

    def _configure_all_channel_navigation(self) -> None:
        """Update scrolling and zoom controls for the current zoom level."""
        channel_count = len(self._all_channel_y_bounds)

        if channel_count == 0:
            return

        visible_channels = min(
            self._visible_channel_count,
            channel_count,
        )
        maximum_start = max(0, channel_count - visible_channels)

        self.channel_scrollbar.setRange(0, maximum_start)
        self.channel_scrollbar.setPageStep(visible_channels)
        self.channel_scrollbar.setSingleStep(1)
        self.channel_scrollbar.setEnabled(maximum_start > 0)

        self.visible_channel_label.setText(
            f"{visible_channels} channels visible"
        )
        self.zoom_in_button.setEnabled(
            visible_channels > self.MIN_VISIBLE_CHANNEL_COUNT
        )
        self.zoom_out_button.setEnabled(
            visible_channels < channel_count
        )

    def _position_channel_labels(self) -> None:
        """Place channel names beside the traces without covering the axes."""
        label_height = max(
            self.canvas.native.height()
            - self.X_AXIS_HEIGHT
            - 2 * self.GRID_MARGIN,
            1,
        )
        label_x = self.Y_AXIS_WIDTH + self.GRID_MARGIN

        self.channel_label_widget.setGeometry(
            label_x,
            self.GRID_MARGIN,
            self.CHANNEL_LABEL_WIDTH,
            label_height,
        )

    def _activate_plot(self, plot_key: tuple[str, int, str]) -> None:
        """Restore auto-fit when the displayed channel or mode changes."""
        if plot_key == self._active_plot:
            return

        self._active_plot = plot_key
        self._auto_fit = True

    def _pause_auto_fit(self, _event=None) -> None:
        """Preserve the camera range after the user starts navigating."""
        self._auto_fit = False

    def _restore_auto_fit(self, _event=None) -> None:
        """Resume following live data when the user double-clicks the plot."""
        self._auto_fit = True

        if self._latest_camera_range is not None:
            self.view.camera.set_range(**self._latest_camera_range)
            self.canvas.update()

    def _update_camera_range(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
        margin: float,
    ) -> None:
        """Store the latest data bounds and apply them while auto-fit is active."""
        self._latest_camera_range = {
            "x": x_range,
            "y": y_range,
            "margin": margin,
        }

        if self._auto_fit:
            self.view.camera.set_range(**self._latest_camera_range)

    def _fit_camera(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """Set readable bounds around the current rolling data window."""
        x_min = float(x.min())
        x_max = float(x.max())
        y_min = float(y.min())
        y_max = float(y.max())

        if x_min == x_max:
            x_padding = 0.5
        else:
            x_padding = (x_max - x_min) * 0.01

        if y_min == y_max:
            y_padding = max(abs(y_min) * 0.05, 1.0)
        else:
            y_padding = (y_max - y_min) * 0.08

        self._update_camera_range(
            x_range=(x_min - x_padding, x_max + x_padding),
            y_range=(y_min - y_padding, y_max + y_padding),
            margin=0,
        )

    def update_all_signals(
        self,
        x: np.ndarray,
        data: np.ndarray,
        mode: str,
    ) -> None:
        """Update the plot with all channels using vertical offsets."""
        x = np.asarray(x, dtype=np.float64)
        data = np.asarray(data, dtype=np.float64)

        if (
            x.ndim != 1
            or data.ndim != 2
            or data.shape[0] == 0
            or data.shape[1] != x.shape[0]
        ):
            self.clear()
            return

        valid_x = np.isfinite(x)

        if not np.any(valid_x):
            self.clear()
            return

        x = x[valid_x]
        data = data[:, valid_x]

        finite_data = data[np.isfinite(data)]

        if finite_data.size == 0:
            self.clear()
            return

        signal_min = float(np.min(finite_data))
        signal_max = float(np.max(finite_data))
        channel_range = signal_max - signal_min

        if not np.isfinite(channel_range) or channel_range == 0:
            channel_range = 1.0

        offset_step = channel_range * 1.5
        channel_count = data.shape[0]
        channel_offsets = (
            np.arange(channel_count - 1, -1, -1) * offset_step
        )

        combined_positions = []
        combined_connect = []
        channel_bounds = []

        for channel_index in range(channel_count):
            y = data[channel_index]
            valid_y = np.isfinite(y)

            if not np.any(valid_y):
                channel_bounds.append(None)
                continue

            channel_x = x[valid_y]
            channel_y = y[valid_y] + channel_offsets[channel_index]

            positions = np.column_stack((channel_x, channel_y)).astype(
                np.float32,
                copy=False,
            )

            combined_positions.append(positions)
            channel_bounds.append(
                (
                    float(channel_y.min()),
                    float(channel_y.max()),
                )
            )

            connect = np.ones(
                len(positions),
                dtype=bool,
            )
            connect[-1] = False
            combined_connect.append(connect)

        if not combined_positions:
            self.clear()
            return

        positions = np.concatenate(
            combined_positions,
            axis=0,
        )
        connect = np.concatenate(
            combined_connect,
            axis=0,
        )

        self.line.set_data(
            pos=positions,
            connect=connect,
        )

        entering_all_channel_mode = (
            self._active_plot is None
            or self._active_plot[0] != "all"
        )
        plot_key = ("all", channel_count, mode)
        self._activate_plot(plot_key)

        x_min = float(x.min())
        x_max = float(x.max())
        x_span = x_max - x_min

        if x_span == 0:
            x_span = 1.0

        self._set_channel_labels_visible(True)

        self.title_label.setText(f"All {channel_count} Channels - {mode}")

        self._all_channel_x_bounds = (
            x_min - x_span * 0.16,
            x_max + x_span * 0.01,
        )
        self._all_channel_y_bounds = channel_bounds

        if entering_all_channel_mode:
            self._visible_channel_count = min(
                self.DEFAULT_VISIBLE_CHANNEL_COUNT,
                channel_count,
            )

        self._ensure_channel_labels(channel_count)
        self._configure_all_channel_navigation()
        self.all_channel_controls.show()
        self.channel_scrollbar.show()

        if entering_all_channel_mode:
            self.channel_scrollbar.setValue(0)

        self._update_all_channel_camera()

        self.canvas.update()

    def _update_all_channel_camera(self, value: int | None = None) -> None:
        """Show one scrollable group while keeping every channel plotted."""
        if (
            self._all_channel_x_bounds is None
            or not self._all_channel_y_bounds
        ):
            return

        channel_count = len(self._all_channel_y_bounds)
        visible_channels = min(
            self._visible_channel_count,
            channel_count,
        )
        first_channel = self.channel_scrollbar.value()
        last_channel = min(
            first_channel + visible_channels,
            channel_count,
        )

        for label_index, label in enumerate(self.channel_labels):
            channel_number = first_channel + label_index + 1
            is_visible = channel_number <= last_channel
            label.setVisible(is_visible)

            if is_visible:
                label.setText(f"Channel {channel_number}")

        visible_bounds = [
            bounds
            for bounds in self._all_channel_y_bounds[first_channel:last_channel]
            if bounds is not None
        ]

        if not visible_bounds:
            return

        y_min = min(bounds[0] for bounds in visible_bounds)
        y_max = max(bounds[1] for bounds in visible_bounds)
        y_padding = max((y_max - y_min) * 0.03, 1.0)
        y_range = (
            y_min - y_padding,
            y_max + y_padding,
        )

        self._update_camera_range(
            x_range=self._all_channel_x_bounds,
            y_range=y_range,
            margin=0,
        )

        if value is not None and not self._auto_fit:
            current_rect = self.view.camera.rect
            self.view.camera.set_range(
                x=(current_rect.left, current_rect.right),
                y=y_range,
                margin=0,
            )

        self.canvas.update()
