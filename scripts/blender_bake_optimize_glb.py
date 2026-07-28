#!/usr/bin/env python3
"""Bake-optimize Tripo GLBs: closed low-poly + painted diffuse (no holes, faster loads).

Restores from `.glb.pre_opt` when present, then runs Blender:
  - Static props/acc/env: voxel remesh → decimate → smart UV → bake DIFFUSE → toon mat
  - Skinned characters: prefer `scripts/blender_char_optimize_glb.py` (remesh + bake +
    weight transfer). This script's skinned branch only hole-fills + mild-decimates and
    can still tear Tripo topology.

Usage:
  python scripts/blender_bake_optimize_glb.py --batch assets/models --glob "*/*.glb" --from-pre-opt
  python scripts/blender_bake_optimize_glb.py assets/models/env_nest_bench_01/env_nest_bench_01.glb --from-pre-opt
  python scripts/blender_char_optimize_glb.py --all --from-pre-opt
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_INNER = Path(__file__).resolve().parent / "_blender_bake_optimize_inner.py"

# Aggressive but bake-safe budgets (paint lives in the texture now).
_FACE_BUDGET = {
    "char_": 36_000,
    "oceanic_": 36_000,
    "npc_": 36_000,
    "acc_": 6_000,
    "prop_": 8_000,
    "env_": 10_000,
    "vfx_": 3_000,
}

# PNG atlases; 1024 + island-aware face boost keeps painted eyes readable.
_TEX_SIZE = {
    "char_": 1024,
    "oceanic_": 1024,
    "npc_": 1024,
    "acc_": 512,
    "prop_": 1024,
    "env_": 1024,
    "vfx_": 256,
}


def _blender_bin() -> str:
    env = os.environ.get("STUDIO_BLENDER_BIN") or os.environ.get("BLENDER_BIN")
    if env and Path(env).is_file():
        return env
    candidates = [
        Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
        Path("/usr/bin/blender"),
        Path("/Applications/Blender.app/Contents/MacOS/Blender"),
    ]
    which = shutil.which("blender")
    if which:
        candidates.insert(0, Path(which))
    for c in candidates:
        if c.is_file():
            return str(c)
    raise RuntimeError("Blender not found — set STUDIO_BLENDER_BIN")


def _prefix_lookup(path: Path, table: dict[str, int], default: int) -> int:
    name = path.stem.lower()
    for prefix, val in table.items():
        if name.startswith(prefix):
            return val
    return default


def _dilate_atlases(glb_path: Path) -> None:
    """Flood the black bake background with nearest island colors.

    Bilinear sampling at UV island borders reads background texels; if
    those stay pure black every island edge renders as dark speckling.
    Iterative 8-neighbour dilation pushes island colors outward until
    the whole atlas is covered.
    """
    import io
    import json
    import struct

    import numpy as np
    from PIL import Image

    data = glb_path.read_bytes()
    if data[:4] != b"glTF":
        return
    off = 12
    gltf = None
    bin_chunk = b""
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8 : off + 8 + clen]
        if ctype == 0x4E4F534A:
            gltf = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        off += 8 + clen
    if gltf is None or not gltf.get("images"):
        return

    bin_out = bytearray(bin_chunk)
    changed = False
    for idx, img_def in enumerate(gltf["images"]):
        bv = gltf["bufferViews"][img_def["bufferView"]]
        blob = bin_chunk[bv["byteOffset"] : bv["byteOffset"] + bv["byteLength"]]
        im = Image.open(io.BytesIO(blob)).convert("RGB")
        px = np.asarray(im).astype(np.uint8)
        empty = px.max(axis=2) < 8  # bake background is pure black
        frac = float(empty.mean())
        if frac < 0.002:
            continue
        filled = px.copy()
        mask = empty.copy()
        # Each pass fills one texel ring outward from the islands; the
        # bake's own 32px EXTEND margin sits underneath, so 12 rings is
        # belt-and-braces for bilinear sampling. The distant background
        # gets one flat mean color, which PNG compresses to nothing.
        for _ in range(12):
            if not mask.any():
                break
            grew = False
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                src_col = np.roll(np.roll(filled, dy, axis=0), dx, axis=1)
                src_mask = np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
                take = mask & ~src_mask
                if take.any():
                    filled[take] = src_col[take]
                    mask = mask & src_mask
                    grew = True
            if not grew:
                break
        if mask.any():
            filled[mask] = px[~empty].mean(axis=0).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(filled).save(buf, format="PNG", optimize=True)
        png = buf.getvalue()
        while len(bin_out) % 4:
            bin_out.append(0)
        gltf["bufferViews"].append(
            {"buffer": 0, "byteOffset": len(bin_out), "byteLength": len(png)}
        )
        bin_out.extend(png)
        img_def["bufferView"] = len(gltf["bufferViews"]) - 1
        img_def["mimeType"] = "image/png"
        changed = True
        print(f"dilate {glb_path.name} img{idx}: filled {frac * 100:.1f}% background")

    if not changed:
        return
    while len(bin_out) % 4:
        bin_out.append(0)
    gltf["buffers"][0]["byteLength"] = len(bin_out)
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_out)
    with glb_path.open("wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        fh.write(json_bytes)
        fh.write(struct.pack("<II", len(bin_out), 0x004E4942))
        fh.write(bytes(bin_out))


def _safe_copy(src: Path, dst: Path, *, attempts: int = 10) -> None:
    last: Exception | None = None
    for i in range(attempts):
        try:
            shutil.copy2(src, dst)
            return
        except OSError as exc:
            last = exc
            time.sleep(0.2 * (i + 1))
    raise RuntimeError(f"copy failed {src} -> {dst}: {last}")


def optimize_one(
    src: Path,
    *,
    faces: int | None = None,
    tex_size: int | None = None,
    from_pre_opt: bool = False,
    dry_run: bool = False,
) -> dict:
    src = src.resolve()
    if not src.is_file():
        raise FileNotFoundError(src)

    budget = faces if faces is not None else _prefix_lookup(src, _FACE_BUDGET, 8_000)
    tex = tex_size if tex_size is not None else _prefix_lookup(src, _TEX_SIZE, 512)
    bak = src.with_suffix(src.suffix + ".pre_opt")

    if dry_run:
        before = bak.stat().st_size if (from_pre_opt and bak.is_file()) else src.stat().st_size
        print(
            f"dry-run {src.name}: faces={budget} tex={tex} "
            f"from_pre_opt={int(from_pre_opt)} ({before / 1e6:.2f} MB)"
        )
        return {"path": str(src), "before": before, "after": before}

    if from_pre_opt and bak.is_file():
        _safe_copy(bak, src)
        print(f"restored dense source from {bak.name}")
    elif bak.is_file() and bak.stat().st_size > src.stat().st_size * 1.05:
        _safe_copy(bak, src)
        print(f"restored denser backup from {bak.name}")
    elif not bak.is_file():
        _safe_copy(src, bak)
        print(f"backup -> {bak.name}")

    before = src.stat().st_size
    blender = _blender_bin()

    # Already game-sized skinned mesh — skip (avoids re-export bloat).
    if src.stem.lower().startswith(("char_", "oceanic_", "npc_")) and before <= 1.8e6:
        print(f"skip {src.name}: already compact skinned mesh ({before / 1e6:.2f} MB)")
        return {"path": str(src), "before": before, "after": before, "saved": 0.0}

    with tempfile.TemporaryDirectory(prefix="pudgy_bake_") as tmp:
        out_glb = Path(tmp) / "baked.glb"
        cmd = [
            blender,
            "--background",
            "--python",
            str(_INNER),
            "--",
            str(src),
            str(out_glb),
            str(budget),
            str(tex),
        ]
        print(f"+ blender bake-optimize {src.name} -> ~{budget:,} tris tex={tex}")
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in (proc.stdout or "").splitlines():
            if any(
                k in line
                for k in (
                    "BAKE_",
                    "static ",
                    "skinned ",
                    "remesh ",
                    "decimate ",
                    "bake ",
                    "uv-boost",
                    "warn:",
                    "Error",
                    "Traceback",
                )
            ):
                safe = line.encode("ascii", "replace").decode("ascii")
                print(safe)
        if proc.returncode != 0 or not out_glb.is_file():
            tail = ((proc.stderr or "") + (proc.stdout or ""))[-3000:]
            raise RuntimeError(f"bake-optimize failed for {src.name}:\n{tail}")

        _dilate_atlases(out_glb)
        _safe_copy(out_glb, src)

    after = src.stat().st_size
    saved = 1.0 - (after / before) if before else 0.0
    print(
        f"BAKE_OK {src.name}: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB "
        f"({saved:.0%} smaller)"
    )
    return {"path": str(src), "before": before, "after": after, "saved": saved}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--batch", type=Path, default=None)
    parser.add_argument("--glob", default="**/*.glb")
    parser.add_argument("--faces", type=int, default=None)
    parser.add_argument("--tex-size", type=int, default=None)
    parser.add_argument("--from-pre-opt", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files: list[Path] = list(args.paths)
    if args.batch is not None:
        files.extend(sorted(args.batch.resolve().glob(args.glob)))
    files = [
        f
        for f in files
        if f.is_file() and f.suffix.lower() == ".glb" and ".pre_opt" not in f.name
    ]
    seen: set[Path] = set()
    uniq: list[Path] = []
    for f in files:
        rp = f.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(rp)
    files = uniq
    if not files:
        print("error: no GLB inputs", file=sys.stderr)
        return 1
    if not _INNER.is_file():
        print(f"error: missing {_INNER}", file=sys.stderr)
        return 1

    total_b = total_a = 0
    failed = 0
    for path in files:
        try:
            stats = optimize_one(
                path,
                faces=args.faces,
                tex_size=args.tex_size,
                from_pre_opt=args.from_pre_opt,
                dry_run=args.dry_run,
            )
            total_b += stats["before"]
            total_a += stats["after"]
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"error: {path}: {exc}", file=sys.stderr)

    if len(files) > 1 and total_b:
        print(
            f"TOTAL {total_b / 1e6:.1f} MB -> {total_a / 1e6:.1f} MB "
            f"({1.0 - total_a / total_b:.0%} smaller), "
            f"{len(files) - failed}/{len(files)} ok"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
