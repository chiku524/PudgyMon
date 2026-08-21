# Copy a Unity player build into dist/PudgyMon for playtesters.
# First: Unity Hub → File → Build Settings → Windows → Build into unity/Builds/Windows/
# Usage: pwsh scripts/build_windows_release.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$UnityBuild = Join-Path $Root "unity\Builds\Windows"
$Out = Join-Path $Root "dist\PudgyMon"
if (Test-Path $Out) { Remove-Item -Recurse -Force $Out }
New-Item -ItemType Directory -Path $Out | Out-Null

if (Test-Path $UnityBuild) {
    Copy-Item -Recurse (Join-Path $UnityBuild "*") $Out
} else {
    Write-Host "No unity/Builds/Windows yet — copy data/assets for a drop folder."
}

New-Item -ItemType Directory -Path (Join-Path $Out "assets") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Out "data") -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $Root "assets\*") (Join-Path $Out "assets")
Copy-Item -Recurse -Force (Join-Path $Root "data\*") (Join-Path $Out "data")

@"
PudgyMon: Party Saga (Unity)

Open the Unity player if present, or open unity/ in Unity Hub and press Play.

Boots into The Nest — walk a glowing pad, press E to play.
Pads: Race · Vibe · Shooter · Hill · Party Saga
Create Map (orange) / My Maps (purple)
Controls: WASD · C skins · N crew · H hat · M Boing claim · Ctrl+O companion
Esc pause · H host LAN · J join 127.0.0.1 · R rematch · Q Nest

Command line: PudgyMon.exe --host --port 7777
               PudgyMon.exe --join --address 192.168.1.10 --port 7777

Claim logs: %LOCALAPPDATA%\PudgyMon\logs\claim_voucher.json
Maps:       %LOCALAPPDATA%\PudgyMon\maps\
"@ | Set-Content -Path (Join-Path $Out "README.txt") -Encoding UTF8

Write-Host "Ready: $Out"
