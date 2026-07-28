# EMG Signal Visualization Application

PySide6 desktop application for receiving, processing, and visualizing streamed
electromyography (EMG) signals. The application displays live signals with
VisPy and retains the complete recording for offline inspection with
Matplotlib.

## Group 20

| Team member | Responsibilities |
|---|---|
| Marwan Abdelsamad | Project structure and MVVM integration, TCP communication and buffering, live VisPy visualization, all-channel navigation, error handling, testing, and integration |
| Neesa Jawad | Original, RMS, and filtered signal modes, live signal-processing improvements, and the initial all-channel plotting implementation |
| Era Baboci | Matplotlib offline inspection, offline controls, and integration of offline plotting with the shared signal-processing functions |

## Features

- Connection controls for the server host and TCP port
- Visible connection and data-receiving status
- Automatic streaming after a successful connection
- Live VisPy plot with labeled time and amplitude axes
- Selection of any of the 32 signal channels
- Original, RMS, and filtered signal modes
- Ten-second rolling live window
- All-channel overview with vertically offset traces
- Zoom and scrolling controls for inspecting groups of channels
- Matplotlib window for inspecting the complete recorded signal offline
- Graceful handling of connection failures, lost connections, and missing data

## Requirements

- Python 3.10 or newer
- An OpenGL-capable system for VisPy rendering
- The packages listed in `requirements.txt`

The main dependencies are NumPy, SciPy, Matplotlib, PySide6, and VisPy.

## Installation

Clone the repository and open a terminal in its root directory.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running the application

The application is the TCP client. It can connect to the server supplied for
Exercise 5. A copy of that server and its recording are included so the project
can also be tested locally.

### 1. Start the supplied server

From the repository root, open a terminal with the virtual environment active:

```powershell
python TCP_Server/main.py
```

The bundled server listens on `localhost` using port `12345`. Keep this terminal
open while using the client.

If the server is already running elsewhere, this step is unnecessary. Use that
server's host and port in the application instead.

### 2. Start the client

Open another terminal in the repository root, activate the same environment,
and run:

```powershell
python main.py
```

## Connecting to the TCP server

1. Enter the server host. For the bundled server, use `localhost`.
2. Enter the TCP port. The bundled server uses `12345`.
3. Click **Connect**.
4. Streaming starts automatically after the connection succeeds.

The status message at the bottom of the window reports connection results,
received packets, server disconnection, and TCP errors. Click **Disconnect** to
stop receiving data manually. The received recording remains available for
offline inspection after disconnection.

Each server packet contains 32 channels with 18 samples per channel. Values are
encoded as `float64`, giving a packet size of:

```text
32 channels x 18 samples x 8 bytes = 4608 bytes
```

## Using the live plot

- Select a channel from **1** through **32** with the channel control.
- Select **Original**, **RMS**, or **Filtered** from the signal-mode menu.
- The x-axis shows elapsed signal time in seconds.
- The y-axis shows signal amplitude and automatically scales to the visible
  data.
- The live display retains a rolling window of the newest ten seconds.
- Drag or use the mouse wheel on the plot to inspect it manually. Double-click
  the plot to restore automatic fitting to the latest data.

### Plotting all channels

Click **Plot All Channels** to display all 32 channels simultaneously with
vertical offsets.

All channels are visible initially. **Zoom In** changes the number of visible
channels through the levels 32, 16, 8, 4, and 2. When zoomed in, use the vertical
scrollbar or mouse wheel to move through the remaining channels. **Zoom Out**
returns toward the complete 32-channel overview.

Selecting an individual channel returns the live plot to single-channel mode.

## Offline inspection

After stopping or disconnecting from the stream:

1. Click **Offline View**.
2. Select a channel from **1** through **32**.
3. Select **Original**, **RMS**, or **Filtered**.
4. Click **Plot/Update** if a manual refresh is needed.

The controls also refresh the Matplotlib plot automatically when the selected
channel or mode changes. The offline window uses the complete recording
received since the latest successful connection, rather than only the
ten-second live window.

If no recording is available, the offline view displays an error instead of
crashing.

## Signal-processing parameters

The application sampling rate is `2000 Hz`.

### Filtered signal

- Filter type: Butterworth bandpass
- Filter order: 4
- Low cutoff: `20 Hz`
- High cutoff: `450 Hz`

Offline processing uses `scipy.signal.filtfilt` for zero-phase filtering of the
complete signal. Live processing uses the causal `scipy.signal.lfilter` and
retains filter state between incoming chunks. The first 27 live filtered
samples are treated as filter warm-up and are not displayed.

### RMS signal

- RMS window: `100 ms`
- Samples per RMS window at 2000 Hz: `200`
- Input to RMS calculation: the bandpass-filtered signal

Offline RMS uses a centered moving window. Live RMS is calculated causally and
retains its moving-window state between chunks. Live RMS output begins after a
complete RMS window is available.

## MVVM project structure

```text
.
|-- main.py
|-- requirements.txt
|-- models/
|   |-- signal_buffer.py
|   `-- signal_processing.py
|-- services/
|   `-- tcp_client.py
|-- viewmodels/
|   `-- main_viewmodel.py
|-- views/
|   |-- connection_view.py
|   |-- main_window.py
|   |-- offline_plot_view.py
|   |-- plot_view.py
|   `-- signal_controls_view.py
|-- TCP_Server/
|   `-- main.py
`-- data/
    `-- recording.pkl
```

### Models

- `SignalBuffer` stores the ten-second rolling live window and the complete
  recording.
- `signal_processing.py` implements offline filtering and RMS calculations and
  maintains state for live processing.

### Services

- `TcpClient` owns the socket, reconstructs complete 4608-byte packets from the
  TCP byte stream, decodes them to 32-by-18 NumPy arrays, and appends them to the
  signal buffer.

### ViewModel

- `MainViewModel` owns the application state and connects GUI actions to the
  TCP, buffering, and signal-processing logic.
- It polls the non-blocking socket, processes each new sample once, and emits Qt
  signals containing display-ready data.
- Views never read directly from the TCP socket.

### Views

- Views contain the PySide6 controls and the VisPy and Matplotlib plotting
  widgets.
- They emit user actions to the ViewModel and render data published by it.

### Application entry point

- `main.py` creates the model, service, ViewModel, and main window and injects
  their dependencies.

The provided `TCP_Server` is kept separate from the client application's MVVM
layers and does not form part of the client implementation.
