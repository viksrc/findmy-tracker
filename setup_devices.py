"""
setup_devices.py
~~~~~~~~~~~~~~~~
One-shot setup: uses `python -m findmy decrypt` to read all FindMy accessories
directly from the Mac keychain and saves each device as a .json file in devices/.

Run once (on a Mac) before using fetch_all_devices.py:

    uv run python setup_devices.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DEVICE_DIR = Path("devices")


def main() -> None:
    print("=== FindMy Tracker — Device Setup ===\n")

    if sys.platform != "darwin":
        print("ERROR: Must be run on a Mac.")
        sys.exit(1)

    print("Reading devices from FindMy keychain (may prompt for keychain access)...\n")

    result = subprocess.run(
        [sys.executable, "-m", "findmy", "decrypt"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("ERROR: findmy decrypt failed.")
        print(result.stderr.strip())
        print("\nMake sure your terminal has Full Disk Access:")
        print("  System Settings -> Privacy & Security -> Full Disk Access")
        sys.exit(1)

    try:
        devices = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("ERROR: Could not parse output from findmy decrypt.")
        print(result.stdout[:500])
        sys.exit(1)

    if not devices:
        print("No devices found. Make sure you're signed into iCloud with FindMy enabled.")
        sys.exit(0)

    DEVICE_DIR.mkdir(exist_ok=True)

    print(f"Found {len(devices)} device(s):\n")
    for device in devices:
        name = device.get("name") or device.get("identifier") or "unknown"
        identifier = device.get("identifier") or name
        # Sanitise filename
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()
        out_path = DEVICE_DIR / f"{safe_name}.json"

        with open(out_path, "w") as f:
            json.dump(device, f, indent=2)

        model = device.get("model", "unknown model")
        print(f"  Saved: {out_path}  ({model})")

    print(f"\nDone! {len(devices)} device(s) saved to '{DEVICE_DIR}/'.")
    print("\nNext step — fetch locations:")
    print("  uv run python main.py")


if __name__ == "__main__":
    main()
