# Packaging & playtester builds

**PudgyMon: Party Saga** — Nest plaza, mini-games, season points, optional Boing Network rewards.

## Windows release folder

```powershell
pwsh scripts/build_windows_release.ps1
```

Output: `dist/PudgyMon/` with the Unity player (if you built to `unity/Builds/Windows/`), plus `assets/`, `data/`, and `README.txt`.

Build the player first in Unity: **File → Build Settings → Windows → Build**.

### In-game

- Boots into **The Nest** (no main menu)
- Walk glowing pads: Race · Vibe · Shooter · Hill · Party Saga → **E** / Enter to start
- **Create Map** (orange) / **My Maps** (purple) — see [MAP_CREATOR.md](MAP_CREATOR.md)
- **Esc** pause (H host LAN · J join · A accounts site)
- **C** cycle skins · **N** crew · **H** hat · **M** claim voucher · **Ctrl+O** claim companion
- **R** rematch · **Q** return to Nest

### LAN

```text
PudgyMon.exe --host --port 7777
PudgyMon.exe --join --address 192.168.1.10 --port 7777
```

Or pause **H** / **J**. Host is listen-server authority.

## Crash / log path

`%LOCALAPPDATA%\PudgyMon\logs\crash.log`  
Claim vouchers: `%LOCALAPPDATA%\PudgyMon\logs\claim_voucher.json`

## Boing

See [BOING_INTEGRATION.md](BOING_INTEGRATION.md).

## Steam

See [STEAM.md](STEAM.md).
