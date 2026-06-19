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
            "font-weight: 600; padding: 6px; color: #d1d5db; "
            "background: #111827;"
        )

        self.canvas = scene.SceneCanvas(
            keys="interactive",
            bgcolor="#111827",
            show=False,
        )
        self.canvas.native.setMinimumHeight(350)

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

        self.view = self.grid.add_view(row=0, col=1, border_color="#374151")
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
        valid = np.isfinite(x) & np.isfinite(y)

        if not np.any(valid):
            self.clear()
            return

        x = x[valid]
        y = y[valid]
        positions = np.column_stack((x, y)).astype(np.float32, copy=False)
        self.line.set_data(pos=positions)

        displayed_mode = mode
        self.title_label.setText(
            f"Channel {channel_number} - {displayed_mode}"
        )
        self._fit_camera(x, y)
        self.canvas.update()

    def clear(self) -> None:
        """Reset the plot to its empty state."""
        self.line.set_data(pos=np.empty((0, 2), dtype=np.float32))
        self.title_label.setText("Waiting for signal data")
        self.canvas.update()

    def _fit_camera(self, x: np.ndarray, y: np.ndarray) -> None:
        """Set readable bounds around the current rolling data window."""
        x_min, x_max = float(x.min()), float(x.max())
        y_min, y_max = float(y.min()), float(y.max())

        if x_min == x_max:
            x_padding = 0.5
        else:
            x_padding = (x_max - x_min) * 0.01

        if y_min == y_max:
            y_padding = max(abs(y_min) * 0.05, 1.0)
        else:
            y_padding = (y_max - y_min) * 0.08

        self.view.camera.set_range(
            x=(x_min - x_padding, x_max + x_padding),
            y=(y_min - y_padding, y_max + y_padding),
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

        if data.ndim != 2 or data.shape[0] == 0:
            self.clear()
            return

        valid_x = np.isfinite(x)
        if not np.any(valid_x):
            self.clear()
            return

        x = x[valid_x]
        data = data[:, valid_x]

        channel_range = np.nanmax(data) - np.nanmin(data)
        if not np.isfinite(channel_range) or channel_range == 0:
            channel_range = 1.0

        offset_step = channel_range * 1.5

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

            connect = np.ones(len(positions), dtype=bool)
            connect[-1] = False
            combined_connect.append(connect)

        if len(combined_positions) == 0:
            self.clear()
            return

        positions = np.concatenate(combined_positions, axis=0)
        connect = np.concatenate(combined_connect, axis=0)

        self.line.set_data(
            pos=positions,
            connect=connect,
        )

        self.title_label.setText(f"All 32 Channels - {mode}")

        self.view.camera.set_range(
            x=(float(x.min()), float(x.max())),
            y=(float(positions[:, 1].min()), float(positions[:, 1].max())),
            margin=0.03,
        )

        self.canvas.update()