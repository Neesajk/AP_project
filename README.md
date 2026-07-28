# EMG Signal Viewer

Desktop application for TCP-based EMG signal acquisition and analysis.

## Team Members & Responsibilities

| Member | Tasks |
|--------|-------|
| Team Member 1 | TCP connection, data receiving, packet handling |
| Team Member 2 | Live VisPy plotting, real-time visualization |
| **Team Member 3** | **Offline Matplotlib inspection, channel selection, signal mode selection, integration, documentation** |

---

## Installation

### Prerequisites
- Python 3.10+
- pip

### Steps

```bash
git clone <repo-url>
cd AP_project

python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

---

## Features

### Live Plot (Team Member 2)
- Real-time VisPy visualization
- Channel selection (1-32)
- Signal mode: Original, RMS, Filtered

### Offline Inspection (Team Member 3)
- Click **"Offline View"** button to inspect recorded data
- Select any channel (1-32)
- Switch between signal modes:
  - **Original**: Raw signal
  - **RMS**: Root-mean-square smoothing (200-sample window)
  - **Filtered**: Low-pass Butterworth (500 Hz, order 4)
- **Plot/Update** button to refresh
- Full Matplotlib interactive controls (zoom, pan, save)

### TCP Connection (Team Member 1)
- Host/Port input
- Connect/Disconnect buttons
- Connection status display

---

## Signal Processing Details

### RMS (Root Mean Square)
- Window: 200 samples = 0.1 seconds at 2000 Hz sampling rate
- Smooths signal to show energy over time
- Formula: `RMS = sqrt(mean(x²))`

### Filtered Signal  
- Type: Butterworth low-pass filter
- Order: 4
- Cutoff: 500 Hz
- Sampling rate: 2000 Hz
- Method: Forward-backward filtering (zero phase distortion)

---

## Project Structure - MVVM Pattern

```
models/
  ├── signal_buffer.py       # Rolling buffer (all teams)
  └── signal_processing.py   # Live + offline signal processing

services/
  └── tcp_client.py          # TCP protocol (Team Member 1)

viewmodels/
  └── main_viewmodel.py      # State + data coordination (all teams)
                             # get_offline_signal() method (Team Member 3)

views/
  ├── main_window.py         # Main container
  ├── connection_view.py     # TCP controls (Team Member 1)
  ├── signal_controls_view.py # Channel/mode selectors (Teams 1,2,3)
  ├── plot_view.py           # VisPy live plot (Team Member 2)
  └── offline_plot_view.py   # Matplotlib offline view (Team Member 3)
```

### Architecture

**Model/Service Layer (data & processing)**
- `signal_processing.py`: Live and offline signal processing
- `signal_buffer.py`: Rolling buffer storage
- `tcp_client.py`: Network I/O

**ViewModel Layer (coordinator)**
- `get_offline_signal(channel, mode)`: Fetch & process data for offline view
- Bridges View and Model
- No GUI code

**View Layer (GUI only)**
- `offline_plot_view.py`: Matplotlib canvas + controls
- Gets data via ViewModel
- Handles user interaction

---

## How Team Member 3's Offline View Works

1. User clicks **"Offline View"** button
2. OfflinePlotView window opens
3. User selects channel (1-32) and mode (Original/RMS/Filtered)
4. Click **"Plot/Update"** → OfflinePlotView calls `viewmodel.get_offline_signal(channel, mode)`
5. ViewModel:
   - Validates channel number
   - Gets raw data from signal_buffer
  - Calls `process_signal()` to apply the selected mode
   - Returns (time_array, signal_array)
6. OfflinePlotView plots using Matplotlib
7. Errors are caught and displayed in plot area

---

## Error Handling

| Error | Response |
|-------|----------|
| No recorded data | "No recorded data available." |
| Invalid channel | "Invalid channel: X. Must be 1-32." |
| Unknown mode | "Unknown signal mode: X" |
| Empty signal | "Signal data is empty." |
| TCP failure | Status message + connection reset |

---

## Dependencies

- **numpy**: Numerical arrays
- **scipy**: Signal processing (Butterworth filter)
- **matplotlib**: Offline plotting
- **PySide6**: GUI framework (Qt6)
- **vispy**: Real-time GPU plotting

---

## Testing Team Member 3 Offline View

1. Connect to TCP server and let data stream for 10+ seconds
2. Disconnect
3. Click "Offline View" button
4. Try different channels and modes
5. Verify Matplotlib interactions (zoom, pan, save)
6. Close window - should clean up without errors

---

## File Changes by Team Member 3

**Created:**
- `views/offline_plot_view.py` - Matplotlib viewer

**Modified:**
- `models/signal_processing.py` - Shared live/offline signal processing
- `views/signal_controls_view.py` - Added "Offline View" button + signal
- `views/main_window.py` - Integrated offline view window
- `viewmodels/main_viewmodel.py` - Added `get_offline_signal()` method
- `README.md` - Documentation

**No changes to:**
- TCP connection logic (Team Member 1)
- Live VisPy plot (Team Member 2)
- Core buffer/services