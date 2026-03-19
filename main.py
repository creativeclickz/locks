"""
InputSense 2K Vision - Main Entry Point

Wires together:
- InputEngine (core processing)
- ModuleGUI (main control panel)
- OverlayWindow (in-game status indicator)
- Controller polling loop (pygame)
- Global hotkey listener (pynput)

All components share the same EngineConfig instance for real-time sync.
"""

import sys
import threading
import time

import pygame

from engine import EngineConfig, InputEngine
from gui import ModuleGUI
from overlay import OverlayWindow

# Hotkey imports — pynput for global hotkeys
try:
    from pynput import keyboard as pynput_keyboard
    HOTKEYS_AVAILABLE = True
except ImportError:
    HOTKEYS_AVAILABLE = False


# ── Controller Polling ────────────────────────────────────────────────

class ControllerPoller:
    """
    Reads raw gamepad input via pygame and feeds it into the engine.
    Runs in its own thread at high frequency (~500 Hz target).
    """

    def __init__(self, engine: InputEngine) -> None:
        self.engine = engine
        self._running = False
        self._thread: threading.Thread | None = None
        self.controller_connected = False
        self.controller_name = "None"

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _poll_loop(self) -> None:
        """Main polling loop. Reads controller and runs engine tick."""
        pygame.init()
        pygame.joystick.init()

        joystick = None

        while self._running:
            # Handle pygame events (required for joystick updates)
            for event in pygame.event.get():
                pass

            # Auto-detect controller
            if joystick is None:
                if pygame.joystick.get_count() > 0:
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
                    self.controller_connected = True
                    self.controller_name = joystick.get_name()
                else:
                    self.controller_connected = False
                    self.controller_name = "No controller"
                    time.sleep(0.5)
                    continue

            # Check if controller is still connected
            try:
                # Read raw stick values
                # Standard mapping: Axis 0=LS X, Axis 1=LS Y, Axis 2=RS X (or L2),
                # Axis 3=RS Y (or R2), Axis 4=RS X, Axis 5=RS Y
                # This varies by controller — we handle common layouts
                num_axes = joystick.get_numaxes()

                ls_x = joystick.get_axis(0) if num_axes > 0 else 0.0
                ls_y = joystick.get_axis(1) if num_axes > 1 else 0.0

                # PlayStation layout: axes 2,5 are triggers, 3,4 are RS
                # Xbox layout: axes 2,3 are RS, 4,5 are triggers
                # Try to detect based on axis count
                if num_axes >= 6:
                    # PlayStation-style (DS4/DualSense): LS=0,1 RS=2,3 L2=4 R2=5
                    # Xbox-style: LS=0,1 RS=3,4 LT=2 RT=5
                    # We'll use a common mapping that works for most
                    rs_x = joystick.get_axis(2) if num_axes > 2 else 0.0
                    rs_y = joystick.get_axis(3) if num_axes > 3 else 0.0
                    l2_raw = joystick.get_axis(4) if num_axes > 4 else 0.0
                elif num_axes >= 4:
                    rs_x = joystick.get_axis(2) if num_axes > 2 else 0.0
                    rs_y = joystick.get_axis(3) if num_axes > 3 else 0.0
                    l2_raw = 0.0
                else:
                    rs_x = 0.0
                    rs_y = 0.0
                    l2_raw = 0.0

                # Normalize L2 from (-1..1) to (0..1) for trigger
                l2 = (l2_raw + 1.0) / 2.0

                # Also check L2 button as fallback (button index 6 on many controllers)
                num_buttons = joystick.get_numbuttons()
                if num_buttons > 6 and joystick.get_button(6):
                    l2 = 1.0

                # Feed raw values into engine
                self.engine.set_raw_input(ls_x, ls_y, rs_x, rs_y, l2)

                # Run processing tick
                self.engine.process_tick()

            except pygame.error:
                # Controller disconnected
                joystick = None
                self.controller_connected = False
                self.controller_name = "Disconnected"
                continue

            # ~500 Hz polling (2ms sleep)
            time.sleep(0.002)

        pygame.joystick.quit()
        pygame.quit()


# ── Hotkey Listener ───────────────────────────────────────────────────

class HotkeyListener:
    """Global hotkey listener using pynput."""

    def __init__(self, gui: ModuleGUI) -> None:
        self.gui = gui
        self._listener: pynput_keyboard.Listener | None = None

    def start(self) -> None:
        if not HOTKEYS_AVAILABLE:
            return

        self._listener = pynput_keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _on_press(self, key: pynput_keyboard.Key | pynput_keyboard.KeyCode | None) -> None:
        try:
            if key == pynput_keyboard.Key.f5:
                self.gui.toggle_master()
            elif key == pynput_keyboard.Key.f6:
                self.gui.toggle_rs_autoup()
            elif key == pynput_keyboard.Key.f7:
                self.gui.toggle_ls_snap()
            elif key == pynput_keyboard.Key.f8:
                self.gui.toggle_rs_snap()
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 50)
    print("  InputSense 2K Vision — Defensive Creative Module")
    print("=" * 50)
    print()

    # Shared config (thread-safe)
    config = EngineConfig()

    # Create engine
    engine = InputEngine(config)

    # Create GUI (must be on main thread for tkinter)
    gui = ModuleGUI(config, engine)

    # Create overlay
    overlay = OverlayWindow(config, engine)

    # Start controller polling thread
    poller = ControllerPoller(engine)
    poller.start()
    print("[+] Controller poller started (500 Hz)")

    # Start hotkey listener
    hotkeys = HotkeyListener(gui)
    hotkeys.start()
    if HOTKEYS_AVAILABLE:
        print("[+] Hotkeys active: F5=Master, F6=RS Auto-Up, F7=LS Snap, F8=RS Snap")
    else:
        print("[!] pynput not available — hotkeys disabled")

    print("[+] GUI ready")
    print()

    # Run GUI main loop (blocks until window is closed)
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Shutting down...")
        poller.stop()
        hotkeys.stop()
        overlay.destroy()
        gui.destroy()
        print("[*] Done.")
        sys.exit(0)


if __name__ == "__main__":
    main()
