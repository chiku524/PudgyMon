#!/usr/bin/env python3
"""Bake-optimize Tripo GLBs: UV-preserve by default (no muddy remesh rebakes).

Restores from `.glb.pre_opt` when present, then:
  - Default **preserve**: weld/dedup + meshopt simplify + strip ORM + PNG
    baseColor (keeps authored UVs/paint — avoids remesh color bleed).
  - Optional **remesh**: Blender voxel remesh → bake DIFFUSE (only when the
    mesh is too broken for preserve).
  - Skinned characters: prefer `scripts/blender_char_optimize_glb.py`.

Usage:
  python scripts/blender_bake_optimize_glb.py --batch assets/models --glob "*/*.glb" --from-pre-opt
  python scripts/blender_bake_optimize_glb.py path.glb --path remesh --from-pre-opt
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

# Quality-first face budgets after meshopt simplify (preserve path).
_FACE_BUDGET = {
    "char_": 48_000,
    "oceanic_": 48_000,
    "npc_": 48_000,
    "acc_": 24_000,
    "prop_": 36_000,
    "env_": 48_000,
    "vfx_": 8_000,
}

# PNG target for authored baseColor. Do not invent detail above Tripo's
# native ~1024 — upscaling only bloated files without fixing paint softness.
_TEX_SIZE = {
    "char_": 1024,
    "oceanic_": 1024,
    "npc_": 1024,
    "acc_": 1024,
    "prop_": 1024,
    "env_": 1024,
    "vfx_": 512,
}

_DEFAULT_PATH = "preserve"


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


def _safe_copy(src: Path, dst: Path, *, attempts: int = 16) -> None:
    last: Exception | None = None
    tmp: Path | None = None
    for i in range(attempts):
        try:
            # Copy to a sibling temp then replace — avoids WinError 1224 when
            # AV / Search Indexer briefly maps the destination GLB.
            tmp = dst.with_suffix(dst.suffix + f".tmp{i}")
            shutil.copy2(src, tmp)
            # os.replace can raise Errno 22 on Windows when the dest is
            # briefly locked; fall back to unlink+move.
            try:
                os.replace(tmp, dst)
            except OSError:
                if dst.is_file():
                    dst.unlink()
                shutil.move(str(tmp), str(dst))
            return
        except OSError as exc:
            last = exc
            time.sleep(0.35 * (i + 1))
            if tmp is not None:
                try:
                    if tmp.is_file():
                        tmp.unlink()
                except OSError:
                    pass
    raise RuntimeError(f"copy failed {src} -> {dst}: {last}")


def _simplify_meshopt(glb: Path, target_faces: int) -> None:
    """UV-seam-safe decimate — keeps authored paint islands intact."""
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        print(f"warn: npx missing; leave dense mesh: {glb.name}")
        return
    # Dense Tripo décor is often ~0.8–1.2M tris; ratio from budget.
    # Error 0.002 is the practical meshopt floor on Tripo split soup —
    # tighter values leave 300k+ tris with almost no extra silhouette.
    ratio = max(0.04, min(0.85, target_faces / 1_000_000))
    with tempfile.TemporaryDirectory(prefix="pudgy_prop_simp_") as tmp:
        out = Path(tmp) / "out.glb"
        cmd = [
            npx,
            "--yes",
            "@gltf-transform/cli@4.1.1",
            "simplify",
            str(glb),
            str(out),
            "--ratio",
            f"{ratio:.4f}",
            "--error",
            "0.002",
            "--lock-border",
            "false",
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if proc.returncode != 0 or not out.is_file():
            print(f"warn: simplify failed for {glb.name}: {(proc.stderr or '')[-400:]}")
            return
        _safe_copy(out, glb)
        print(f"simplify ok {glb.name} ratio={ratio:.3f}")


def _sharpen_basecolor(glb: Path, target_edge: int) -> None:
    """Upscale authored baseColor to target_edge PNG with mild unsharp."""
    import io
    import json
    import struct

    from PIL import Image, ImageFilter

    data = glb.read_bytes()
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
    if gltf is None:
        return

    base_imgs: set[int] = set()
    textures = gltf.get("textures", [])
    for mat in gltf.get("materials", []):
        tex_info = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if tex_info is not None:
            src = textures[tex_info["index"]].get("source")
            if src is not None:
                base_imgs.add(src)
    if not base_imgs:
        return

    views = gltf["bufferViews"]
    bin_out = bytearray(bin_chunk)
    changed = False
    for idx in sorted(base_imgs):
        img_def = gltf["images"][idx]
        bv = views[img_def["bufferView"]]
        blob = bin_chunk[bv["byteOffset"] : bv["byteOffset"] + bv["byteLength"]]
        im = Image.open(io.BytesIO(blob)).convert("RGB")
        w, h = im.size
        already_png = img_def.get("mimeType") == "image/png"
        if already_png:
            print(f"sharpen skip {glb.name} img{idx}: already {w}x{h} PNG")
            continue
        # JPEG → PNG. Only upscale when below target; never invent past source
        # resolution just to hit a higher budget.
        if max(w, h) < target_edge:
            scale = target_edge / max(w, h)
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=3))
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
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
        print(f"sharpen {glb.name} img{idx}: {w}x{h} -> {im.size[0]}x{im.size[1]} PNG")

    if not changed:
        return
    while len(bin_out) % 4:
        bin_out.append(0)
    gltf["buffers"][0]["byteLength"] = len(bin_out)
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_out)
    tmp = glb.with_suffix(glb.suffix + ".sharpen_tmp")
    with tmp.open("wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        fh.write(json_bytes)
        fh.write(struct.pack("<II", len(bin_out), 0x004E4942))
        fh.write(bytes(bin_out))
    _safe_copy(tmp, glb)
    try:
        tmp.unlink()
    except OSError:
        pass


def _strip_orm_and_prune(glb: Path) -> None:
    """Drop normal/ORM texture refs then prune orphaned images."""
    import json
    import struct

    data = glb.read_bytes()
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
    if gltf is None:
        return
    removed = 0
    for mat in gltf.get("materials", []):
        for slot in ("normalTexture", "occlusionTexture"):
            if slot in mat:
                del mat[slot]
                removed += 1
        pbr = mat.get("pbrMetallicRoughness", {})
        if "metallicRoughnessTexture" in pbr:
            del pbr["metallicRoughnessTexture"]
            removed += 1
    if removed:
        # rewrite GLB JSON+bin in place
        bin_out = bytearray(bin_chunk)
        while len(bin_out) % 4:
            bin_out.append(0)
        gltf["buffers"] = [{"byteLength": len(bin_out)}]
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
        print(f"strip-orm: removed {removed} material texture ref(s)")

    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        return
    with tempfile.TemporaryDirectory(prefix="pudgy_prune_") as tmp:
        out = Path(tmp) / "out.glb"
        proc = subprocess.run(
            [npx, "--yes", "@gltf-transform/cli@4.1.1", "prune", str(glb), str(out)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0 and out.is_file():
            _safe_copy(out, glb)


def _optimize_preserve_fast(src: Path, *, budget: int, tex: int) -> None:
    """Keep Tripo UVs/paint: meshopt simplify + PNG upsample (no Blender remesh).

    Avoids Blender re-export of million-triangle sources (very slow) and the
    remesh color-bleed that muddied balloon arches / striped umbrellas.
    """
    print(f"+ preserve-fast {src.name} -> ~{budget:,} tris tex={tex}")
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if npx:
        with tempfile.TemporaryDirectory(prefix="pudgy_weld_") as tmp:
            td = Path(tmp)
            cur = td / "in.glb"
            shutil.copy2(src, cur)
            for step, args in (
                ("weld", ["weld", str(cur), str(td / "weld.glb")]),
                ("dedup", ["dedup", str(td / "weld.glb"), str(td / "dedup.glb")]),
            ):
                proc = subprocess.run(
                    [npx, "--yes", "@gltf-transform/cli@4.1.1", *args],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                out = Path(args[-1])
                if proc.returncode == 0 and out.is_file():
                    cur = out
                else:
                    print(f"warn: {step} skipped for {src.name}")
                    break
            _safe_copy(cur, src)
    _simplify_meshopt(src, budget)
    _strip_orm_and_prune(src)
    _sharpen_basecolor(src, tex)


def optimize_one(
    src: Path,
    *,
    faces: int | None = None,
    tex_size: int | None = None,
    path: str = _DEFAULT_PATH,
    from_pre_opt: bool = False,
    dry_run: bool = False,
) -> dict:
    src = src.resolve()
    if not src.is_file():
        raise FileNotFoundError(src)

    budget = faces if faces is not None else _prefix_lookup(src, _FACE_BUDGET, 36_000)
    tex = tex_size if tex_size is not None else _prefix_lookup(src, _TEX_SIZE, 1536)
    path = (path or _DEFAULT_PATH).lower()
    bak = src.with_suffix(src.suffix + ".pre_opt")

    if dry_run:
        before = bak.stat().st_size if (from_pre_opt and bak.is_file()) else src.stat().st_size
        print(
            f"dry-run {src.name}: faces={budget} tex={tex} path={path} "
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

    # Already game-sized skinned mesh — skip (avoids re-export bloat).
    if src.stem.lower().startswith(("char_", "oceanic_", "npc_")) and before <= 1.8e6:
        print(f"skip {src.name}: already compact skinned mesh ({before / 1e6:.2f} MB)")
        return {"path": str(src), "before": before, "after": before, "saved": 0.0}

    if path == "preserve":
        _optimize_preserve_fast(src, budget=budget, tex=tex)
        after = src.stat().st_size
        saved = 1.0 - (after / before) if before else 0.0
        print(
            f"BAKE_OK {src.name}: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB "
            f"({saved:.0%} smaller, path=preserve)"
        )
        return {"path": str(src), "before": before, "after": after, "saved": saved}

    # Remesh path: Blender closed cage + bake (fallback for broken meshes).
    blender = _blender_bin()
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
            "remesh",
        ]
        print(
            f"+ blender bake-optimize {src.name} -> ~{budget:,} tris "
            f"tex={tex} path=remesh"
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
                    "BAKE_",
                    "static ",
                    "skinned ",
                    "remesh ",
                    "decimate ",
                    "bake ",
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
        f"({saved:.0%} smaller, path=remesh)"
    )
    return {"path": str(src), "before": before, "after": after, "saved": saved}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--batch", type=Path, default=None)
    parser.add_argument("--glob", default="**/*.glb")
    parser.add_argument("--faces", type=int, default=None)
    parser.add_argument("--tex-size", type=int, default=None)
    parser.add_argument(
        "--path",
        choices=("preserve", "remesh"),
        default=_DEFAULT_PATH,
        help="preserve=keep Tripo UVs/paint (default); remesh=closed cage + bake",
    )
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
                path=args.path,
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
