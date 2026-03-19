"""
InputSense 2K Vision - Defensive Locks Settings GUI

Run this alongside Helios to control the Defensive Locks Creative Module in real time.
All changes are saved to defensive_locks_config.json, which the module reads automatically.

Usage:
    python defensive_locks_settings.py
    (or: py -3.11 defensive_locks_settings.py)

Hotkeys (global, work even when this window is not focused):
    F5 = Toggle Master ON/OFF
    F6 = Toggle RS Auto-Up
    F7 = Toggle LS Snapping
    F8 = Toggle RS Snapping
"""

import json
import os
import tkinter as tk
from tkinter import ttk

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

# ── Config File ───────────────────────────────────────────────────────
CONFIG_FILENAME = "defensive_locks_config.json"

DEFAULT_CONFIG = {
    "master_enabled": True,
    "rs_auto_up_enabled": True,
    "ls_snapping_enabled": True,
    "rs_snapping_enabled": True,
    "deadzone": 0.15,
    "snap_threshold": 0.25,
    "l2_threshold": 0.30,
}


def _get_config_path() -> str:
    """Get the config file path — same location logic as the module."""
    # Check next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, CONFIG_FILENAME)
    if os.path.isfile(path):
        return path

    # Check user home
    home = os.path.expanduser("~")
    home_path = os.path.join(home, CONFIG_FILENAME)
    if os.path.isfile(home_path):
        return home_path

    # Default: next to script
    return path


def load_config() -> dict:
    """Load config from file, returning defaults if not found."""
    path = _get_config_path()
    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                saved = json.load(f)
            # Merge with defaults to handle missing keys
            config = dict(DEFAULT_CONFIG)
            config.update(saved)
            return config
    except (json.JSONDecodeError, OSError):
        pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Save config to file — the module reads this automatically."""
    path = _get_config_path()
    try:
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"[!] Could not save config: {e}")


class SettingsGUI:
    """Settings GUI for the Defensive Locks Creative Module."""

    def __init__(self) -> None:
        self.config = load_config()

        self.root = tk.Tk()
        self.root.title("Defensive Locks — Settings")
        self.root.geometry("480x560")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Track toggle states
        self.master_var = tk.BooleanVar(value=self.config["master_enabled"])
        self.rs_autoup_var = tk.BooleanVar(value=self.config["rs_auto_up_enabled"])
        self.ls_snap_var = tk.BooleanVar(value=self.config["ls_snapping_enabled"])
        self.rs_snap_var = tk.BooleanVar(value=self.config["rs_snapping_enabled"])
        self.deadzone_var = tk.DoubleVar(value=self.config["deadzone"])
        self.threshold_var = tk.DoubleVar(value=self.config["snap_threshold"])
        self.l2_threshold_var = tk.DoubleVar(value=self.config["l2_threshold"])

        self._build_ui()
        self._bind_hotkeys()

    def _build_ui(self) -> None:
        # ── Title ──
        title_frame = tk.Frame(self.root, bg=BG_DARK)
        title_frame.pack(fill=tk.X, padx=16, pady=(12, 4))

        tk.Label(
            title_frame, text="DEFENSIVE LOCKS",
            font=("Consolas", 18, "bold"), fg=ACCENT_ON, bg=BG_DARK
        ).pack(side=tk.LEFT)

        self.status_indicator = tk.Label(
            title_frame, text="● ACTIVE", font=("Consolas", 12, "bold"),
            fg=ACCENT_ON, bg=BG_DARK
        )
        self.status_indicator.pack(side=tk.RIGHT)

        tk.Label(
            self.root, text="Settings — changes apply instantly in Helios",
            font=("Consolas", 9), fg=TEXT_SECONDARY, bg=BG_DARK
        ).pack(anchor=tk.W, padx=16)

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
                          0.0, 0.5, self._on_deadzone_change)
        self._make_slider(sliders_frame, "Snap Threshold", self.threshold_var,
                          0.05, 0.8, self._on_threshold_change)
        self._make_slider(sliders_frame, "L2 Defense Threshold", self.l2_threshold_var,
                          0.05, 0.8, self._on_l2_threshold_change)

        # ── Config File Info ──
        info_frame = tk.Frame(self.root, bg=BG_DARK)
        info_frame.pack(fill=tk.X, padx=16, pady=(8, 4))

        config_path = _get_config_path()
        tk.Label(
            info_frame, text=f"Config: {config_path}",
            font=("Consolas", 7), fg=TEXT_SECONDARY, bg=BG_DARK,
            wraplength=440, justify=tk.LEFT
        ).pack(anchor=tk.W)

        # ── Hotkey Info ──
        hotkey_frame = tk.Frame(self.root, bg=BG_DARK)
        hotkey_frame.pack(fill=tk.X, padx=16, pady=(4, 8))
        tk.Label(
            hotkey_frame,
            text="Hotkeys:  F5 Master  |  F6 RS Auto-Up  |  F7 LS Snap  |  F8 RS Snap",
            font=("Consolas", 8), fg=TEXT_SECONDARY, bg=BG_DARK
        ).pack()

        # ── Status Message ──
        self.status_msg = tk.Label(
            self.root, text="Ready — module will pick up changes automatically",
            font=("Consolas", 8), fg=ACCENT_ON, bg=BG_DARK
        )
        self.status_msg.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=4)

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
                     from_: float, to: float, command: object) -> None:
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
            variable=var, showvalue=False, length=200,
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
        self.config["master_enabled"] = new_val
        self._update_master_button()
        self._save_and_notify()

    def _toggle_rs_autoup(self) -> None:
        new_val = not self.rs_autoup_var.get()
        self.rs_autoup_var.set(new_val)
        self.config["rs_auto_up_enabled"] = new_val
        self._update_feature_button(self.rs_autoup_btn, "RS Auto-Up", new_val)
        self._save_and_notify()

    def _toggle_ls_snap(self) -> None:
        new_val = not self.ls_snap_var.get()
        self.ls_snap_var.set(new_val)
        self.config["ls_snapping_enabled"] = new_val
        self._update_feature_button(self.ls_snap_btn, "LS Snapping", new_val)
        self._save_and_notify()

    def _toggle_rs_snap(self) -> None:
        new_val = not self.rs_snap_var.get()
        self.rs_snap_var.set(new_val)
        self.config["rs_snapping_enabled"] = new_val
        self._update_feature_button(self.rs_snap_btn, "RS Snapping", new_val)
        self._save_and_notify()

    # ── Slider Callbacks ──────────────────────────────────────────────

    def _on_deadzone_change(self, value: float) -> None:
        self.config["deadzone"] = value
        self._save_and_notify()

    def _on_threshold_change(self, value: float) -> None:
        self.config["snap_threshold"] = value
        self._save_and_notify()

    def _on_l2_threshold_change(self, value: float) -> None:
        self.config["l2_threshold"] = value
        self._save_and_notify()

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

    # ── Save & Notify ─────────────────────────────────────────────────

    def _save_and_notify(self) -> None:
        """Save config and show brief status update."""
        save_config(self.config)
        self.status_msg.configure(text="Settings saved — applied in Helios", fg=ACCENT_ON)
        # Reset message after 2 seconds
        self.root.after(2000, lambda: self.status_msg.configure(
            text="Ready — module will pick up changes automatically"
        ))

    # ── Hotkeys ───────────────────────────────────────────────────────

    def _bind_hotkeys(self) -> None:
        """Bind F5-F8 hotkeys for quick toggles."""
        self.root.bind_all("<F5>", lambda e: self._toggle_master())
        self.root.bind_all("<F6>", lambda e: self._toggle_rs_autoup())
        self.root.bind_all("<F7>", lambda e: self._toggle_ls_snap())
        self.root.bind_all("<F8>", lambda e: self._toggle_rs_snap())

    # ── Main Loop ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the GUI."""
        self.root.mainloop()


def main() -> None:
    print("=" * 50)
    print("  Defensive Locks — Settings Panel")
    print("  Changes apply instantly in Helios")
    print("=" * 50)
    print()
    print(f"  Config file: {_get_config_path()}")
    print()
    print("  Hotkeys: F5=Master  F6=RS Auto-Up")
    print("           F7=LS Snap  F8=RS Snap")
    print()

    gui = SettingsGUI()
    gui.run()


if __name__ == "__main__":
    main()
