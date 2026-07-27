#!/usr/bin/env python3
"""Bevy-safe GLB size optimizer (no Draco / Meshopt / WebP / KTX2).

Tripo crew meshes are often 100k–500k tris after a light pass — that dominates
file size. This script welds, UV-aware simplifies, caps/re-encodes JPEG textures,
and resamples animation keyframes while staying compatible with Bevy 0.19.

Usage:
  python scripts/optimize_glb.py assets/models/char_pudgy_pink_01/char_pudgy_pink_01.glb
  python scripts/optimize_glb.py assets/models/char_pudgy_pink_01/char_pudgy_pink_01.glb --preset hero
  python scripts/optimize_glb.py --batch assets/models --glob "char_pudgy_*/*.glb"
  python scripts/optimize_glb.py path.glb --dry-run

Presets (quality-first → smaller):
  hero  keep more tris / 768px tex  (close-ups)
  game  default party third-person
  prop  aggressive (accessories / décor)
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

_COMPONENT_BYTES = {
    5120: 1,  # BYTE
    5121: 1,  # UNSIGNED_BYTE
    5122: 2,  # SHORT
    5123: 2,  # UNSIGNED_SHORT
    5125: 4,  # UNSIGNED_INT
    5126: 4,  # FLOAT
}
_TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


@dataclass(frozen=True)
class Preset:
    name: str
    # Target fraction of vertices to keep (simplifier may stop earlier on error).
    ratio: float
    # Max geometric error as fraction of mesh radius (higher = more reduction).
    error: float
    max_tex: int
    jpeg_quality: int
    # Drop ORM / normal maps that are nearly unused weight on tiny props.
    strip_orm: bool = False


PRESETS: dict[str, Preset] = {
    # Tuned for a single pass from dense Tripo meshes (~100k–300k tris).
    # Do not re-run on already-optimized GLBs without --force (see optimize_file).
    "hero": Preset("hero", ratio=0.18, error=0.008, max_tex=768, jpeg_quality=82),
    "game": Preset("game", ratio=0.12, error=0.010, max_tex=512, jpeg_quality=78),
    "prop": Preset("prop", ratio=0.08, error=0.016, max_tex=384, jpeg_quality=72),
}


def _npx() -> str:
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        candidate = Path(r"C:\Program Files\nodejs\npx.cmd")
        if candidate.is_file():
            npx = str(candidate)
    if not npx:
        raise RuntimeError("npx not found on PATH (needed for @gltf-transform/cli)")
    return npx


def _gltf(npx: str, *args: str) -> None:
    cmd = [npx, "--yes", "@gltf-transform/cli@4.1.1", *args]
    print("+", " ".join(cmd[-6:] if len(cmd) > 8 else cmd))
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if proc.stdout and proc.stdout.strip():
        # Keep the one-line size summary from the CLI (ASCII-safe for Windows consoles).
        for line in proc.stdout.strip().splitlines()[-3:]:
            safe = (
                line.replace("\u2192", "->")
                .replace("\u2014", "-")
                .replace("\u2013", "-")
                .encode("ascii", "replace")
                .decode("ascii")
            )
            if safe.strip():
                print(safe)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2500:]
        err = err.replace("\u2192", "->")
        raise RuntimeError(f"gltf-transform {' '.join(args[:2])} failed:\n{err}")


def _sanitize_bevy_accessors(glb: Path) -> int:
    """Materialize zero accessors that lack bufferView (illegal for Bevy's loader).

    gltf-transform `sparse` / Blender animation optimize can emit constant-zero
    accessors with no bufferView. Spec allows that for zeros; Bevy 0.19 rejects
    the file as invalid glTF. Returns how many accessors were repaired.
    """
    data = glb.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"not a GLB: {glb}")
    offset = 12
    json_chunk = None
    bin_chunk = None
    json_start = bin_start = None
    while offset + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8 : offset + 8 + clen]
        if ctype == 0x4E4F534A:
            json_chunk = bytearray(chunk)
            json_start = offset
        elif ctype == 0x004E4942:
            bin_chunk = bytearray(chunk)
            bin_start = offset
        offset += 8 + clen
    if json_chunk is None or bin_chunk is None:
        raise RuntimeError(f"incomplete GLB: {glb}")

    gltf = json.loads(bytes(json_chunk))
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.setdefault("bufferViews", [])
    repaired = 0
    for acc in accessors:
        if "bufferView" in acc or "sparse" in acc:
            continue
        ctype = acc.get("componentType")
        atype = acc.get("type")
        count = int(acc.get("count", 0))
        if ctype not in _COMPONENT_BYTES or atype not in _TYPE_COMPONENTS or count <= 0:
            continue
        elem = _COMPONENT_BYTES[ctype] * _TYPE_COMPONENTS[atype]
        nbytes = elem * count
        # Align to 4 bytes for GLB packing.
        pad = (4 - (len(bin_chunk) % 4)) % 4
        bin_chunk.extend(b"\x00" * pad)
        bv_index = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": len(bin_chunk),
                "byteLength": nbytes,
            }
        )
        bin_chunk.extend(b"\x00" * nbytes)
        acc["bufferView"] = bv_index
        acc["byteOffset"] = 0
        repaired += 1

    if repaired == 0:
        return 0

    gltf["buffers"] = [{"byteLength": len(bin_chunk)}]
    new_json = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(new_json) % 4)) % 4
    new_json += b" " * json_pad
    bin_pad = (4 - (len(bin_chunk) % 4)) % 4
    bin_chunk.extend(b"\x00" * bin_pad)

    out = bytearray()
    out += b"glTF"
    out += struct.pack("<II", 2, 12 + 8 + len(new_json) + 8 + len(bin_chunk))
    out += struct.pack("<II", len(new_json), 0x4E4F534A)
    out += new_json
    out += struct.pack("<II", len(bin_chunk), 0x004E4942)
    out += bin_chunk
    # Silence unused-start lint for readers that keep offsets around.
    _ = (json_start, bin_start)
    glb.write_bytes(out)
    return repaired


def _face_count(glb: Path) -> int | None:
    """Best-effort triangle count via gltf-transform inspect (None if unavailable)."""
    try:
        npx = _npx()
        proc = subprocess.run(
            [npx, "--yes", "@gltf-transform/cli@4.1.1", "inspect", str(glb)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        if proc.returncode != 0:
            return None
        # MESHES table: # | name | mode | meshPrimitives | glPrimitives | ...
        # Split on box-drawing or ASCII pipes.
        total = 0
        for line in proc.stdout.splitlines():
            if "TRIANGLES" not in line:
                continue
            raw = line.replace("|", "│")
            parts = [p.strip() for p in raw.split("│") if p.strip()]
            # Find the TRIANGLES column, then glPrimitives is two columns later
            # (#, name, mode=TRIANGLES, meshPrimitives, glPrimitives).
            try:
                mode_i = parts.index("TRIANGLES")
            except ValueError:
                continue
            prim_i = mode_i + 2
            if prim_i >= len(parts):
                continue
            digits = parts[prim_i].replace(",", "").replace(" ", "")
            if digits.isdigit():
                total += int(digits)
        return total or None
    except Exception:
        return None


def _restore_dense_backup(src: Path, bak: Path) -> int:
    """Copy denser .pre_opt backup over working GLB. Returns restored byte size."""
    shutil.copy2(bak, src)
    return bak.stat().st_size


def optimize_file(
    src: Path,
    *,
    dest: Path | None = None,
    preset: str = "game",
    ratio: float | None = None,
    error: float | None = None,
    max_tex: int | None = None,
    jpeg_quality: int | None = None,
    backup: bool = True,
    dry_run: bool = False,
    force: bool = False,
    skip_simplify_below: int = 40_000,
) -> dict:
    """Optimize one GLB. Returns size stats. Writes to dest (default: in-place)."""
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    p = PRESETS[preset]
    ratio = p.ratio if ratio is None else ratio
    error = p.error if error is None else error
    max_tex = p.max_tex if max_tex is None else max_tex
    jpeg_quality = p.jpeg_quality if jpeg_quality is None else jpeg_quality

    src = src.resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    out = (dest or src).resolve()
    before = src.stat().st_size

    if dry_run:
        print(
            f"dry-run {src.name}: preset={preset} ratio={ratio} error={error} "
            f"tex<={max_tex} jpeg q{jpeg_quality} ({before / 1e6:.2f} MB)"
        )
        return {"path": str(src), "before": before, "after": before, "preset": preset}

    bak = src.with_suffix(src.suffix + ".pre_opt")
    # Prefer denser original backup so repeated / failed passes cannot lock in
    # a barely-touched mesh. Restore whenever backup is larger (not only 2x).
    if backup and out == src and bak.is_file() and bak.stat().st_size > before:
        print(
            f"restoring dense source from {bak.name} "
            f"({bak.stat().st_size / 1e6:.2f} MB -> working copy)"
        )
        before = _restore_dense_backup(src, bak)
    elif backup and out == src and not bak.is_file():
        shutil.copy2(src, bak)
        print(f"backup -> {bak.name}")

    faces = _face_count(src)
    do_simplify = True
    if faces is None:
        print("mesh face count unknown; simplifying anyway")
    elif faces < skip_simplify_below and not force:
        print(
            f"skip simplify ({faces:,} tris < {skip_simplify_below:,}); "
            "texture/resample only (pass --force to simplify anyway)"
        )
        do_simplify = False
    else:
        print(f"mesh {faces:,} tris before optimize")

    npx = _npx()

    with tempfile.TemporaryDirectory(prefix="pudgy_opt_") as tmp:
        td = Path(tmp)
        cur = td / "00_in.glb"
        shutil.copy2(src, cur)
        step_i = 0

        def run(label: str, cmd: str, *extra: str) -> None:
            nonlocal cur, step_i
            step_i += 1
            nxt = td / f"{step_i:02d}_{label}.glb"
            _gltf(npx, cmd, str(cur), str(nxt), *extra)
            cur.unlink(missing_ok=True)
            cur = nxt

        run("weld", "weld")
        run("dedup", "dedup")
        run("prune", "prune")
        if do_simplify:
            run(
                "simplify",
                "simplify",
                "--ratio",
                str(ratio),
                "--error",
                str(error),
                "--lock-border",
                "true",
            )
        run(
            "resize",
            "resize",
            "--width",
            str(max_tex),
            "--height",
            str(max_tex),
            "--filter",
            "lanczos3",
        )
        # Plain image/jpeg embeds — Bevy-safe (no EXT_texture_webp / Basis).
        run(
            "jpeg",
            "jpeg",
            "--quality",
            str(jpeg_quality),
            "--formats",
            "*",
            "--slots",
            "baseColorTexture,metallicRoughnessTexture,occlusionTexture,emissiveTexture",
        )
        # Normals benefit from slightly higher quality to avoid banding.
        try:
            run(
                "jpeg_n",
                "jpeg",
                "--quality",
                str(min(90, jpeg_quality + 8)),
                "--formats",
                "*",
                "--slots",
                "normalTexture",
            )
        except RuntimeError as err:
            print(f"warn: normal jpeg pass skipped ({err})")
        try:
            run("resample", "resample", "--tolerance", "0.0004")
        except RuntimeError as err:
            print(f"warn: resample skipped ({err})")
        # Do NOT run gltf-transform `sparse`: it emits zero accessors without
        # bufferView, which Bevy 0.19 rejects as invalid glTF.

        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cur, out)
        fixed = _sanitize_bevy_accessors(out)
        if fixed:
            print(f"bevy-sanitize: materialized {fixed} zero accessor(s)")

    after = out.stat().st_size
    saved = 1.0 - (after / before) if before else 0.0
    print(
        f"OPT_OK {out.name}: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB "
        f"({saved:.0%} smaller, preset={preset})"
    )
    return {
        "path": str(out),
        "before": before,
        "after": after,
        "saved": saved,
        "preset": preset,
    }


def _guess_preset(path: Path) -> str:
    name = path.stem.lower()
    if name.startswith("char_") or name.startswith("oceanic_"):
        return "game"
    if name.startswith("acc_") or name.startswith("prop_") or name.startswith("env_"):
        return "prop"
    return "game"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="GLB file(s) to optimize",
    )
    parser.add_argument(
        "--batch",
        type=Path,
        default=None,
        help="Root folder to scan (with --glob)",
    )
    parser.add_argument(
        "--glob",
        default="**/*.glb",
        help="Glob under --batch (default: **/*.glb)",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default=None,
        help="Size/quality preset (default: guess from filename)",
    )
    parser.add_argument("--ratio", type=float, default=None, help="Override simplify keep ratio")
    parser.add_argument("--error", type=float, default=None, help="Override simplify error")
    parser.add_argument("--max-tex", type=int, default=None, help="Max texture edge px")
    parser.add_argument("--jpeg-quality", type=int, default=None, help="JPEG quality 1-100")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (single input only); default overwrites in place",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not write .glb.pre_opt beside in-place targets",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Simplify even when the mesh is already under the face budget",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files: list[Path] = list(args.paths)
    if args.batch is not None:
        root = args.batch.resolve()
        files.extend(sorted(root.glob(args.glob)))
    # Skip backups / temp
    files = [
        f
        for f in files
        if f.is_file()
        and f.suffix.lower() == ".glb"
        and ".pre_opt" not in f.name
        and not f.name.endswith("_weld.glb")
        and not f.name.endswith("_simp.glb")
    ]
    # De-dupe
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
    if args.out is not None and len(files) != 1:
        print("error: --out requires exactly one input", file=sys.stderr)
        return 1

    total_before = total_after = 0
    failed = 0
    for path in files:
        preset = args.preset or _guess_preset(path)
        try:
            stats = optimize_file(
                path,
                dest=args.out,
                preset=preset,
                ratio=args.ratio,
                error=args.error,
                max_tex=args.max_tex,
                jpeg_quality=args.jpeg_quality,
                backup=not args.no_backup,
                dry_run=args.dry_run,
                force=args.force,
            )
            total_before += stats["before"]
            total_after += stats["after"]
        except Exception as exc:  # noqa: BLE001 — batch continues
            failed += 1
            print(f"error: {path}: {exc}", file=sys.stderr)

    if len(files) > 1 and total_before:
        print(
            f"TOTAL {total_before / 1e6:.1f} MB -> {total_after / 1e6:.1f} MB "
            f"({1.0 - total_after / total_before:.0%} smaller), "
            f"{len(files) - failed}/{len(files)} ok"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
