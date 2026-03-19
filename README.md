# InputSense 2K Vision - Defensive Creative Module

A real-time controller input processing module for defensive input control with a full GUI.

## Features

- **RS Auto-Up Override**: Forces right stick upward during active movement or defensive states (L2/LT trigger or LS activity)
- **Strict Cardinal Snapping**: 4-direction only input (up, down, left, right) for both LS and RS — no diagonals
- **Adjustable Deadzone & Threshold**: Fine-tune snapping sensitivity via GUI slider
- **Real-Time GUI**: Master toggle, per-feature toggles, visual indicators, all applied instantly
- **Hotkeys**: Toggle features mid-game without opening the GUI
- **On-Screen Overlay**: Small always-on-top indicator showing module status

## Processing Pipeline

```
Raw Input → Deadzone Filter → Cardinal Snapping → RS Override → Final Output
```

All stick outputs are normalized to full values (`-1`, `0`, `1`). No partial analog values, no smoothing, no interpolation.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### Hotkeys

| Key | Action |
|-----|--------|
| `F5` | Toggle Master ON/OFF |
| `F6` | Toggle RS Auto-Up |
| `F7` | Toggle LS Snapping |
| `F8` | Toggle RS Snapping |

## Requirements

- Python 3.8+ (for running the standalone GUI version)
- A connected game controller (DualSense / PS5 controller)
- Windows (for virtual controller and Helios integration)

## Building the Creative Module (.pyd for Helios / 2K Vision)

To use this as a Creative Module inside Helios II / 2K Vision:

1. **Install Python 3.11** (required — must match Helios): https://www.python.org/downloads/release/python-3110/
2. **Install Visual Studio Build Tools** (for the C compiler): https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Select "Desktop development with C++" during install
3. Run the build script:
   ```bash
   cd locks
   python build_creative_module.py
   ```
   The script auto-finds Python 3.11 even if it's not your default Python.
4. Copy the output `defensive_locks.cp311-win_amd64.pyd` to your 2K Vision `_creative` folder
5. In Helios, go to Creative Modules and import it

## Architecture

- `defensive_locks.py` — Creative Module for Helios (uses `creative_helper` API: `iterate()`, `get_val()`, `set_val()`, `get_actual()`)
- `engine.py` — Core input processing (deadzone, snapping, RS override logic)
- `gui.py` — Full tkinter GUI with toggles, sliders, and status indicators
- `overlay.py` — Small always-on-top overlay window for in-game status
- `main.py` — Entry point for standalone mode, wires everything together
- `build_creative_module.py` — Build script to compile the Creative Module .pyd
