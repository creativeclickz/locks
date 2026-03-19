"""
Build script for the Defensive Locks Creative Module.

This script automatically finds Python 3.11 on your system (required by Helios)
and compiles defensive_locks.py into a .pyd that loads in 2K Vision / Helios II.

Usage:
    python build_creative_module.py

Requirements:
    - Python 3.11 installed (does NOT need to be your default Python)
    - Cython (auto-installed if missing)
    - A C compiler (Visual Studio Build Tools)
"""

import os
import sys
import subprocess
import glob as glob_module


def _find_python311() -> str:
    """
    Find Python 3.11 on the system. Checks common install locations on Windows.
    Returns the path to the python.exe, or exits with instructions if not found.
    """
    # If we're already running 3.11, use current interpreter
    if sys.version_info[:2] == (3, 11):
        return sys.executable

    # Common Windows install locations for Python 3.11
    search_paths = [
        # Standard user install
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe"),
        # System-wide install
        r"C:\Python311\python.exe",
        r"C:\Program Files\Python311\python.exe",
        r"C:\Program Files (x86)\Python311\python.exe",
        # Windows Store / py launcher
        # Also check common custom locations
        os.path.expanduser(r"~\Python311\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\python.exe"),
    ]

    # Also try glob for versioned installs
    for pattern in [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python31*\python.exe"),
        r"C:\Python31*\python.exe",
    ]:
        search_paths.extend(glob_module.glob(pattern))

    for path in search_paths:
        if os.path.isfile(path):
            # Verify it's actually 3.11
            try:
                result = subprocess.run(
                    [path, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
                    capture_output=True, text=True, timeout=10,
                )
                version = result.stdout.strip()
                if version == "3.11":
                    return path
            except (subprocess.SubprocessError, OSError):
                continue

    # Try the py launcher (Windows Python Launcher)
    try:
        result = subprocess.run(
            ["py", "-3.11", "-c", "import sys; print(sys.executable)"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            py_path = result.stdout.strip()
            if os.path.isfile(py_path):
                return py_path
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    # Not found — give clear instructions
    print("=" * 60)
    print("  ERROR: Python 3.11 not found!")
    print("=" * 60)
    print()
    print(f"  Your current Python is {sys.version_info[0]}.{sys.version_info[1]},")
    print("  but Helios requires modules compiled with Python 3.11.")
    print()
    print("  Install Python 3.11 from:")
    print("  https://www.python.org/downloads/release/python-3110/")
    print()
    print("  Download: 'Windows installer (64-bit)'")
    print("  Install it (you don't need to make it your default).")
    print("  Then run this script again.")
    print()
    print("  If Python 3.11 IS installed but not found, you can")
    print("  run the build directly with:")
    print(r'  "C:\path\to\python311\python.exe" build_creative_module.py')
    print()
    sys.exit(1)


def main():
    print("=" * 60)
    print("  Defensive Locks — Creative Module Builder")
    print("  Target: Python 3.11 (Helios / 2K Vision)")
    print("=" * 60)
    print()

    # Find Python 3.11
    python311 = _find_python311()
    print(f"[+] Using Python 3.11: {python311}")

    # Ensure Cython is installed for Python 3.11
    try:
        subprocess.check_call(
            [python311, "-c", "import Cython"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print("[+] Cython is installed")
    except subprocess.CalledProcessError:
        print("[*] Installing Cython for Python 3.11...")
        subprocess.check_call(
            [python311, "-m", "pip", "install", "cython"],
        )
        print("[+] Cython installed")

    # Ensure setuptools is available
    try:
        subprocess.check_call(
            [python311, "-c", "import setuptools"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("[*] Installing setuptools for Python 3.11...")
        subprocess.check_call(
            [python311, "-m", "pip", "install", "setuptools"],
        )

    # Create a stub creative_helper module for compilation
    script_dir = os.path.dirname(os.path.abspath(__file__))
    stub_path = os.path.join(script_dir, "creative_helper.py")
    stub_created = False
    if not os.path.exists(stub_path):
        with open(stub_path, "w") as f:
            f.write(
                "# Stub for compilation only - Helios provides the real module\n"
                "MAX_AXIS = 32767\n"
                "STICK_1_X = 0\n"
                "STICK_1_Y = 1\n"
                "STICK_2_X = 2\n"
                "STICK_2_Y = 3\n"
                "BUTTON_5 = 4\n"
                "def get_val(idx): return 0\n"
                "def set_val(idx, val): pass\n"
                "def get_actual(idx): return 0\n"
            )
        stub_created = True
        print("[+] Created creative_helper stub for compilation")

    # Create setup.py for Cython build
    setup_content = '''
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "defensive_locks.py",
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
    ),
)
'''
    setup_path = os.path.join(script_dir, "_setup_cython.py")
    with open(setup_path, "w") as f:
        f.write(setup_content)

    # Build using Python 3.11
    print()
    print("[*] Compiling defensive_locks.py -> .pyd ...")
    print()
    try:
        subprocess.check_call(
            [python311, setup_path, "build_ext", "--inplace"],
            cwd=script_dir,
        )
        print()
        print("=" * 60)
        print("  BUILD SUCCESSFUL!")
        print("=" * 60)
        print()

        # Find the output .pyd file
        pyd_pattern = os.path.join(script_dir, "defensive_locks*.pyd")
        pyd_files = glob_module.glob(pyd_pattern)
        if pyd_files:
            pyd_name = os.path.basename(pyd_files[0])
            print(f"  Output: {pyd_name}")
        else:
            pyd_name = "defensive_locks.cp311-win_amd64.pyd"
            print(f"  Expected output: {pyd_name}")

        print()
        print("  NEXT STEPS:")
        print(f"  1. Copy {pyd_name} to your 2K Vision _creative folder")
        print("  2. In Helios, go to Creative Modules and import it")
        print()
    except subprocess.CalledProcessError as e:
        print()
        print(f"[!] Build failed: {e}")
        print()
        print("[!] Make sure you have a C compiler installed.")
        print("    Download Visual Studio Build Tools from:")
        print("    https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("    Select 'Desktop development with C++' during install.")
        print()
    finally:
        # Clean up temporary files
        if stub_created and os.path.exists(stub_path):
            os.remove(stub_path)
        if os.path.exists(setup_path):
            os.remove(setup_path)


if __name__ == "__main__":
    main()
