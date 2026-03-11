# findmy-tracker

A Python tool to fetch the **current location and status** of all your Apple FindMy devices — AirTags, iPhones, iPads, Macs, and any FindMy-compatible accessory — from the command line, on any platform.

Built on top of [FindMy.py](https://github.com/malmeloo/FindMy.py).

---

## Features

- Fetches live location reports for all your FindMy accessories
- Shows latitude, longitude, accuracy, battery level, and report age
- Caches your login session so you only need to authenticate once
- Supports SMS and Trusted Device 2FA
- Works on macOS, Linux, and Windows

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Mac to **export your device key files** (one-time setup)

---

## Installation

```bash
# Clone the repo
git clone https://github.com/yourname/findmy-tracker
cd findmy-tracker

# Install dependencies with uv
uv sync
```

---

## Setup: Export Your Device Keys (one-time, requires a Mac)

Apple stores FindMy device keys locally on your Mac. You need to export and convert them once.

### Step 1 — Copy plist files

```bash
mkdir -p plists

# AirTags and accessories you own
cp ~/Library/Application\ Support/com.apple.icloud.searchpartyd/OwnedBeacons/*.plist ./plists/

# Your Apple devices (iPhone, iPad, Mac, etc.)
cp ~/Library/Application\ Support/com.apple.icloud.searchpartyd/ParticipatingDevices/*.plist ./plists/
```

> **Tip:** If you see "permission denied", grant your terminal Full Disk Access in
> `System Settings -> Privacy & Security -> Full Disk Access`.

### Step 2 — Convert plist to JSON

```bash
mkdir -p devices

for f in plists/*.plist; do
  uv run python -m findmy plist2json "$f" -o "devices/$(basename "$f" .plist).json"
done
```

Your `devices/` folder should now contain one `.json` file per device.

---

## Usage

```bash
uv run python findmy_tracker/fetch_all_devices.py
```

**First run** — you will be prompted to sign in with your Apple ID and complete 2FA.
Your session is saved to `account.json` for subsequent runs.

**Subsequent runs** — session is loaded automatically, no login required.

### Example output

```
Loaded 3 device(s) from 'devices/'.
[auth] Signed in as you@icloud.com (Jane Doe)

Fetching locations for 3 device(s) ...

Device                          Latitude   Longitude  Accuracy Battery    Last Seen
------------------------------------------------------------------------------------
My AirTag                      37.33182  -122.03118       10m Full       3m ago
Jane's iPhone                  37.33195  -122.03101        5m Full       1m ago
MacBook Pro                    37.33180  -122.03122       15m Medium     12m ago
```

---

## Project Structure

```
findmy-tracker/
├── findmy_tracker/
│   ├── __init__.py
│   └── fetch_all_devices.py   # main script
├── devices/                   # your converted device .json files (git-ignored)
├── plists/                    # raw exported .plist files (git-ignored)
├── account.json               # cached login session (git-ignored)
├── ani_libs.bin               # Anisette libs cache (git-ignored, ~200 MB)
├── pyproject.toml
└── README.md
```

---

## Configuration

Edit the constants at the top of `findmy_tracker/fetch_all_devices.py`:

| Variable | Default | Description |
|---|---|---|
| `ACCOUNT_FILE` | `account.json` | Where to cache your login session |
| `DEVICE_JSON_DIR` | `devices/` | Folder with converted device JSON files |
| `ANISETTE_LIBS` | `ani_libs.bin` | Local Anisette libs cache path |

### Using a remote Anisette server

If you prefer not to download the ~200 MB local Anisette libs, you can use a remote server.
Edit `_make_anisette()` in `fetch_all_devices.py`:

```python
from findmy.reports.anisette import RemoteAnisetteProvider

def _make_anisette():
    return RemoteAnisetteProvider("https://your-anisette-server")
```

> Warning: Public Anisette servers are community-run and may be unreliable.
> Self-hosting is recommended for production use.

---

## How It Works

1. **Authentication** — Signs into your Apple account using the Anisette protocol (the same handshake Apple devices use). Your session is cached locally.
2. **Key loading** — Loads rolling cryptographic key pairs from the exported device JSON files.
3. **Report fetching** — Queries Apple's FindMy network for the latest location reports encrypted with your device keys.
4. **Decryption** — Decrypts the location data locally using your private keys.

---

## Security and Privacy

- Your Apple credentials and session token are stored **only on your local machine** (`account.json`).
- Device private keys are stored in `devices/` — keep these safe and never commit them.
- Add the following to your `.gitignore`:

```gitignore
account.json
ani_libs.bin
devices/
plists/
```

---

## Limitations

| Limitation | Detail |
|---|---|
| Mac required for key export | Device `.plist` files only exist on a Mac paired to your Apple account |
| No "list all devices" API | Apple does not expose this; you must export keys manually |
| Location freshness | Reports come from nearby Apple devices that spotted yours — may be minutes to hours old |
| 2FA re-prompt | Apple invalidates sessions periodically (~30 days); delete `account.json` to re-authenticate |

---

## Credits

- [FindMy.py](https://github.com/malmeloo/FindMy.py) by [@malmeloo](https://github.com/malmeloo)
- OpenHaystack research by [@seemo-lab](https://github.com/seemoo-lab)
- Authentication work from [@JJTech0130](https://github.com/JJTech0130)'s Pypush
