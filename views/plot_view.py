"""Live plot area for the main window."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from vispy import scene


class PlotView(QWidget):
    """Display a live, interactive plot of the selected signal channel."""

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
        self.canvas.events.mouse_press.connect(self._pause_auto_fit)
        self.canvas.events.mouse_wheel.connect(self._pause_auto_fit)
        self.canvas.events.mouse_double_click.connect(self._restore_auto_fit)

        self._active_plot = None
        self._auto_fit = True
        self._latest_camera_range = None

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
        self.y_axis.width_max = 75

        self.x_axis = scene.AxisWidget(
            orientation="bottom",
            axis_label="Time (s)",
            axis_label_margin=32,
            **axis_style,
        )
        self.x_axis.height_max = 55

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

        self.channel_labels = scene.Text(
            text="",
            color="#e5e7eb",
            font_size=8,
            pos=(0, 0),
            anchor_x="right",
            anchor_y="center",
            parent=self.view.scene,
        )
        self.channel_labels.visible = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_label)
        layout.addWidget(self.canvas.native, stretch=1)

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
        self.channel_labels.visible = False

        self.title_label.setText(f"Channel {channel_number} - {mode}")

        self._fit_camera(x, y)
        self.canvas.update()

    def clear(self) -> None:
        """Reset the plot to its empty state."""
        self.line.set_data(
            pos=np.empty((0, 2), dtype=np.float32),
            connect="strip",
        )
        self.channel_labels.visible = False
        self._active_plot = None
        self._auto_fit = True
        self._latest_camera_range = None

        self.title_label.setText("Waiting for signal data")
        self.canvas.update()

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
        signal_midpoint = (signal_min + signal_max) / 2

        combined_positions = []
        combined_connect = []

        for channel_index in range(data.shape[0]):
            y = data[channel_index]
            valid_y = np.isfinite(y)

            if not np.any(valid_y):
                continue

            channel_x = x[valid_y]
            channel_y = y[valid_y] + channel_index * offset_step

            positions = np.column_stack((channel_x, channel_y)).astype(
                np.float32,
                copy=False,
            )

            combined_positions.append(positions)

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

        channel_count = data.shape[0]
        self._activate_plot(("all", channel_count, mode))

        x_min = float(x.min())
        x_max = float(x.max())
        x_span = x_max - x_min

        if x_span == 0:
            x_span = 1.0

        label_x = x_min - x_span * 0.02
        label_positions = np.column_stack(
            (
                np.full(channel_count, label_x),
                signal_midpoint + np.arange(channel_count) * offset_step,
            )
        )
        labels = [
            f"Channel {channel_number}"
            for channel_number in range(1, channel_count + 1)
        ]

        if self.channel_labels.text != labels:
            self.channel_labels.text = labels

        self.channel_labels.pos = label_positions
        self.channel_labels.visible = True

        self.title_label.setText(f"All {channel_count} Channels - {mode}")

        self._update_camera_range(
            x_range=(
                x_min - x_span * 0.18,
                x_max,
            ),
            y_range=(
                float(positions[:, 1].min()),
                float(positions[:, 1].max()),
            ),
            margin=0.03,
        )

        self.canvas.update()
