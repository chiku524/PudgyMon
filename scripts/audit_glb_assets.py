#!/usr/bin/env python3
"""Audit shipped GLBs against the asset-pipeline budgets (no Blender / node needed).

Reports per asset: file size, triangles, vertices, index width, texture
resolution / format / bytes, ORM texture refs, and animation payload. Flags
anything over budget so under-optimized assets are impossible to miss.

Usage:
  python scripts/audit_glb_assets.py                 # audit assets/models
  python scripts/audit_glb_assets.py --root some/dir
  python scripts/audit_glb_assets.py --strict        # exit 1 on any flag
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

# (max_tris, max_tex_edge) by asset id prefix — mirrors the Blender bake
# budgets in blender_bake_optimize_glb.py / blender_char_optimize_glb.py.
_BUDGETS: dict[str, tuple[int, int]] = {
    "char_": (48_000, 1024),
    "oceanic_": (48_000, 1024),
    "npc_": (48_000, 1024),
    "acc_": (14_000, 1024),
    "prop_": (18_000, 1024),
    "env_": (22_000, 1024),
    "vfx_": (6_000, 512),
}
_DEFAULT_BUDGET = (18_000, 1024)
# Headroom before a flag fires (decimate targets are approximate).
_TRIS_SLACK = 1.35

_COMPONENT_BYTES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_TYPE_COMPONENTS = {
    "SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16,
}


def _load_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError("not a GLB")
    off = 12
    gltf, bin_chunk = None, b""
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8 : off + 8 + clen]
        if ctype == 0x4E4F534A:
            gltf = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        off += 8 + clen
    if gltf is None:
        raise ValueError("no JSON chunk")
    return gltf, bin_chunk


def _image_dims(blob: bytes) -> tuple[int, int] | None:
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", blob[16:24])
        return w, h
    if blob[:2] == b"\xff\xd8":  # JPEG: scan for SOF0/1/2 marker
        i = 2
        while i + 9 < len(blob):
            if blob[i] != 0xFF:
                i += 1
                continue
            marker = blob[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", blob[i + 5 : i + 9])
                return w, h
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg_len = struct.unpack(">H", blob[i + 2 : i + 4])[0]
            i += 2 + seg_len
    return None


def _accessor_count(gltf: dict, index: int) -> int:
    return int(gltf.get("accessors", [])[index].get("count", 0))


def audit_glb(path: Path) -> dict:
    gltf, bin_chunk = _load_glb(path)
    views = gltf.get("bufferViews", [])
    accessors = gltf.get("accessors", [])

    tris = verts = 0
    index_types: set[str] = set()
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:  # TRIANGLES
                continue
            if "indices" in prim:
                acc = accessors[prim["indices"]]
                tris += int(acc.get("count", 0)) // 3
                index_types.add({5123: "u16", 5125: "u32"}.get(acc.get("componentType"), "?"))
            elif "POSITION" in prim.get("attributes", {}):
                tris += _accessor_count(gltf, prim["attributes"]["POSITION"]) // 3
            if "POSITION" in prim.get("attributes", {}):
                verts += _accessor_count(gltf, prim["attributes"]["POSITION"])

    textures = []
    for img in gltf.get("images", []):
        blob = b""
        if "bufferView" in img:
            bv = views[img["bufferView"]]
            start = bv.get("byteOffset", 0)
            blob = bin_chunk[start : start + bv["byteLength"]]
        dims = _image_dims(blob)
        textures.append(
            {
                "mime": img.get("mimeType", "?"),
                "bytes": len(blob),
                "dims": dims,
            }
        )

    orm_refs = 0
    for mat in gltf.get("materials", []):
        orm_refs += sum(1 for slot in ("normalTexture", "occlusionTexture") if slot in mat)
        orm_refs += 1 if "metallicRoughnessTexture" in mat.get("pbrMetallicRoughness", {}) else 0

    anim_bytes = 0
    for anim in gltf.get("animations", []):
        for sampler in anim.get("samplers", []):
            for key in ("input", "output"):
                acc = accessors[sampler[key]]
                n = _COMPONENT_BYTES.get(acc.get("componentType"), 4)
                c = _TYPE_COMPONENTS.get(acc.get("type"), 1)
                anim_bytes += int(acc.get("count", 0)) * n * c

    return {
        "size": path.stat().st_size,
        "tris": tris,
        "verts": verts,
        "index_types": index_types,
        "textures": textures,
        "orm_refs": orm_refs,
        "anim_bytes": anim_bytes,
        "anims": len(gltf.get("animations", [])),
        "skinned": bool(gltf.get("skins")),
    }


def _budget_for(name: str) -> tuple[int, int]:
    for prefix, budget in _BUDGETS.items():
        if name.startswith(prefix):
            return budget
    return _DEFAULT_BUDGET


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_REPO / "assets" / "models")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any flag")
    args = parser.parse_args()

    files = sorted(
        f
        for f in args.root.glob("*/*.glb")
        if ".pre_opt" not in f.name and not f.parent.name.startswith("_")
    )
    if not files:
        print(f"no GLBs under {args.root}", file=sys.stderr)
        return 1

    flagged = 0
    total = 0
    for path in files:
        name = path.stem
        try:
            info = audit_glb(path)
        except Exception as exc:  # noqa: BLE001
            print(f"FLAG {name}: unreadable ({exc})")
            flagged += 1
            continue
        total += info["size"]
        max_tris, max_tex = _budget_for(name)

        flags: list[str] = []
        if info["tris"] > max_tris * _TRIS_SLACK:
            flags.append(f"tris {info['tris']:,} > budget {max_tris:,}")
        for tex in info["textures"]:
            if tex["dims"] and max(tex["dims"]) > max_tex:
                flags.append(f"tex {tex['dims'][0]}x{tex['dims'][1]} > {max_tex}")
            if tex["mime"] not in ("image/jpeg", "image/png"):
                flags.append(f"tex mime {tex['mime']}")
        if info["orm_refs"] and not name.startswith(("char_", "oceanic_", "npc_")):
            flags.append(f"{info['orm_refs']} ORM/normal ref(s) — run optimize_glb --preset prop")
        if "u32" in info["index_types"] and info["verts"] < 65_000:
            flags.append("u32 indices on <65k verts")
        if info["anim_bytes"] > 600_000:
            flags.append(f"animation payload {info['anim_bytes'] / 1e6:.1f} MB")

        tex_desc = ", ".join(
            f"{t['dims'][0]}x{t['dims'][1]}" if t["dims"] else t["mime"]
            for t in info["textures"]
        ) or "none"
        status = "FLAG" if flags else "ok  "
        print(
            f"{status} {name:<28} {info['size'] / 1e3:>7.0f} KB  "
            f"tris {info['tris']:>7,}  tex [{tex_desc}]  "
            f"anims {info['anims']} ({info['anim_bytes'] / 1e3:.0f} KB)"
            + (f"  <- {'; '.join(flags)}" if flags else "")
        )
        flagged += 1 if flags else 0

    print(
        f"\n{len(files)} assets, {total / 1e6:.1f} MB total, "
        f"{flagged} flagged"
    )
    return 1 if (flagged and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
