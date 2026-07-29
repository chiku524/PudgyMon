#!/usr/bin/env python3
"""Automatically import + rig a character GLB into the PudgyMon pipeline.

Detects the incoming file and picks a path:

  • no armature     → dense import + stubby shared rig + procedural clips
                      (`import_dense_character_glb.py` → `rig_and_animate_pudgy.py`)
  • Studio 41-bone  → keep skin weights (`import_rigged_character_glb.py`),
                      optionally copy clips from a same-rig donor
  • stubby 12-bone  → keep / refresh via `rig_and_animate_pudgy.py`
  • unknown rig     → refuse unless `--force stubby|keep`

Short vs tall / wide vs narrow pudgies:
  Pass `--height` (default 1.2) to bake playable height on import. The stubby
  rig places bones as fractions of the mesh AABB (X width, Y depth, Z height)
  and scales envelopes + clip location/rotation by those dimensions vs a
  canonical ~0.85×1.20×1.15 stubby. Clip transfer (`--clip-source`) also
  rescales donor motion by target/donor AABB ratios.
  Example:
    python scripts/auto_rig_glb.py --src short.glb --asset-id char_pudgy_lava_01 --height 0.95
    python scripts/auto_rig_glb.py --src tall.glb  --asset-id char_pudgy_sky_01  --height 1.35

Usage:
  # Static Tripo download → playable stubby-rigged crew
  python scripts/auto_rig_glb.py \\
    --src "C:/Users/.../forest_creature.glb" \\
    --asset-id char_pudgy_forest_01

  # Studio-rigged download; steal locomotion from water
  python scripts/auto_rig_glb.py \\
    --src "C:/Users/.../pink_rigged.glb" \\
    --asset-id char_pudgy_pink_01 \\
    --clip-source char_pudgy_water_01

  # Inspect only
  python scripts/auto_rig_glb.py --src path.glb --inspect
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
_MODELS = _REPO / "assets" / "models"

_STUBBY_MARKERS = {
    "Root",
    "Hips",
    "Spine",
    "Head",
    "L_Arm",
    "R_Arm",
    "L_Leg",
    "R_Leg",
}
_STUDIO_MARKERS = {
    "Root",
    "Hip",
    "Pelvis",
    "L_Thigh",
    "R_Thigh",
    "L_Calf",
    "R_Calf",
}


def _parse_glb_json(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"not a GLB: {path}")
    offset = 12
    while offset + 8 <= len(data):
        clen = struct.unpack_from("<I", data, offset)[0]
        ctype = struct.unpack_from("<I", data, offset + 4)[0]
        chunk = data[offset + 8 : offset + 8 + clen]
        offset += 8 + clen
        if ctype == 0x4E4F534A:
            return json.loads(chunk.decode("utf-8"))
    raise RuntimeError(f"no JSON chunk in {path}")


def inspect_glb(path: Path) -> dict:
    g = _parse_glb_json(path)
    nodes = g.get("nodes", [])
    skins = g.get("skins", [])
    joints: list[str] = []
    if skins:
        joints = [nodes[i].get("name", f"node_{i}") for i in skins[0].get("joints", [])]
    anims = [a.get("name") or f"anim_{i}" for i, a in enumerate(g.get("animations", []))]
    jset = set(joints)
    stubby_hits = len(jset & _STUBBY_MARKERS)
    studio_hits = len(jset & _STUDIO_MARKERS)
    if not joints:
        family = "none"
    elif studio_hits >= 5:
        family = "studio"
    elif stubby_hits >= 6:
        family = "stubby"
    else:
        family = "unknown"
    return {
        "path": str(path),
        "joint_count": len(joints),
        "joints": joints,
        "animations": anims,
        "family": family,
        "stubby_hits": stubby_hits,
        "studio_hits": studio_hits,
    }


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(_REPO))
    return proc.returncode


def _py() -> str:
    return sys.executable


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--src", type=Path, required=True, help="Input character GLB")
    parser.add_argument(
        "--asset-id",
        default="",
        help="Destination asset id (required unless --inspect)",
    )
    parser.add_argument(
        "--force",
        choices=("auto", "stubby", "keep"),
        default="auto",
        help="auto=detect; stubby=re-rig to shared 12-bone; keep=import_rigged only",
    )
    parser.add_argument(
        "--clip-source",
        default="",
        help="Asset id to copy clips from after import (same-rig only, e.g. char_pudgy_water_01)",
    )
    parser.add_argument(
        "--clips",
        default="",
        help="Optional comma list for --clip-source transfer",
    )
    parser.add_argument("--height", type=float, default=1.2)
    parser.add_argument("--max-tex", type=int, default=1024)
    parser.add_argument("--notes", default="")
    parser.add_argument("--inspect", action="store_true", help="Print rig family and exit")
    parser.add_argument(
        "--skip-simplify",
        action="store_true",
        help="Forwarded to stubby re-rig (no gltf-transform pre-pass)",
    )
    args = parser.parse_args()

    if not args.src.is_file():
        print(f"error: missing {args.src}", file=sys.stderr)
        return 1

    info = inspect_glb(args.src)
    print(
        f"inspect: family={info['family']} joints={info['joint_count']} "
        f"studio_hits={info['studio_hits']} stubby_hits={info['stubby_hits']} "
        f"clips={info['animations']}"
    )
    if args.inspect:
        print(json.dumps({k: info[k] for k in info if k != "joints"}, indent=2))
        if info["joints"]:
            print("joints:", ", ".join(info["joints"][:16]), ("..." if info["joint_count"] > 16 else ""))
        return 0

    aid = args.asset_id.strip()
    if not aid:
        print("error: --asset-id is required (or use --inspect)", file=sys.stderr)
        return 1

    family = info["family"]
    mode = args.force
    if mode == "auto":
        if family == "none":
            mode = "stubby"
        elif family == "studio":
            mode = "keep"
        elif family == "stubby":
            # Already on contract armature — refresh weights/clips if empty.
            mode = "stubby" if not info["animations"] else "keep"
        else:
            print(
                "error: unknown armature; pass --force stubby (re-rig) or --force keep",
                file=sys.stderr,
            )
            return 2

    print(f"pipeline: mode={mode} -> asset_id={aid}")
    notes = args.notes or f"auto_rig_glb ({mode}, family={family})"

    if mode == "stubby":
        # 1) Floor / JPEG / sockets as a static body
        rc = _run(
            [
                _py(),
                str(_SCRIPTS / "import_dense_character_glb.py"),
                "--src",
                str(args.src),
                "--asset-id",
                aid,
                "--height",
                str(args.height),
                "--max-tex",
                str(args.max_tex),
                "--notes",
                notes,
            ]
        )
        if rc != 0:
            return rc
        # 2) Shared armature + procedural party clips
        rig_cmd = [
            _py(),
            str(_SCRIPTS / "rig_and_animate_pudgy.py"),
            "--asset-id",
            aid,
        ]
        if args.skip_simplify:
            rig_cmd.append("--skip-simplify")
        rc = _run(rig_cmd)
        if rc != 0:
            return rc
    else:
        # keep existing skin
        if family == "none" and mode == "keep":
            print("error: --force keep needs an armature", file=sys.stderr)
            return 2
        rc = _run(
            [
                _py(),
                str(_SCRIPTS / "import_rigged_character_glb.py"),
                "--src",
                str(args.src),
                "--asset-id",
                aid,
                "--height",
                str(args.height),
                "--max-tex",
                str(args.max_tex),
                "--notes",
                notes,
            ]
        )
        if rc != 0:
            return rc

    if args.clip_source.strip():
        xfer = [
            _py(),
            str(_SCRIPTS / "transfer_crew_clips.py"),
            "--from",
            args.clip_source.strip(),
            "--to",
            aid,
        ]
        if args.clips.strip():
            xfer.extend(["--clips", args.clips.strip()])
        rc = _run(xfer)
        if rc != 0:
            return rc

    out = _MODELS / aid / f"{aid}.glb"
    print(f"AUTO_RIG_OK {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
