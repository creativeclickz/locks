"""
Build script for the Defensive Locks Creative Module.

Run this on your Windows machine with Python 3.11:
    python build_creative_module.py

This will compile defensive_locks.py into a .pyd file
that you can load into 2K Vision / Helios II.

Requirements:
    pip install cython
"""

import os
import sys
import subprocess


def main():
    # Check Python version
    if sys.version_info[:2] != (3, 11):
        print(f"[!] Warning: You are using Python {sys.version_info[0]}.{sys.version_info[1]}")
        print("    The .pyd must match your Helios Python version (3.11)")
        print()

    # Check Cython is installed
    try:
        import Cython
        print(f"[+] Cython {Cython.__version__} found")
    except ImportError:
        print("[!] Cython not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cython"])
        print("[+] Cython installed")

    # Create a stub creative_helper module for compilation
    stub_path = os.path.join(os.path.dirname(__file__), "creative_helper.py")
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
    setup_path = os.path.join(os.path.dirname(__file__), "_setup_cython.py")
    with open(setup_path, "w") as f:
        f.write(setup_content)

    # Build
    print("[*] Compiling defensive_locks.py -> .pyd ...")
    try:
        subprocess.check_call(
            [sys.executable, setup_path, "build_ext", "--inplace"],
            cwd=os.path.dirname(__file__) or ".",
        )
        print()
        print("[+] Build successful!")
        print("[+] Look for: defensive_locks.cp311-win_amd64.pyd")
        print()
        print("To install:")
        print("  1. Copy defensive_locks.cp311-win_amd64.pyd to your")
        print("     2K Vision _creative folder")
        print("  2. In Helios, go to Creative Modules and import it")
    except subprocess.CalledProcessError as e:
        print(f"[!] Build failed: {e}")
        print("[!] Make sure you have a C compiler installed")
        print("    (Visual Studio Build Tools or MinGW)")
    finally:
        # Clean up
        if stub_created and os.path.exists(stub_path):
            os.remove(stub_path)
        if os.path.exists(setup_path):
            os.remove(setup_path)


if __name__ == "__main__":
    main()
