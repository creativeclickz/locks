"""
InputSense 2K Vision - Defensive Locks Creative Module

Defensive input control module for 2K Vision / Helios II.
Implements cardinal snapping, RS auto-up override, and deadzone filtering.

Pipeline per tick:
  Raw Input (get_actual) -> Deadzone -> Cardinal Snapping -> RS Override -> Output (set_val)

All stick outputs normalized to full axis values. No smoothing, no interpolation.

Settings are read from defensive_locks_config.json (written by the settings GUI).
The config file is checked periodically so changes apply in real time.
"""

import os
import json

from creative_helper import (
    set_val,
    get_actual,
    MAX_AXIS,
    STICK_1_X,
    STICK_1_Y,
    STICK_2_X,
    STICK_2_Y,
    BUTTON_5,
)

# ── Config File Path ─────────────────────────────────────────────────
# Store config next to this module, or in user's home directory
_CONFIG_FILENAME: str = "defensive_locks_config.json"
_config_path: str = ""
_config_check_counter: int = 0
_CONFIG_CHECK_INTERVAL: int = 50  # Check config every ~50 ticks (~100ms at 500Hz)

# ── Configuration ─────────────────────────────────────────────────────
# These can be adjusted via the settings GUI

# Master toggle (1 = ON, 0 = OFF)
_master_enabled: int = 1

# Feature toggles
_rs_auto_up_enabled: int = 1
_ls_snapping_enabled: int = 1
_rs_snapping_enabled: int = 1

# Deadzone threshold (as fraction of MAX_AXIS)
_deadzone_fraction: float = 0.15

# Snap threshold (as fraction of MAX_AXIS)
_snap_fraction: float = 0.25

# L2/LT trigger threshold for defensive state detection (as fraction of MAX_AXIS)
_l2_defensive_threshold: float = 0.30


# ── Internal State ────────────────────────────────────────────────────

_is_moving: int = 0
_is_defensive: int = 0
_rs_override_active: int = 0


def _find_config_path() -> str:
    """Find the config file path. Checks multiple locations."""
    # Check next to this module file
    try:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(module_dir, _CONFIG_FILENAME)
        if os.path.isfile(path):
            return path
    except (NameError, OSError):
        pass

    # Check user's home directory
    home = os.path.expanduser("~")
    path = os.path.join(home, _CONFIG_FILENAME)
    if os.path.isfile(path):
        return path

    # Check common Helios/2K Vision locations
    for check_dir in [
        os.path.join(home, "Documents"),
        os.path.join(home, "AppData", "Local", "2K Vision"),
    ]:
        path = os.path.join(check_dir, _CONFIG_FILENAME)
        if os.path.isfile(path):
            return path

    # Default: next to module or in home
    try:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(module_dir, _CONFIG_FILENAME)
    except (NameError, OSError):
        return os.path.join(home, _CONFIG_FILENAME)


def _load_config() -> None:
    """Load configuration from JSON file if it exists."""
    global _master_enabled, _rs_auto_up_enabled, _ls_snapping_enabled
    global _rs_snapping_enabled, _deadzone_fraction, _snap_fraction
    global _l2_defensive_threshold, _config_path

    if not _config_path:
        _config_path = _find_config_path()

    try:
        if os.path.isfile(_config_path):
            with open(_config_path, "r") as f:
                cfg = json.load(f)
            _master_enabled = 1 if cfg.get("master_enabled", True) else 0
            _rs_auto_up_enabled = 1 if cfg.get("rs_auto_up_enabled", True) else 0
            _ls_snapping_enabled = 1 if cfg.get("ls_snapping_enabled", True) else 0
            _rs_snapping_enabled = 1 if cfg.get("rs_snapping_enabled", True) else 0
            _deadzone_fraction = float(cfg.get("deadzone", 0.15))
            _snap_fraction = float(cfg.get("snap_threshold", 0.25))
            _l2_defensive_threshold = float(cfg.get("l2_threshold", 0.30))
    except (json.JSONDecodeError, OSError, ValueError, KeyError):
        pass  # Keep current settings on any error


# ── Helper Functions ──────────────────────────────────────────────────

def _abs_val(v: int) -> int:
    """Absolute value without importing math."""
    if v < 0:
        return -v
    return v


def _magnitude_sq(x: int, y: int) -> int:
    """Squared magnitude to avoid sqrt (faster comparison)."""
    return x * x + y * y


def _snap_to_cardinal(x: int, y: int, threshold: int) -> tuple:
    """
    Quantize stick input to nearest cardinal direction.
    Hard threshold, no interpolation.
    Returns (snapped_x, snapped_y) at full axis magnitude or zero.
    """
    abs_x = _abs_val(x)
    abs_y = _abs_val(y)

    # Both below threshold — no input
    if abs_x < threshold and abs_y < threshold:
        return 0, 0

    # Snap to dominant axis at full magnitude
    if abs_x >= abs_y:
        if x > 0:
            return MAX_AXIS, 0
        else:
            return -MAX_AXIS, 0
    else:
        if y > 0:
            return 0, MAX_AXIS
        else:
            return 0, -MAX_AXIS


def _normalize_full(v: int) -> int:
    """Normalize to full axis value: -MAX_AXIS, 0, or MAX_AXIS."""
    if v > 0:
        return MAX_AXIS
    elif v < 0:
        return -MAX_AXIS
    return 0


# ── Init Function ─────────────────────────────────────────────────────

def _init() -> None:
    """Called once when the module is first loaded by 2K Vision / Helios."""
    global _master_enabled, _rs_auto_up_enabled, _ls_snapping_enabled
    global _rs_snapping_enabled, _is_moving, _is_defensive, _rs_override_active
    _master_enabled = 1
    _rs_auto_up_enabled = 1
    _ls_snapping_enabled = 1
    _rs_snapping_enabled = 1
    _is_moving = 0
    _is_defensive = 0
    _rs_override_active = 0
    # Load saved config if available
    _load_config()


# ── Main Iterate Function ────────────────────────────────────────────

def iterate() -> None:
    """
    Called every controller tick by 2K Vision / Helios.
    Reads raw input, processes through pipeline, writes output.
    """
    global _is_moving, _is_defensive, _rs_override_active, _config_check_counter

    # Periodically reload config from file
    _config_check_counter += 1
    if _config_check_counter >= _CONFIG_CHECK_INTERVAL:
        _config_check_counter = 0
        _load_config()

    # If master is off, don't process — passthrough raw input
    if not _master_enabled:
        _is_moving = 0
        _is_defensive = 0
        _rs_override_active = 0
        return

    # Calculate thresholds in axis units
    deadzone_threshold = int(MAX_AXIS * _deadzone_fraction)
    snap_threshold = int(MAX_AXIS * _snap_fraction)
    l2_threshold = int(MAX_AXIS * _l2_defensive_threshold)

    # ── Read raw stick values ──
    raw_ls_x = get_actual(STICK_1_X)
    raw_ls_y = get_actual(STICK_1_Y)
    raw_rs_x = get_actual(STICK_2_X)
    raw_rs_y = get_actual(STICK_2_Y)

    # ── Read L2/LT trigger for defensive state ──
    raw_l2 = get_actual(BUTTON_5)

    # ── Step 1: Deadzone ──
    deadzone_sq = deadzone_threshold * deadzone_threshold

    ls_x = raw_ls_x
    ls_y = raw_ls_y
    if _magnitude_sq(raw_ls_x, raw_ls_y) < deadzone_sq:
        ls_x = 0
        ls_y = 0

    rs_x = raw_rs_x
    rs_y = raw_rs_y
    if _magnitude_sq(raw_rs_x, raw_rs_y) < deadzone_sq:
        rs_x = 0
        rs_y = 0

    # ── Detect movement / defense state ──
    _is_moving = 1 if _magnitude_sq(ls_x, ls_y) > deadzone_sq else 0
    _is_defensive = 1 if _abs_val(raw_l2) > l2_threshold else 0

    # ── Step 2: Cardinal Snapping ──
    if _ls_snapping_enabled:
        ls_x, ls_y = _snap_to_cardinal(ls_x, ls_y, snap_threshold)
    else:
        ls_x = _normalize_full(ls_x)
        ls_y = _normalize_full(ls_y)

    if _rs_snapping_enabled:
        rs_x, rs_y = _snap_to_cardinal(rs_x, rs_y, snap_threshold)
    else:
        rs_x = _normalize_full(rs_x)
        rs_y = _normalize_full(rs_y)

    # ── Step 3: RS Override (force up) ──
    # Takes priority over snapping when movement/defense is active
    _rs_override_active = 0
    if _rs_auto_up_enabled and (_is_moving or _is_defensive):
        rs_x = 0
        rs_y = -MAX_AXIS  # Up is negative Y
        _rs_override_active = 1

    # ── Step 4: Final normalization (safety) ──
    ls_x = _normalize_full(ls_x)
    ls_y = _normalize_full(ls_y)
    rs_x = _normalize_full(rs_x)
    rs_y = _normalize_full(rs_y)

    # ── Write processed values to controller output ──
    set_val(STICK_1_X, ls_x)
    set_val(STICK_1_Y, ls_y)
    set_val(STICK_2_X, rs_x)
    set_val(STICK_2_Y, rs_y)
