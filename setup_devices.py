"""
setup_devices.py
~~~~~~~~~~~~~~~~
One-shot setup script: copies FindMy .plist files from their default Mac
location and converts them to the JSON format required by findmy-tracker.

Run once (on a Mac) before using fetch_all_devices.py:

    uv run python setup_devices.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Apple stores FindMy keys here on macOS
SEARCHPARTYD = Path.home() / "Library/Application Support/com.apple.icloud.searchpartyd"
OWNED_BEACONS = SEARCHPARTYD / "OwnedBeacons"        # AirTags, FindMy accessories
PARTICIPATING = SEARCHPARTYD / "ParticipatingDevices" # iPhone, iPad, Mac, etc.

PLIST_DIR = Path("plists")
DEVICE_DIR = Path("devices")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_macos() -> None:
    if sys.platform != "darwin":
        print("ERROR: This setup script must be run on a Mac.")
        print("       The device key files only exist on a Mac paired to your Apple account.")
        sys.exit(1)


def check_source_dirs() -> None:
    missing = [p for p in (OWNED_BEACONS, PARTICIPATING) if not p.exists()]
    if missing:
        print("WARNING: The following FindMy data directories were not found:")
        for p in missing:
            print(f"  {p}")
        print()
        print("This usually means FindMy has not stored any device keys here yet.")
        print("Make sure you are signed into iCloud and have FindMy enabled.")
        if not OWNED_BEACONS.exists() and not PARTICIPATING.exists():
            sys.exit(1)


def copy_plists() -> list[Path]:
    """Copy all .plist files from both source dirs into PLIST_DIR."""
    PLIST_DIR.mkdir(exist_ok=True)
    copied: list[Path] = []

    for source_dir in (OWNED_BEACONS, PARTICIPATING):
        if not source_dir.exists():
            continue
        plists = list(source_dir.glob("*.plist"))
        if not plists:
            print(f"  No .plist files found in {source_dir}")
            continue
        for src in plists:
            dst = PLIST_DIR / src.name
            shutil.copy2(src, dst)
            copied.append(dst)
            print(f"  Copied: {src.name}")

    return copied


def convert_plists(plist_files: list[Path]) -> int:
    """Convert each .plist to .json using the findmy CLI."""
    DEVICE_DIR.mkdir(exist_ok=True)
    success = 0

    for plist_path in plist_files:
        json_path = DEVICE_DIR / plist_path.with_suffix(".json").name
        print(f"  Converting {plist_path.name} -> {json_path} ...", end=" ")

        result = subprocess.run(
            [
                sys.executable, "-m", "findmy",
                "plist2json", str(plist_path),
                "-o", str(json_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("OK")
            success += 1
        else:
            print("FAILED")
            print(f"    stdout: {result.stdout.strip()}")
            print(f"    stderr: {result.stderr.strip()}")

    return success


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== FindMy Tracker — Device Setup ===\n")

    # 1. Platform check
    check_macos()

    # 2. Verify source dirs exist
    check_source_dirs()

    # 3. Copy .plist files
    print(f"Step 1: Copying .plist files to '{PLIST_DIR}/' ...")
    plist_files = copy_plists()

    if not plist_files:
        print("\nNo .plist files were found. Nothing to do.")
        sys.exit(0)

    print(f"\nCopied {len(plist_files)} file(s).\n")

    # 4. Convert to JSON
    print(f"Step 2: Converting .plist files to JSON in '{DEVICE_DIR}/' ...")
    converted = convert_plists(plist_files)

    # 5. Summary
    print()
    print(f"Done! {converted}/{len(plist_files)} device(s) converted successfully.")
    print()

    if converted == 0:
        print("No devices were converted. Check the errors above.")
        sys.exit(1)

    print("You can now fetch device locations with:")
    print("  uv run python findmy_tracker/fetch_all_devices.py")
    print()

    # Reminder: Full Disk Access
    print("NOTE: If you got 'Permission denied' errors, grant your terminal")
    print("      Full Disk Access in:")
    print("      System Settings -> Privacy & Security -> Full Disk Access")


if __name__ == "__main__":
    main()
