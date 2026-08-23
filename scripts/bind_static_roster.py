#!/usr/bin/env python3
"""Bind Studio lava locomotion onto every roster body that has no walk/run clips."""
from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_ROSTER = _REPO / "data" / "characters" / "roster.json"
_BIND = _REPO / "scripts" / "bind_mesh_to_studio_rig.py"
_DONOR = "char_pudgy_lava_01"


def gltf_anims(path: Path) -> list[str]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        return []
    json_len = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20 : 20 + json_len])
    return [a.get("name", "") for a in doc.get("animations", [])]


def has_loco(anims: list[str]) -> bool:
    return any("walk" in n.lower() or "run" in n.lower() for n in anims)


def main() -> int:
    only = set(sys.argv[1:])
    roster = json.loads(_ROSTER.read_text(encoding="utf-8"))
    failed = 0
    for entry in roster["characters"]:
        asset_id = entry["id"]
        if only and asset_id not in only:
            continue
        glb = _MODELS / asset_id / f"{asset_id}.glb"
        if not glb.is_file():
            print("MISSING", asset_id, file=sys.stderr)
            failed += 1
            continue
        if has_loco(gltf_anims(glb)):
            print("SKIP", asset_id, "(already has locomotion)")
            continue
        cmd = [
            sys.executable,
            str(_BIND),
            "--mesh",
            str(glb),
            "--donor",
            _DONOR,
            "--asset-id",
            asset_id,
            "--notes",
            f"{entry.get('label', asset_id)} — Studio skeleton + lava locomotion",
        ]
        print("+", asset_id)
        proc = subprocess.run(cmd, cwd=_REPO)
        if proc.returncode != 0:
            print("FAIL", asset_id, file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
