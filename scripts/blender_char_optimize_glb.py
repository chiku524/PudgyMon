#!/usr/bin/env python3
"""Re-optimize skinned Pudgy characters: remesh (no holes) + bake + weight transfer.

Restores from `.glb.pre_opt`, builds a closed low-poly cage, bakes candy diffuse,
transfers skin weights from the dense source, and keeps the armature clips.

Usage:
  python scripts/blender_char_optimize_glb.py --all --from-pre-opt
  python scripts/blender_char_optimize_glb.py char_pudgy_forest_01 --from-pre-opt
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
_MODELS = _REPO / "assets" / "models"
_INNER = Path(__file__).resolve().parent / "_blender_char_optimize_inner.py"

_DEFAULT_CHARS = [
    "char_pudgy_base_01",
    "char_pudgy_forest_01",
    "char_pudgy_lava_01",
    "char_pudgy_sky_01",
    "oceanic_pudgymon_01",
]

# Preserve path keeps Tripo UV paint; tris can go higher since no bake.
_FACE_BUDGET = 36_000
_TEX_SIZE = 1024  # remesh-fallback bake size; preserve path ignores it
_PATH = "preserve"


def _blender_bin() -> str:
    env = os.environ.get("STUDIO_BLENDER_BIN") or os.environ.get("BLENDER_BIN")
    if env and Path(env).is_file():
        return env
    candidates = [
        Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
        Path("/usr/bin/blender"),
    ]
    which = shutil.which("blender")
    if which:
        candidates.insert(0, Path(which))
    for c in candidates:
        if c.is_file():
            return str(c)
    raise RuntimeError("Blender not found")


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


def _simplify_meshopt(glb: Path, target_faces: int) -> None:
    """Decimate with meshopt — UV-seam-safe, unlike Blender collapse."""
    import shutil
    import subprocess
    import tempfile

    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        print(f"warn: npx missing; char stays dense: {glb.name}")
        return
    # Estimate ratio from file's face count is overkill; Tripo crew are
    # all ~180-190k tris, so pick ratio from the budget conservatively.
    ratio = max(0.05, min(0.9, target_faces / 190_000))
    with tempfile.TemporaryDirectory(prefix="pudgy_simplify_") as tmp:
        out = Path(tmp) / "out.glb"
        cmd = [
            npx, "--yes", "@gltf-transform/cli@4.1.1",
            "simplify", str(glb), str(out),
            "--ratio", f"{ratio:.4f}",
            "--error", "0.001",
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if proc.returncode != 0 or not out.is_file():
            print(f"warn: simplify failed for {glb.name}: {(proc.stderr or '')[-400:]}")
            return
        shutil.copy2(out, glb)
        print(f"simplify ok {glb.name} ratio={ratio:.3f}")


def _sharpen_basecolor(glb: Path, target_edge: int = 1024) -> None:
    """Upscale + unsharp the authored basecolor and embed as PNG.

    The Tripo source paint is 512px JPEG — soft eyes are baked into the
    source. Lanczos 2x + a moderate unsharp mask recovers edge contrast,
    and PNG stops any further chroma loss.
    """
    import io
    import json
    import struct

    from PIL import Image, ImageFilter

    data = glb.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError(f"not a GLB: {glb}")
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
    if gltf is None:
        raise ValueError(f"no JSON chunk: {glb}")

    # Basecolor image indices via material references.
    base_imgs: set[int] = set()
    textures = gltf.get("textures", [])
    for mat in gltf.get("materials", []):
        tex_info = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if tex_info is not None:
            src = textures[tex_info["index"]].get("source")
            if src is not None:
                base_imgs.add(src)
    if not base_imgs:
        print(f"warn: no basecolor to sharpen in {glb.name}")
        return

    views = gltf["bufferViews"]
    bin_out = bytearray(bin_chunk)
    for idx in sorted(base_imgs):
        img_def = gltf["images"][idx]
        bv = views[img_def["bufferView"]]
        blob = bin_chunk[bv["byteOffset"] : bv["byteOffset"] + bv["byteLength"]]
        im = Image.open(io.BytesIO(blob)).convert("RGB")
        w, h = im.size
        if max(w, h) < target_edge:
            scale = target_edge / max(w, h)
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=140, threshold=2))
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        png = buf.getvalue()

        while len(bin_out) % 4:
            bin_out.append(0)
        new_view = {"buffer": 0, "byteOffset": len(bin_out), "byteLength": len(png)}
        bin_out.extend(png)
        gltf["bufferViews"].append(new_view)
        img_def["bufferView"] = len(gltf["bufferViews"]) - 1
        img_def["mimeType"] = "image/png"
        print(f"sharpen {glb.name} img{idx}: {w}x{h} -> {im.size[0]}x{im.size[1]} PNG")

    while len(bin_out) % 4:
        bin_out.append(0)
    gltf["buffers"][0]["byteLength"] = len(bin_out)
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_out)
    with glb.open("wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        fh.write(json_bytes)
        fh.write(struct.pack("<II", len(bin_out), 0x004E4942))
        fh.write(bytes(bin_out))


def optimize_one(
    asset_id: str,
    *,
    faces: int = _FACE_BUDGET,
    tex_size: int = _TEX_SIZE,
    path: str = _PATH,
    from_pre_opt: bool = True,
    dry_run: bool = False,
) -> dict:
    src = _MODELS / asset_id / f"{asset_id}.glb"
    if not src.is_file():
        raise FileNotFoundError(src)
    bak = src.with_suffix(src.suffix + ".pre_opt")

    if dry_run:
        before = bak.stat().st_size if (from_pre_opt and bak.is_file()) else src.stat().st_size
        print(f"dry-run {asset_id}: faces={faces} tex={tex_size} ({before / 1e6:.2f} MB)")
        return {"id": asset_id, "before": before, "after": before}

    if from_pre_opt and bak.is_file():
        _safe_copy(bak, src)
        print(f"restored dense source from {bak.name}")
    elif not bak.is_file():
        _safe_copy(src, bak)
        print(f"backup -> {bak.name}")

    before = src.stat().st_size
    with tempfile.TemporaryDirectory(prefix="pudgy_char_") as tmp:
        out_glb = Path(tmp) / "char.glb"
        cmd = [
            _blender_bin(),
            "--background",
            "--python",
            str(_INNER),
            "--",
            str(src),
            str(out_glb),
            str(faces),
            str(tex_size),
            path,
        ]
        print(
            f"+ blender char-optimize {asset_id} -> ~{faces:,} tris "
            f"tex={tex_size} path={path}"
        )
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
                    "CHAR_OPT",
                    "CHAR_PATH",
                    "remesh ",
                    "decimate ",
                    "bake ",
                    "weights ",
                    "drop ",
                    "warn:",
                    "Error",
                    "Traceback",
                    "BOUND",
                )
            ):
                print(line.encode("ascii", "replace").decode("ascii"))
        if proc.returncode != 0 or not out_glb.is_file():
            tail = ((proc.stderr or "") + (proc.stdout or ""))[-3500:]
            raise RuntimeError(f"char-optimize failed for {asset_id}:\n{tail}")
        if path != "remesh":
            _simplify_meshopt(out_glb, faces)
        _sharpen_basecolor(out_glb)
        _safe_copy(out_glb, src)

    after = src.stat().st_size
    print(
        f"CHAR_OK {asset_id}: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB "
        f"({1.0 - after / before:.0%} smaller)"
    )
    return {"id": asset_id, "before": before, "after": after}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_ids", nargs="*", help="Character asset ids")
    parser.add_argument("--all", action="store_true", help="All default crew skins")
    parser.add_argument("--faces", type=int, default=_FACE_BUDGET)
    parser.add_argument("--tex-size", type=int, default=_TEX_SIZE)
    parser.add_argument("--from-pre-opt", action="store_true", default=True)
    parser.add_argument("--no-from-pre-opt", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ids = list(args.asset_ids)
    if args.all or not ids:
        ids = list(_DEFAULT_CHARS)
    from_pre = False if args.no_from_pre_opt else True

    if not _INNER.is_file():
        print(f"error: missing {_INNER}", file=sys.stderr)
        return 1

    failed = []
    total_b = total_a = 0
    for aid in ids:
        try:
            stats = optimize_one(
                aid,
                faces=args.faces,
                tex_size=args.tex_size,
                from_pre_opt=from_pre,
                dry_run=args.dry_run,
            )
            total_b += stats["before"]
            total_a += stats["after"]
        except Exception as exc:  # noqa: BLE001
            failed.append(aid)
            print(f"error: {aid}: {exc}", file=sys.stderr)

    if len(ids) > 1 and total_b:
        print(
            f"TOTAL {total_b / 1e6:.1f} MB -> {total_a / 1e6:.1f} MB "
            f"({1.0 - total_a / total_b:.0%} smaller), "
            f"{len(ids) - len(failed)}/{len(ids)} ok"
        )
    if failed:
        print("failed:", ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
