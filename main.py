"""
InputSense 2K Vision - Main Entry Point

Wires together:
- InputEngine (core processing)
- ModuleGUI (main control panel)
- OverlayWindow (in-game status indicator)
- Controller polling loop (pygame)
- Virtual gamepad output (vgamepad/ViGEmBus)
- Global hotkey listener (pynput)

All components share the same EngineConfig instance for real-time sync.

Controller flow:
  Physical DualSense -> pygame (raw read) -> InputEngine (process) -> vgamepad (virtual Xbox output) -> Game
"""

import sys
import threading
import time

import pygame

from engine import EngineConfig, InputEngine
from gui import ModuleGUI
from overlay import OverlayWindow

# Virtual gamepad imports
try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except ImportError:
    VGAMEPAD_AVAILABLE = False

# Hotkey imports — pynput for global hotkeys
try:
    from pynput import keyboard as pynput_keyboard
    HOTKEYS_AVAILABLE = True
except ImportError:
    HOTKEYS_AVAILABLE = False


# ── DualSense Button Mapping ─────────────────────────────────────────
# DualSense button indices (pygame) -> Xbox 360 vgamepad buttons
DUALSENSE_BUTTON_MAP: dict[int, int] = {
    0: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,              # Square -> X
    1: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,               # Cross -> A
    2: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,               # Circle -> B
    3: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,               # Triangle -> Y
    4: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,   # L1 -> LB
    5: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,  # R1 -> RB
    8: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,            # Share -> Back
    9: vg.XUSB_BUTTON.XUSB_GAMEPAD_START,            # Options -> Start
    10: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,      # L3 -> LS Click
    11: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,     # R3 -> RS Click
    12: vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,           # PS Button -> Guide
} if VGAMEPAD_AVAILABLE else {}


def _hat_to_dpad(hat_x: int, hat_y: int) -> int:
    """Convert pygame hat (x, y) to vgamepad DPAD button flags."""
    if not VGAMEPAD_AVAILABLE:
        return 0
    dpad = 0
    if hat_y == 1:
        dpad |= vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP
    elif hat_y == -1:
        dpad |= vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN
    if hat_x == -1:
        dpad |= vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT
    elif hat_x == 1:
        dpad |= vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
    return dpad


def _float_to_stick_int(value: float) -> int:
    """Convert -1.0..1.0 float to -32768..32767 int for vgamepad."""
    clamped = max(-1.0, min(1.0, value))
    if clamped >= 0:
        return int(clamped * 32767)
    return int(clamped * 32768)


def _float_to_trigger_byte(value: float) -> int:
    """Convert 0.0..1.0 float to 0..255 byte for vgamepad trigger."""
    return int(max(0.0, min(1.0, value)) * 255)


# ── Controller Polling ────────────────────────────────────────────────

class ControllerPoller:
    """
    Reads raw gamepad input via pygame, feeds it into the engine,
    and outputs processed values to a virtual Xbox 360 controller via vgamepad.

    Runs in its own thread at high frequency (~500 Hz target).
    """

    def __init__(self, engine: InputEngine) -> None:
        self.engine = engine
        self._running = False
        self._thread: threading.Thread | None = None
        self.controller_connected = False
        self.controller_name = "None"
        self.virtual_pad_active = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _poll_loop(self) -> None:
        """Main polling loop. Reads controller, processes, outputs to virtual pad."""
        pygame.init()
        pygame.joystick.init()

        joystick = None
        virtual_pad = None

        # Create virtual Xbox 360 controller
        if VGAMEPAD_AVAILABLE:
            try:
                virtual_pad = vg.VX360Gamepad()
                self.virtual_pad_active = True
                print("[+] Virtual Xbox 360 controller created")
            except Exception as e:
                print(f"[!] Could not create virtual controller: {e}")
                print("[!] Make sure ViGEmBus is installed:")
                print("    https://github.com/nefarius/ViGEmBus/releases")
                self.virtual_pad_active = False
        else:
            print("[!] vgamepad not installed — virtual controller disabled")
            print("[!] Run: pip install vgamepad")

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
                    print(f"[+] Controller detected: {self.controller_name}")
                    print(f"    Axes: {joystick.get_numaxes()}, "
                          f"Buttons: {joystick.get_numbuttons()}, "
                          f"Hats: {joystick.get_numhats()}")
                else:
                    self.controller_connected = False
                    self.controller_name = "No controller"
                    time.sleep(0.5)
                    continue

            try:
                num_axes = joystick.get_numaxes()
                num_buttons = joystick.get_numbuttons()
                num_hats = joystick.get_numhats()

                # ── Read raw stick values ──
                # DualSense: LS=0,1  RS=2,3  L2=4  R2=5
                ls_x = joystick.get_axis(0) if num_axes > 0 else 0.0
                ls_y = joystick.get_axis(1) if num_axes > 1 else 0.0
                rs_x = joystick.get_axis(2) if num_axes > 2 else 0.0
                rs_y = joystick.get_axis(3) if num_axes > 3 else 0.0
                l2_raw = joystick.get_axis(4) if num_axes > 4 else 0.0
                r2_raw = joystick.get_axis(5) if num_axes > 5 else 0.0

                # Normalize triggers from (-1..1) to (0..1)
                l2 = (l2_raw + 1.0) / 2.0
                r2 = (r2_raw + 1.0) / 2.0

                # Feed raw values into engine
                self.engine.set_raw_input(ls_x, ls_y, rs_x, rs_y, l2)

                # Run processing tick
                self.engine.process_tick()

                # ── Output to virtual controller ──
                if virtual_pad is not None:
                    self._update_virtual_pad(
                        virtual_pad, joystick,
                        ls_x, ls_y, rs_x, rs_y, l2, r2,
                        num_buttons, num_hats,
                    )

            except pygame.error:
                joystick = None
                self.controller_connected = False
                self.controller_name = "Disconnected"
                print("[!] Controller disconnected")
                continue

            # ~500 Hz polling (2ms sleep)
            time.sleep(0.002)

        # Cleanup
        if virtual_pad is not None:
            virtual_pad.reset()
            virtual_pad.update()
        pygame.joystick.quit()
        pygame.quit()

    def _update_virtual_pad(
        self,
        virtual_pad: "vg.VX360Gamepad",
        joystick: pygame.joystick.JoystickType,
        ls_x: float, ls_y: float,
        rs_x: float, rs_y: float,
        l2: float, r2: float,
        num_buttons: int, num_hats: int,
    ) -> None:
        """Send current state to the virtual Xbox 360 controller."""
        ls_out = self.engine.ls_output
        rs_out = self.engine.rs_output
        master_on = self.engine.config.snapshot()["master_enabled"]

        # Reset virtual pad state for clean update
        virtual_pad.reset()

        # Sticks: processed output when master ON, raw passthrough when OFF
        if master_on:
            out_ls_x = ls_out.x
            out_ls_y = ls_out.y
            out_rs_x = rs_out.x
            out_rs_y = rs_out.y
        else:
            out_ls_x = ls_x
            out_ls_y = ls_y
            out_rs_x = rs_x
            out_rs_y = rs_y

        virtual_pad.left_joystick(
            x_value=_float_to_stick_int(out_ls_x),
            y_value=_float_to_stick_int(-out_ls_y),  # vgamepad Y is inverted
        )
        virtual_pad.right_joystick(
            x_value=_float_to_stick_int(out_rs_x),
            y_value=_float_to_stick_int(-out_rs_y),
        )

        # Triggers: always passthrough (no processing on triggers)
        virtual_pad.left_trigger(value=_float_to_trigger_byte(l2))
        virtual_pad.right_trigger(value=_float_to_trigger_byte(r2))

        # Buttons: passthrough all DualSense buttons to Xbox mapping
        for ps_idx, xbox_btn in DUALSENSE_BUTTON_MAP.items():
            if ps_idx < num_buttons and joystick.get_button(ps_idx):
                virtual_pad.press_button(button=xbox_btn)

        # D-Pad from hat
        if num_hats > 0:
            hat = joystick.get_hat(0)
            dpad_flags = _hat_to_dpad(hat[0], hat[1])
            if dpad_flags & vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP:
                virtual_pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
            if dpad_flags & vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN:
                virtual_pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            if dpad_flags & vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT:
                virtual_pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
            if dpad_flags & vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT:
                virtual_pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        # Send update to virtual controller
        virtual_pad.update()


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
    print("=" * 60)
    print("  InputSense 2K Vision — Defensive Creative Module")
    print("  Controller Flow: DualSense -> Engine -> Virtual Xbox -> Game")
    print("=" * 60)
    print()

    if not VGAMEPAD_AVAILABLE:
        print("WARNING: vgamepad is not installed!")
        print("  Install it with: pip install vgamepad")
        print("  Also install ViGEmBus:")
        print("  https://github.com/nefarius/ViGEmBus/releases")
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
    print("IMPORTANT: In your game, select the virtual Xbox controller")
    print("           (not your physical DualSense) as the input device.")
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
