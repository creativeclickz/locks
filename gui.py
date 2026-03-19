"""
InputSense 2K Vision - Main GUI

Full tkinter interface with:
- Master ON/OFF toggle with visual indicator
- RS Auto-Up toggle
- LS Snapping toggle
- RS Snapping toggle
- Deadzone and snap threshold sliders
- Real-time stick output visualization
- Status bar showing active features
"""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine import EngineConfig, InputEngine


# ── Color Constants ───────────────────────────────────────────────────
BG_DARK = "#1a1a2e"
BG_PANEL = "#16213e"
BG_CARD = "#0f3460"
ACCENT_ON = "#00e676"
ACCENT_OFF = "#ff1744"
ACCENT_WARN = "#ffab00"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#9e9e9e"
SLIDER_TROUGH = "#263238"


class ModuleGUI:
    """Main GUI window for the InputSense 2K Vision module."""

    def __init__(self, config: "EngineConfig", engine: "InputEngine") -> None:
        self.config = config
        self.engine = engine

        self.root = tk.Tk()
        self.root.title("InputSense 2K Vision — Defensive Creative Module")
        self.root.geometry("720x680")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Track toggle states
        self.master_var = tk.BooleanVar(value=config.master_enabled)
        self.rs_autoup_var = tk.BooleanVar(value=config.rs_auto_up_enabled)
        self.ls_snap_var = tk.BooleanVar(value=config.ls_snapping_enabled)
        self.rs_snap_var = tk.BooleanVar(value=config.rs_snapping_enabled)
        self.deadzone_var = tk.DoubleVar(value=config.deadzone)
        self.threshold_var = tk.DoubleVar(value=config.snap_threshold)

        self._build_ui()
        self._start_update_loop()

    # ── UI Construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Title bar
        title_frame = tk.Frame(self.root, bg=BG_DARK)
        title_frame.pack(fill=tk.X, padx=16, pady=(12, 4))

        tk.Label(
            title_frame, text="INPUTSENSE 2K VISION",
            font=("Consolas", 18, "bold"), fg=ACCENT_ON, bg=BG_DARK
        ).pack(side=tk.LEFT)

        self.status_indicator = tk.Label(
            title_frame, text="● ACTIVE", font=("Consolas", 12, "bold"),
            fg=ACCENT_ON, bg=BG_DARK
        )
        self.status_indicator.pack(side=tk.RIGHT)

        tk.Label(
            self.root, text="Defensive Creative Module",
            font=("Consolas", 10), fg=TEXT_SECONDARY, bg=BG_DARK
        ).pack(anchor=tk.W, padx=16)

        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16, pady=8)

        # ── Master Toggle ──
        master_frame = tk.Frame(self.root, bg=BG_CARD, highlightbackground=ACCENT_ON,
                                highlightthickness=2)
        master_frame.pack(fill=tk.X, padx=16, pady=4)

        self.master_btn = tk.Button(
            master_frame, text="MASTER: ON", font=("Consolas", 14, "bold"),
            fg="#000000", bg=ACCENT_ON, activebackground=ACCENT_ON,
            relief=tk.FLAT, padx=20, pady=8,
            command=self._toggle_master
        )
        self.master_btn.pack(fill=tk.X, padx=8, pady=8)

        # ── Feature Toggles ──
        toggles_frame = tk.Frame(self.root, bg=BG_DARK)
        toggles_frame.pack(fill=tk.X, padx=16, pady=4)

        self.rs_autoup_btn = self._make_toggle_button(
            toggles_frame, "RS Auto-Up", self.rs_autoup_var, self._toggle_rs_autoup, 0
        )
        self.ls_snap_btn = self._make_toggle_button(
            toggles_frame, "LS Snapping", self.ls_snap_var, self._toggle_ls_snap, 1
        )
        self.rs_snap_btn = self._make_toggle_button(
            toggles_frame, "RS Snapping", self.rs_snap_var, self._toggle_rs_snap, 2
        )

        # ── Sliders ──
        sliders_frame = tk.Frame(self.root, bg=BG_PANEL)
        sliders_frame.pack(fill=tk.X, padx=16, pady=8)

        self._make_slider(sliders_frame, "Deadzone", self.deadzone_var,
                          0.0, 0.5, self._on_deadzone_change, 0)
        self._make_slider(sliders_frame, "Snap Threshold", self.threshold_var,
                          0.05, 0.8, self._on_threshold_change, 1)

        # ── Live Monitor ──
        monitor_frame = tk.LabelFrame(
            self.root, text=" Live Input Monitor ",
            font=("Consolas", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_PANEL,
            labelanchor=tk.N
        )
        monitor_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        # Stick visualizations
        sticks_frame = tk.Frame(monitor_frame, bg=BG_PANEL)
        sticks_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # LS visualization
        ls_frame = tk.Frame(sticks_frame, bg=BG_PANEL)
        ls_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=4)
        tk.Label(ls_frame, text="LEFT STICK", font=("Consolas", 9, "bold"),
                 fg=TEXT_SECONDARY, bg=BG_PANEL).pack()
        self.ls_canvas = tk.Canvas(ls_frame, width=140, height=140,
                                   bg="#0a0a1a", highlightthickness=1,
                                   highlightbackground="#333")
        self.ls_canvas.pack(pady=4)
        self.ls_value_label = tk.Label(ls_frame, text="X: 0.0  Y: 0.0",
                                       font=("Consolas", 9), fg=TEXT_PRIMARY,
                                       bg=BG_PANEL)
        self.ls_value_label.pack()

        # RS visualization
        rs_frame = tk.Frame(sticks_frame, bg=BG_PANEL)
        rs_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=4)
        tk.Label(rs_frame, text="RIGHT STICK", font=("Consolas", 9, "bold"),
                 fg=TEXT_SECONDARY, bg=BG_PANEL).pack()
        self.rs_canvas = tk.Canvas(rs_frame, width=140, height=140,
                                   bg="#0a0a1a", highlightthickness=1,
                                   highlightbackground="#333")
        self.rs_canvas.pack(pady=4)
        self.rs_value_label = tk.Label(rs_frame, text="X: 0.0  Y: 0.0",
                                       font=("Consolas", 9), fg=TEXT_PRIMARY,
                                       bg=BG_PANEL)
        self.rs_value_label.pack()

        # State indicators
        state_frame = tk.Frame(sticks_frame, bg=BG_PANEL)
        state_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=4)
        tk.Label(state_frame, text="STATE", font=("Consolas", 9, "bold"),
                 fg=TEXT_SECONDARY, bg=BG_PANEL).pack(pady=(0, 4))

        self.moving_label = tk.Label(state_frame, text="● Moving: NO",
                                     font=("Consolas", 9), fg=TEXT_SECONDARY,
                                     bg=BG_PANEL)
        self.moving_label.pack(anchor=tk.W, padx=8)

        self.defensive_label = tk.Label(state_frame, text="● Defensive: NO",
                                        font=("Consolas", 9), fg=TEXT_SECONDARY,
                                        bg=BG_PANEL)
        self.defensive_label.pack(anchor=tk.W, padx=8)

        self.rs_override_label = tk.Label(state_frame, text="● RS Override: OFF",
                                          font=("Consolas", 9), fg=TEXT_SECONDARY,
                                          bg=BG_PANEL)
        self.rs_override_label.pack(anchor=tk.W, padx=8)

        self.l2_label = tk.Label(state_frame, text="L2: 0.00",
                                 font=("Consolas", 9), fg=TEXT_SECONDARY,
                                 bg=BG_PANEL)
        self.l2_label.pack(anchor=tk.W, padx=8, pady=(8, 0))

        # ── Hotkey Info ──
        hotkey_frame = tk.Frame(self.root, bg=BG_DARK)
        hotkey_frame.pack(fill=tk.X, padx=16, pady=(4, 8))
        tk.Label(
            hotkey_frame,
            text="Hotkeys:  F5 Master  |  F6 RS Auto-Up  |  F7 LS Snap  |  F8 RS Snap",
            font=("Consolas", 8), fg=TEXT_SECONDARY, bg=BG_DARK
        ).pack()

    # ── Toggle Button Factory ─────────────────────────────────────────

    def _make_toggle_button(self, parent: tk.Frame, label: str,
                            var: tk.BooleanVar, command: object,
                            col: int) -> tk.Button:
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.grid(row=0, column=col, padx=6, pady=4, sticky="ew")
        parent.columnconfigure(col, weight=1)

        state = "ON" if var.get() else "OFF"
        color = ACCENT_ON if var.get() else ACCENT_OFF

        btn = tk.Button(
            frame, text=f"{label}: {state}",
            font=("Consolas", 10, "bold"), fg="#000000", bg=color,
            activebackground=color, relief=tk.FLAT, padx=10, pady=6,
            command=command
        )
        btn.pack(fill=tk.X)
        return btn

    # ── Slider Factory ────────────────────────────────────────────────

    def _make_slider(self, parent: tk.Frame, label: str, var: tk.DoubleVar,
                     from_: float, to: float, command: object, row: int) -> None:
        frame = tk.Frame(parent, bg=BG_PANEL)
        frame.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(frame, text=label, font=("Consolas", 10),
                 fg=TEXT_PRIMARY, bg=BG_PANEL).pack(side=tk.LEFT, padx=(4, 8))

        value_label = tk.Label(frame, text=f"{var.get():.2f}",
                               font=("Consolas", 10, "bold"),
                               fg=ACCENT_ON, bg=BG_PANEL, width=5)
        value_label.pack(side=tk.RIGHT, padx=4)

        slider = tk.Scale(
            frame, from_=from_, to=to, resolution=0.01, orient=tk.HORIZONTAL,
            variable=var, showvalue=False, length=300,
            bg=BG_PANEL, fg=TEXT_PRIMARY, troughcolor=SLIDER_TROUGH,
            highlightthickness=0, sliderrelief=tk.FLAT,
            command=lambda v, lbl=value_label, cmd=command: (
                lbl.configure(text=f"{float(v):.2f}"),
                cmd(float(v))
            )
        )
        slider.pack(side=tk.RIGHT, padx=4)

    # ── Toggle Callbacks ──────────────────────────────────────────────

    def _toggle_master(self) -> None:
        new_val = not self.master_var.get()
        self.master_var.set(new_val)
        self.config.update(master_enabled=new_val)
        self._update_master_button()

    def _toggle_rs_autoup(self) -> None:
        new_val = not self.rs_autoup_var.get()
        self.rs_autoup_var.set(new_val)
        self.config.update(rs_auto_up_enabled=new_val)
        self._update_feature_button(self.rs_autoup_btn, "RS Auto-Up", new_val)

    def _toggle_ls_snap(self) -> None:
        new_val = not self.ls_snap_var.get()
        self.ls_snap_var.set(new_val)
        self.config.update(ls_snapping_enabled=new_val)
        self._update_feature_button(self.ls_snap_btn, "LS Snapping", new_val)

    def _toggle_rs_snap(self) -> None:
        new_val = not self.rs_snap_var.get()
        self.rs_snap_var.set(new_val)
        self.config.update(rs_snapping_enabled=new_val)
        self._update_feature_button(self.rs_snap_btn, "RS Snapping", new_val)

    # ── Button Visual Updates ─────────────────────────────────────────

    def _update_master_button(self) -> None:
        is_on = self.master_var.get()
        color = ACCENT_ON if is_on else ACCENT_OFF
        text = "MASTER: ON" if is_on else "MASTER: OFF"
        self.master_btn.configure(text=text, bg=color, activebackground=color)
        status_text = "● ACTIVE" if is_on else "● INACTIVE"
        self.status_indicator.configure(text=status_text, fg=color)

    def _update_feature_button(self, btn: tk.Button, label: str,
                               is_on: bool) -> None:
        color = ACCENT_ON if is_on else ACCENT_OFF
        state = "ON" if is_on else "OFF"
        btn.configure(text=f"{label}: {state}", bg=color, activebackground=color)

    # ── Public Toggle Methods (for hotkeys) ───────────────────────────

    def toggle_master(self) -> None:
        self.root.after(0, self._toggle_master)

    def toggle_rs_autoup(self) -> None:
        self.root.after(0, self._toggle_rs_autoup)

    def toggle_ls_snap(self) -> None:
        self.root.after(0, self._toggle_ls_snap)

    def toggle_rs_snap(self) -> None:
        self.root.after(0, self._toggle_rs_snap)

    # ── Live Monitor Update ───────────────────────────────────────────

    def _start_update_loop(self) -> None:
        self._update_monitor()

    def _update_monitor(self) -> None:
        """Update stick visualizations and state indicators."""
        ls = self.engine.ls_output
        rs = self.engine.rs_output

        # Update stick canvases
        self._draw_stick(self.ls_canvas, ls.x, ls.y)
        self._draw_stick(self.rs_canvas, rs.x, rs.y)

        # Update value labels
        self.ls_value_label.configure(text=f"X: {ls.x:+.0f}  Y: {ls.y:+.0f}")
        self.rs_value_label.configure(text=f"X: {rs.x:+.0f}  Y: {rs.y:+.0f}")

        # Update state indicators
        if self.engine.is_moving:
            self.moving_label.configure(text="● Moving: YES", fg=ACCENT_ON)
        else:
            self.moving_label.configure(text="● Moving: NO", fg=TEXT_SECONDARY)

        if self.engine.is_defensive:
            self.defensive_label.configure(text="● Defensive: YES", fg=ACCENT_WARN)
        else:
            self.defensive_label.configure(text="● Defensive: NO", fg=TEXT_SECONDARY)

        if self.engine.rs_override_active:
            self.rs_override_label.configure(text="● RS Override: ON", fg=ACCENT_WARN)
        else:
            self.rs_override_label.configure(text="● RS Override: OFF", fg=TEXT_SECONDARY)

        self.l2_label.configure(text=f"L2: {self.engine.l2_trigger:.2f}")

        # Schedule next update (~30 fps for GUI)
        self.root.after(33, self._update_monitor)

    def _draw_stick(self, canvas: tk.Canvas, x: float, y: float) -> None:
        """Draw stick position on canvas. Center = neutral, dot = current."""
        canvas.delete("all")
        w = 140
        h = 140
        cx = w // 2
        cy = h // 2
        radius = 55

        # Draw crosshair
        canvas.create_line(cx, 10, cx, h - 10, fill="#333333", width=1)
        canvas.create_line(10, cy, w - 10, cy, fill="#333333", width=1)

        # Draw boundary circle
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                           outline="#444444", width=1)

        # Draw deadzone circle
        dz = self.deadzone_var.get()
        dz_r = int(radius * dz)
        if dz_r > 0:
            canvas.create_oval(cx - dz_r, cy - dz_r, cx + dz_r, cy + dz_r,
                               outline="#662222", width=1, dash=(2, 2))

        # Draw stick position
        dot_x = cx + int(x * radius)
        dot_y = cy + int(y * radius)
        dot_r = 6

        # Color based on activity
        if abs(x) > 0 or abs(y) > 0:
            dot_color = ACCENT_ON
        else:
            dot_color = TEXT_SECONDARY

        canvas.create_oval(dot_x - dot_r, dot_y - dot_r,
                           dot_x + dot_r, dot_y + dot_r,
                           fill=dot_color, outline="")

        # Draw direction line from center
        if abs(x) > 0 or abs(y) > 0:
            canvas.create_line(cx, cy, dot_x, dot_y, fill=dot_color, width=2)

    # ── Slider Callbacks ──────────────────────────────────────────────

    def _on_deadzone_change(self, value: float) -> None:
        self.config.update(deadzone=value)

    def _on_threshold_change(self, value: float) -> None:
        self.config.update(snap_threshold=value)

    # ── Main Loop ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the tkinter main loop."""
        self.root.mainloop()

    def is_alive(self) -> bool:
        """Check if the GUI window is still open."""
        try:
            return self.root.winfo_exists()
        except tk.TclError:
            return False

    def destroy(self) -> None:
        """Safely destroy the GUI."""
        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass
