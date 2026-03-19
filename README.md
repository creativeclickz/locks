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

- Python 3.8+
- A connected game controller (Xbox, PlayStation, etc.)
- Windows / Linux / macOS

## Architecture

- `engine.py` — Core input processing (deadzone, snapping, RS override logic)
- `gui.py` — Full tkinter GUI with toggles, sliders, and status indicators
- `overlay.py` — Small always-on-top overlay window for in-game status
- `main.py` — Entry point, wires everything together
