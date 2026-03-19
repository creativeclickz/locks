"""
InputSense 2K Vision - Core Input Processing Engine

Processing pipeline: Raw Input -> Deadzone -> Cardinal Snapping -> RS Override -> Final Output
All outputs normalized to (-1, 0, 1). No smoothing, no interpolation.
"""

import math
import threading
from dataclasses import dataclass, field


@dataclass
class StickState:
    """Represents a processed stick output."""
    x: float = 0.0
    y: float = 0.0


@dataclass
class EngineConfig:
    """All configurable parameters for the engine, driven by GUI in real time."""
    master_enabled: bool = True
    rs_auto_up_enabled: bool = True
    ls_snapping_enabled: bool = True
    rs_snapping_enabled: bool = True
    deadzone: float = 0.15
    snap_threshold: float = 0.25

    # Internal lock for thread-safe config updates
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs: object) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key) and not key.startswith("_"):
                    setattr(self, key, value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "master_enabled": self.master_enabled,
                "rs_auto_up_enabled": self.rs_auto_up_enabled,
                "ls_snapping_enabled": self.ls_snapping_enabled,
                "rs_snapping_enabled": self.rs_snapping_enabled,
                "deadzone": self.deadzone,
                "snap_threshold": self.snap_threshold,
            }


class InputEngine:
    """
    Core input processing engine.

    Pipeline per tick:
      1. Apply deadzone to raw stick values
      2. Snap to cardinal direction (if enabled)
      3. Apply RS override (force up) if movement/defense is active
      4. Normalize outputs to (-1, 0, 1)
    """

    def __init__(self, config: EngineConfig) -> None:
        self.config = config

        # Latest processed outputs
        self.ls_output = StickState()
        self.rs_output = StickState()

        # Raw input cache (set by controller reader)
        self.raw_ls_x: float = 0.0
        self.raw_ls_y: float = 0.0
        self.raw_rs_x: float = 0.0
        self.raw_rs_y: float = 0.0
        self.l2_trigger: float = 0.0  # 0.0 to 1.0

        # State flags
        self.is_moving: bool = False
        self.is_defensive: bool = False
        self.rs_override_active: bool = False

    # ── Deadzone ──────────────────────────────────────────────────────

    @staticmethod
    def apply_deadzone(x: float, y: float, deadzone: float) -> tuple[float, float]:
        """Zero out inputs within deadzone radius. No rescaling — hard cutoff."""
        magnitude = math.sqrt(x * x + y * y)
        if magnitude < deadzone:
            return 0.0, 0.0
        return x, y

    # ── Cardinal Snapping ─────────────────────────────────────────────

    @staticmethod
    def snap_to_cardinal(x: float, y: float, threshold: float) -> tuple[float, float]:
        """
        Quantize stick input to nearest cardinal direction.

        Uses hard threshold comparison — no interpolation or easing.
        Returns exactly one axis active at a time, normalized to -1 or 1.
        If input is below threshold on both axes, returns (0, 0).
        """
        abs_x = abs(x)
        abs_y = abs(y)

        # Both below threshold — no input
        if abs_x < threshold and abs_y < threshold:
            return 0.0, 0.0

        # Snap to dominant axis
        if abs_x >= abs_y:
            return (1.0 if x > 0 else -1.0), 0.0
        else:
            return 0.0, (1.0 if y > 0 else -1.0)

    # ── Normalization ─────────────────────────────────────────────────

    @staticmethod
    def normalize_value(v: float) -> float:
        """Clamp to -1, 0, or 1. No partial analog values."""
        if v > 0.0:
            return 1.0
        elif v < 0.0:
            return -1.0
        return 0.0

    # ── State Detection ───────────────────────────────────────────────

    def detect_movement_state(self, ls_x: float, ls_y: float, l2: float,
                              deadzone: float) -> None:
        """Determine if player is moving or in defensive stance."""
        ls_magnitude = math.sqrt(ls_x * ls_x + ls_y * ls_y)
        self.is_moving = ls_magnitude > deadzone
        self.is_defensive = l2 > 0.3  # L2 trigger threshold for defensive state

    # ── Main Processing Tick ──────────────────────────────────────────

    def process_tick(self) -> tuple[StickState, StickState]:
        """
        Run the full processing pipeline once.
        Called every controller loop iteration.

        Returns (ls_output, rs_output) with final processed values.
        """
        cfg = self.config.snapshot()

        # If master is off, pass through zeros (no processing)
        if not cfg["master_enabled"]:
            self.ls_output = StickState(0.0, 0.0)
            self.rs_output = StickState(0.0, 0.0)
            self.rs_override_active = False
            self.is_moving = False
            self.is_defensive = False
            return self.ls_output, self.rs_output

        deadzone = float(cfg["deadzone"])
        threshold = float(cfg["snap_threshold"])

        # ── Step 1: Deadzone ──
        ls_x, ls_y = self.apply_deadzone(self.raw_ls_x, self.raw_ls_y, deadzone)
        rs_x, rs_y = self.apply_deadzone(self.raw_rs_x, self.raw_rs_y, deadzone)

        # ── Detect movement / defense state ──
        self.detect_movement_state(ls_x, ls_y, self.l2_trigger, deadzone)

        # ── Step 2: Cardinal Snapping ──
        if cfg["ls_snapping_enabled"]:
            ls_x, ls_y = self.snap_to_cardinal(ls_x, ls_y, threshold)
        else:
            # Still normalize even without snapping
            ls_x = self.normalize_value(ls_x)
            ls_y = self.normalize_value(ls_y)

        if cfg["rs_snapping_enabled"]:
            rs_x, rs_y = self.snap_to_cardinal(rs_x, rs_y, threshold)
        else:
            rs_x = self.normalize_value(rs_x)
            rs_y = self.normalize_value(rs_y)

        # ── Step 3: RS Override (force up) ──
        # Takes priority over snapping when movement/defense is active
        self.rs_override_active = False
        if cfg["rs_auto_up_enabled"] and (self.is_moving or self.is_defensive):
            rs_x = 0.0
            rs_y = -1.0  # Up is negative Y on standard gamepad axes
            self.rs_override_active = True

        # ── Step 4: Final normalization (safety) ──
        ls_x = self.normalize_value(ls_x)
        ls_y = self.normalize_value(ls_y)
        rs_x = self.normalize_value(rs_x)
        rs_y = self.normalize_value(rs_y)

        self.ls_output = StickState(ls_x, ls_y)
        self.rs_output = StickState(rs_x, rs_y)

        return self.ls_output, self.rs_output

    # ── Input Setters (called by controller reader) ───────────────────

    def set_raw_input(self, ls_x: float, ls_y: float,
                      rs_x: float, rs_y: float, l2: float) -> None:
        """Update raw input values. Called from the controller polling loop."""
        self.raw_ls_x = ls_x
        self.raw_ls_y = ls_y
        self.raw_rs_x = rs_x
        self.raw_rs_y = rs_y
        self.l2_trigger = max(0.0, min(1.0, l2))
