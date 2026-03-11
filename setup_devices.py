"""
setup_devices.py
~~~~~~~~~~~~~~~~
One-shot setup: uses `python -m findmy decrypt --out-dir devices/` to read all
FindMy accessories from the Mac keychain and save each as a .json file.

Run once (on your Mac with Full Disk Access enabled for Terminal):

    uv run python setup_devices.py

After this, you can fetch locations from any machine:

    uv run python main.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEVICE_DIR = Path("devices")


def main() -> None:
    print("=== FindMy Tracker — Device Setup ===\n")

    if sys.platform != "darwin":
        print("ERROR: Must be run on a Mac with the FindMy app signed in.")
        sys.exit(1)

    DEVICE_DIR.mkdir(exist_ok=True)

    print("Decrypting devices from FindMy keychain...")
    print("(You may be prompted for keychain access.)\n")

    result = subprocess.run(
        [sys.executable, "-m", "findmy", "decrypt", "--out-dir", str(DEVICE_DIR)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("ERROR: findmy decrypt failed.\n")
        if result.stderr:
            print(result.stderr.strip())
        if result.stdout:
            print(result.stdout.strip())
        print(
            "\nTroubleshooting:\n"
            "  1. Make sure Terminal/iTerm has Full Disk Access:\n"
            "     System Settings -> Privacy & Security -> Full Disk Access\n"
            "  2. Make sure you're signed into iCloud with FindMy enabled.\n"
            "  3. Try running manually:  uv run python -m findmy decrypt\n"
        )
        sys.exit(1)

    # Show what was saved
    saved = sorted(DEVICE_DIR.glob("*.json"))
    if not saved:
        print("No devices found. Make sure FindMy is enabled in iCloud settings.")
        sys.exit(0)

    print(f"Saved {len(saved)} device(s) to '{DEVICE_DIR}/':\n")
    for path in saved:
        print(f"  {path.name}")

    print(f"\nDone! Now fetch locations with:\n  uv run python main.py\n")


if __name__ == "__main__":
    main()
