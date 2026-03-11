"""
fetch_all_devices.py
~~~~~~~~~~~~~~~~~~~~
Fetches the current location and status of all FindMy accessories in your
Apple account (AirTags, iPhones, iPads, Macs, etc.).

Usage:
    uv run python findmy_tracker/fetch_all_devices.py

Prerequisites:
    See README.md for how to export and convert your device .plist files.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from findmy import FindMyAccessory
from findmy.reports import AppleAccount, LoginState
from findmy.reports.anisette import LocalAnisetteProvider

# ---------------------------------------------------------------------------
# Config — edit these paths if you want
# ---------------------------------------------------------------------------
ACCOUNT_FILE = Path("account.json")   # cached login session (created on first run)
DEVICE_JSON_DIR = Path("devices/")    # folder containing your converted .json files
ANISETTE_LIBS = Path("ani_libs.bin")  # Anisette libs cache (~200 MB, downloaded once)

# To use a remote Anisette server instead of local, replace LocalAnisetteProvider
# with RemoteAnisetteProvider and pass the server URL:
#
#   from findmy.reports.anisette import RemoteAnisetteProvider
#   def _make_anisette():
#       return RemoteAnisetteProvider("https://your-anisette-server")
#
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)

BATTERY_LABELS: dict[int, str] = {
    0b00: "Full",
    0b01: "Medium",
    0b10: "Low",
    0b11: "Very Low",
}


def battery_level(status: int) -> str:
    """Decode battery level from a FindMy status byte."""
    return BATTERY_LABELS.get((status >> 6) & 0b11, "Unknown")


def _make_anisette() -> LocalAnisetteProvider:
    return LocalAnisetteProvider(libs_path=ANISETTE_LIBS)


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------

def get_or_login() -> AppleAccount:
    """
    Load a cached Apple account session, or perform an interactive login
    with full 2FA support (SMS or Trusted Device).
    """
    anisette = _make_anisette()

    if ACCOUNT_FILE.exists():
        print(f"[auth] Loading saved session from '{ACCOUNT_FILE}' …")
        return AppleAccount.from_json(ACCOUNT_FILE, anisette)

    acc = AppleAccount(anisette)

    email = input("Apple ID email: ").strip()
    password = input("Apple ID password: ").strip()

    state = acc.login(email, password)

    if state == LoginState.REQUIRE_2FA:
        methods = acc.get_2fa_methods()
        print("\nAvailable 2FA methods:")
        for i, method in enumerate(methods):
            print(f"  {i}: {method}")

        choice = int(input("Choose method number: "))
        chosen = methods[choice]
        chosen.request()
        code = input("Enter 2FA code: ").strip()
        chosen.submit(code)

    acc.to_json(ACCOUNT_FILE)
    print(f"[auth] Session saved to '{ACCOUNT_FILE}'.")
    return acc


# ---------------------------------------------------------------------------
# Device loading
# ---------------------------------------------------------------------------

def load_devices(directory: Path) -> list[tuple[FindMyAccessory, Path]]:
    """
    Load all FindMyAccessory objects from *.json files in *directory*.
    Returns a list of (accessory, path) tuples so we can save state later.
    """
    pairs: list[tuple[FindMyAccessory, Path]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            device = FindMyAccessory.from_json(path)
            pairs.append((device, path))
        except Exception as exc:
            print(f"  [skip] {path.name}: {exc}")
    return pairs


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _device_name(device: FindMyAccessory, path: Path) -> str:
    """Return the best human-readable name for a device."""
    return (
        getattr(device, "name", None)
        or getattr(device, "identifier", None)
        or path.stem
    )


def _format_age(timestamp: datetime | None) -> str:
    if timestamp is None:
        return "?"
    # Make sure we compare timezone-aware datetimes
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - timestamp
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s ago"
    if total_seconds < 3600:
        return f"{total_seconds // 60}m ago"
    if total_seconds < 86400:
        return f"{total_seconds // 3600}h ago"
    return f"{total_seconds // 86400}d ago"


def print_results(
    device_pairs: list[tuple[FindMyAccessory, Path]],
    locations: dict,
) -> None:
    """Pretty-print a table of device locations."""
    col = {"name": 30, "lat": 10, "lon": 11, "acc": 9, "bat": 10, "age": 12}
    header = (
        f"{'Device':<{col['name']}} "
        f"{'Latitude':>{col['lat']}} "
        f"{'Longitude':>{col['lon']}} "
        f"{'Accuracy':>{col['acc']}} "
        f"{'Battery':<{col['bat']}} "
        f"Last Seen"
    )
    print()
    print(header)
    print("─" * (sum(col.values()) + len(col) + 5))

    for device, path in device_pairs:
        name = _device_name(device, path)
        location = locations.get(device)

        if location is None:
            print(f"{name:<{col['name']}}  (no location report available)")
            continue

        bat = battery_level(location.status)
        age = _format_age(getattr(location, "timestamp", None))
        print(
            f"{name:<{col['name']}} "
            f"{location.latitude:>{col['lat']}.5f} "
            f"{location.longitude:>{col['lon']}.5f} "
            f"{location.accuracy:>{col['acc']}.0f}m "
            f"{bat:<{col['bat']}} "
            f"{age}"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    DEVICE_JSON_DIR.mkdir(exist_ok=True)

    # 1. Load device key files
    device_pairs = load_devices(DEVICE_JSON_DIR)
    if not device_pairs:
        print(
            f"\nNo device .json files found in '{DEVICE_JSON_DIR}/'.\n\n"
            "Export your device keys from your Mac and convert them:\n\n"
            "  # Copy plist files\n"
            "  cp ~/Library/Application\\ Support/com.apple.icloud.searchpartyd/"
            "OwnedBeacons/*.plist ./plists/\n\n"
            "  # Convert each plist -> json\n"
            "  for f in plists/*.plist; do\n"
            '    uv run python -m findmy plist2json "$f" '
            '-o "devices/$(basename "$f" .plist).json"\n'
            "  done\n"
        )
        return

    print(f"Loaded {len(device_pairs)} device(s) from '{DEVICE_JSON_DIR}/'.")

    # 2. Authenticate
    acc = get_or_login()
    print(f"[auth] Signed in as {acc.account_name} ({acc.first_name} {acc.last_name})")

    # 3. Fetch locations
    devices = [d for d, _ in device_pairs]
    print(f"\nFetching locations for {len(devices)} device(s) …")
    locations = acc.fetch_location(devices)

    # 4. Print results
    print_results(device_pairs, locations)

    # 5. Persist updated session and device states
    acc.to_json(ACCOUNT_FILE)
    for device, path in device_pairs:
        device.to_json(path)

    print(f"\nSession and device states saved. Run again anytime to refresh.\n")


if __name__ == "__main__":
    main()
