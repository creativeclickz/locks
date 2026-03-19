"""
InputSense 2K Vision - On-Screen Overlay

Small always-on-top transparent indicator window that shows module status mid-game.
Displays: Master state, RS Override active, current stick directions.
"""

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine import EngineConfig, InputEngine

# Colors
OVERLAY_BG = "#111111"
COLOR_ACTIVE = "#00e676"
COLOR_INACTIVE = "#ff1744"
COLOR_WARN = "#ffab00"
COLOR_TEXT = "#cccccc"
COLOR_DIM = "#555555"


class OverlayWindow:
    """Small always-on-top status overlay for in-game visibility."""

    def __init__(self, config: "EngineConfig", engine: "InputEngine") -> None:
        self.config = config
        self.engine = engine

        self.root = tk.Toplevel()
        self.root.title("IS2KV")
        self.root.geometry("180x120+10+10")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=OVERLAY_BG)
        self.root.overrideredirect(True)  # Borderless

        # Make draggable
        self._drag_data = {"x": 0, "y": 0}
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)

        self._build_ui()
        self._start_update_loop()

    def _build_ui(self) -> None:
        # Title
        tk.Label(
            self.root, text="IS2KV", font=("Consolas", 8, "bold"),
            fg=COLOR_DIM, bg=OVERLAY_BG
        ).pack(anchor=tk.W, padx=4, pady=(2, 0))

        # Master status
        self.master_label = tk.Label(
            self.root, text="● ACTIVE", font=("Consolas", 10, "bold"),
            fg=COLOR_ACTIVE, bg=OVERLAY_BG
        )
        self.master_label.pack(anchor=tk.W, padx=4)

        # Feature indicators row
        features_frame = tk.Frame(self.root, bg=OVERLAY_BG)
        features_frame.pack(fill=tk.X, padx=4, pady=2)

        self.rs_up_indicator = tk.Label(
            features_frame, text="RS↑", font=("Consolas", 9, "bold"),
            fg=COLOR_ACTIVE, bg=OVERLAY_BG
        )
        self.rs_up_indicator.pack(side=tk.LEFT, padx=2)

        self.ls_snap_indicator = tk.Label(
            features_frame, text="LS□", font=("Consolas", 9, "bold"),
            fg=COLOR_ACTIVE, bg=OVERLAY_BG
        )
        self.ls_snap_indicator.pack(side=tk.LEFT, padx=2)

        self.rs_snap_indicator = tk.Label(
            features_frame, text="RS□", font=("Consolas", 9, "bold"),
            fg=COLOR_ACTIVE, bg=OVERLAY_BG
        )
        self.rs_snap_indicator.pack(side=tk.LEFT, padx=2)

        # RS override state
        self.override_label = tk.Label(
            self.root, text="RS Override: OFF", font=("Consolas", 8),
            fg=COLOR_DIM, bg=OVERLAY_BG
        )
        self.override_label.pack(anchor=tk.W, padx=4)

        # Stick output summary
        self.sticks_label = tk.Label(
            self.root, text="LS(0,0) RS(0,0)", font=("Consolas", 8),
            fg=COLOR_TEXT, bg=OVERLAY_BG
        )
        self.sticks_label.pack(anchor=tk.W, padx=4, pady=(2, 0))

    def _start_update_loop(self) -> None:
        self._update()

    def _update(self) -> None:
        """Update overlay display."""
        cfg = self.config.snapshot()

        # Master
        if cfg["master_enabled"]:
            self.master_label.configure(text="● ACTIVE", fg=COLOR_ACTIVE)
        else:
            self.master_label.configure(text="● INACTIVE", fg=COLOR_INACTIVE)

        # Feature indicators
        self.rs_up_indicator.configure(
            fg=COLOR_ACTIVE if cfg["rs_auto_up_enabled"] else COLOR_DIM
        )
        self.ls_snap_indicator.configure(
            fg=COLOR_ACTIVE if cfg["ls_snapping_enabled"] else COLOR_DIM
        )
        self.rs_snap_indicator.configure(
            fg=COLOR_ACTIVE if cfg["rs_snapping_enabled"] else COLOR_DIM
        )

        # RS Override
        if self.engine.rs_override_active:
            self.override_label.configure(text="RS Override: ON", fg=COLOR_WARN)
        else:
            self.override_label.configure(text="RS Override: OFF", fg=COLOR_DIM)

        # Stick outputs
        ls = self.engine.ls_output
        rs = self.engine.rs_output
        self.sticks_label.configure(
            text=f"LS({ls.x:+.0f},{ls.y:+.0f}) RS({rs.x:+.0f},{rs.y:+.0f})"
        )

        self.root.after(50, self._update)

    # ── Drag Support ──────────────────────────────────────────────────

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event: tk.Event) -> None:
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def destroy(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass
