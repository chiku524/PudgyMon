#!/usr/bin/env python3
"""Unity-safe GLB size optimizer (no Draco / Meshopt / WebP / KTX2).

Welds, UV-aware simplifies, caps/re-encodes JPEG textures (alpha-safe), strips
ORM/normal maps on props, resamples animation keyframes, prunes orphans, and
validates the output still loads in Unity glTFast.

NOTE: raw Tripo exports are vertex-split triangle soup that meshopt cannot
simplify much — the script warns when that happens. For those, use the Blender
pipelines instead (they remesh a closed cage and bake the diffuse):
  scripts/blender_bake_optimize_glb.py   (props / accessories / env)
  scripts/blender_char_optimize_glb.py   (skinned characters)

Usage:
  python scripts/optimize_glb.py assets/models/char_pudgy_pink_01/char_pudgy_pink_01.glb
  python scripts/optimize_glb.py assets/models/char_pudgy_pink_01/char_pudgy_pink_01.glb --preset hero
  python scripts/optimize_glb.py --batch assets/models --glob "char_pudgy_*/*.glb"
  python scripts/optimize_glb.py path.glb --dry-run

Presets (quality-first → smaller):
  hero  keep more tris / 1024px tex  (close-ups)
  game  default party third-person (1024px, high JPEG)
  prop  décor/accessories — still readable, not crushed
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    # JPEG baseColor — fine for env/props viewed at party distance; never for crew.
    jpeg_basecolor: bool = False
    skip_simplify_below: int = 60_000


PRESETS: dict[str, Preset] = {
    # Quality-first: size savings without crushing painted candy detail.
    # Do not re-run on already-optimized GLBs without --force (see optimize_file).
    # Prefer Blender bake/char pipelines for raw Tripo triangle soup.
    "hero": Preset("hero", ratio=0.35, error=0.004, max_tex=1024, jpeg_quality=92),
    "game": Preset("game", ratio=0.25, error=0.006, max_tex=1024, jpeg_quality=90),
    "prop": Preset(
        "prop",
        ratio=0.12,
        error=0.035,
        max_tex=512,
        jpeg_quality=86,
        strip_orm=True,
        jpeg_basecolor=True,
        skip_simplify_below=16_000,
    ),
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
    print("+", " ".join(cmd[-8:] if len(cmd) > 10 else cmd))
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


def _load_glb(glb: Path) -> tuple[dict, bytearray]:
    """Parse a GLB into (gltf json, binary chunk)."""
    data = glb.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"not a GLB: {glb}")
    offset = 12
    json_chunk = None
    bin_chunk = bytearray()
    while offset + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8 : offset + 8 + clen]
        if ctype == 0x4E4F534A:
            json_chunk = chunk
        elif ctype == 0x004E4942:
            bin_chunk = bytearray(chunk)
        offset += 8 + clen
    if json_chunk is None:
        raise RuntimeError(f"incomplete GLB: {glb}")
    return json.loads(json_chunk), bin_chunk


def _write_glb(glb: Path, gltf: dict, bin_chunk: bytearray) -> None:
    gltf["buffers"] = [{"byteLength": len(bin_chunk)}]
    new_json = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    new_json += b" " * ((4 - (len(new_json) % 4)) % 4)
    bin_chunk = bytearray(bin_chunk)
    bin_chunk.extend(b"\x00" * ((4 - (len(bin_chunk) % 4)) % 4))

    out = bytearray()
    out += b"glTF"
    out += struct.pack("<II", 2, 12 + 8 + len(new_json) + 8 + len(bin_chunk))
    out += struct.pack("<II", len(new_json), 0x4E4F534A)
    out += new_json
    out += struct.pack("<II", len(bin_chunk), 0x004E4942)
    out += bin_chunk
    glb.write_bytes(out)


def _sanitize_bevy_accessors(glb: Path) -> int:
    """Materialize zero accessors that lack bufferView (illegal for some loaders).

    gltf-transform `sparse` / Blender animation optimize can emit constant-zero
    accessors with no bufferView. Spec allows that for zeros; Unity glTFast
    prefers explicit views. Returns how many accessors were repaired.
    """
    gltf, bin_chunk = _load_glb(glb)
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

    _write_glb(glb, gltf, bin_chunk)
    return repaired


def _has_alpha_materials(glb: Path) -> bool:
    """True when any material relies on texture alpha (MASK / BLEND)."""
    gltf, _ = _load_glb(glb)
    return any(
        mat.get("alphaMode", "OPAQUE") in ("MASK", "BLEND")
        for mat in gltf.get("materials", [])
    )


def _has_normal_maps(glb: Path) -> bool:
    gltf, _ = _load_glb(glb)
    return any("normalTexture" in mat for mat in gltf.get("materials", []))


def _has_skins(glb: Path) -> bool:
    gltf, _ = _load_glb(glb)
    return bool(gltf.get("skins"))


# Material texture slots that are dead weight on tiny props (paint is baked
# into baseColor; toon-ish lighting makes normal / ORM detail invisible).
_ORM_SLOTS = ("normalTexture", "occlusionTexture")
_PBR_ORM_SLOTS = ("metallicRoughnessTexture",)


def _strip_orm_slots(glb: Path) -> int:
    """Remove normal / occlusion / metallicRoughness texture refs from materials.

    Returns the number of references removed. The images themselves become
    orphans — run a `prune` pass afterwards to drop them from the file.
    """
    gltf, bin_chunk = _load_glb(glb)
    removed = 0
    for mat in gltf.get("materials", []):
        for slot in _ORM_SLOTS:
            if slot in mat:
                del mat[slot]
                removed += 1
        pbr = mat.get("pbrMetallicRoughness", {})
        for slot in _PBR_ORM_SLOTS:
            if slot in pbr:
                del pbr[slot]
                removed += 1
    if removed:
        _write_glb(glb, gltf, bin_chunk)
    return removed


def _unity_tune_materials(glb: Path) -> None:
    """Make PBR values Unity/URP-friendly for painted toon assets.

    Bevy's default metallic=1 reads as chrome in URP Lit. Force dielectric
    paint, drop cameras/lights that would steal Camera.main, and keep
    double-sided off on opaque mats (fill-rate).
    """
    gltf, bin_chunk = _load_glb(glb)
    dirty = False
    if gltf.get("cameras"):
        gltf["cameras"] = []
        dirty = True
    exts = gltf.get("extensions") or {}
    if "KHR_lights_punctual" in exts:
        del exts["KHR_lights_punctual"]
        dirty = True
    used = [e for e in gltf.get("extensionsUsed", []) if e != "KHR_lights_punctual"]
    req = [e for e in gltf.get("extensionsRequired", []) if e != "KHR_lights_punctual"]
    if used != gltf.get("extensionsUsed", []):
        gltf["extensionsUsed"] = used
        dirty = True
    if req != gltf.get("extensionsRequired", []):
        gltf["extensionsRequired"] = req
        dirty = True

    for node in gltf.get("nodes", []):
        if "camera" in node:
            del node["camera"]
            dirty = True
        if "extensions" in node and "KHR_lights_punctual" in node["extensions"]:
            del node["extensions"]["KHR_lights_punctual"]
            dirty = True

    for mat in gltf.get("materials", []):
        pbr = mat.setdefault("pbrMetallicRoughness", {})
        if pbr.get("metallicFactor", 1.0) != 0.0:
            pbr["metallicFactor"] = 0.0
            dirty = True
        if "roughnessFactor" not in pbr:
            pbr["roughnessFactor"] = 0.62
            dirty = True
        if mat.get("alphaMode", "OPAQUE") == "OPAQUE" and mat.get("doubleSided"):
            mat["doubleSided"] = False
            dirty = True

    asset = gltf.setdefault("asset", {})
    extra = asset.setdefault("extras", {})
    if extra.get("target") != "unity-gltfast":
        extra["target"] = "unity-gltfast"
        extra["up"] = "+Y"
        extra["forward"] = "+Z"
        dirty = True

    if dirty:
        _write_glb(glb, gltf, bin_chunk)


def _validate_bevy_glb(glb: Path) -> None:
    """Fail loudly if the output would not load in Unity glTFast (legacy name)."""
    _validate_unity_glb(glb)


def _validate_unity_glb(glb: Path) -> None:
    """Fail loudly if the output would not load in Unity glTFast."""
    gltf, _ = _load_glb(glb)
    problems: list[str] = []
    for i, acc in enumerate(gltf.get("accessors", [])):
        if "bufferView" not in acc and "sparse" not in acc:
            problems.append(f"accessor {i} has no bufferView (glTFast rejects this)")
    for ext in gltf.get("extensionsRequired", []):
        problems.append(f"requires extension {ext} (Unity glTFast may not support it)")
    for i, img in enumerate(gltf.get("images", [])):
        mime = img.get("mimeType")
        if mime not in (None, "image/jpeg", "image/png"):
            problems.append(f"image {i} has unsupported mimeType {mime}")
    if problems:
        raise RuntimeError(f"{glb.name} failed Unity glTFast validation: " + "; ".join(problems))


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


def _replace_file(src: Path, dest: Path) -> None:
    """Copy dest in place, retrying Windows ERROR_USER_MAPPED_FILE (1224)."""
    last: OSError | None = None
    for attempt in range(8):
        try:
            shutil.copy2(src, dest)
            return
        except OSError as err:
            last = err
            if getattr(err, "winerror", None) != 1224:
                raise
            time.sleep(0.4 * (attempt + 1))
    raise last  # type: ignore[misc]


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
    skip_simplify_below: int | None = None,
    restore_pre_opt: bool = False,
) -> dict:
    """Optimize one GLB. Returns size stats. Writes to dest (default: in-place)."""
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    p = PRESETS[preset]
    ratio = p.ratio if ratio is None else ratio
    error = p.error if error is None else error
    max_tex = p.max_tex if max_tex is None else max_tex
    jpeg_quality = p.jpeg_quality if jpeg_quality is None else jpeg_quality
    skip_simplify_below = (
        p.skip_simplify_below if skip_simplify_below is None else skip_simplify_below
    )

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
    # Restoring dense .pre_opt is optional — Unity re-optimizes the working
    # GLB (already glTF-Transform'd) unless the caller wants a full rebake.
    if restore_pre_opt and backup and out == src and bak.is_file() and bak.stat().st_size > before:
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
        skinned = _has_skins(cur)
        if not skinned:
            # Unity likes a single static mesh with the pivot on the floor.
            try:
                run("flatten", "flatten")
            except RuntimeError as err:
                print(f"warn: flatten skipped ({err})")
            try:
                run("join", "join")
            except RuntimeError as err:
                print(f"warn: join skipped ({err})")
            try:
                run("center", "center", "--pivot", "below")
            except RuntimeError as err:
                print(f"warn: center skipped ({err})")
        if do_simplify:
            # Border locking protects skinned seams, but on static meshes it
            # can lock nearly every vertex (Tripo exports are vertex-split
            # triangle soup where every edge is a "border").
            lock_border = "true" if skinned else "false"
            run(
                "simplify",
                "simplify",
                "--ratio",
                str(ratio),
                "--error",
                str(error),
                "--lock-border",
                lock_border,
            )

        # ORM / normal maps are dead weight on props (diffuse is baked, toon
        # lighting hides the detail) — drop the refs, prune removes the images.
        if p.strip_orm:
            stripped = _strip_orm_slots(cur)
            if stripped:
                print(f"strip-orm: removed {stripped} material texture ref(s)")
                run("prune_orm", "prune")

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
        # Crew keeps PNG baseColor (eyes/edges). Env/props may JPEG — Unity URP
        # samples them at party distance where chroma smear is invisible.
        jpeg_albedo = p.jpeg_basecolor and not skinned and not _has_alpha_materials(cur)
        if jpeg_albedo:
            print("Unity prop: JPEG baseColor for URP size")
            run(
                "jpeg_base",
                "jpeg",
                "--quality",
                str(jpeg_quality),
                "--formats",
                "*",
                "--slots",
                "baseColorTexture",
            )
        elif _has_alpha_materials(cur):
            print("alpha materials present — keeping baseColor format (no JPEG)")
        else:
            print("keeping baseColor as PNG (crew / cutout)")
        run(
            "jpeg",
            "jpeg",
            "--quality",
            str(jpeg_quality),
            "--formats",
            "*",
            "--slots",
            "{metallicRoughnessTexture,occlusionTexture,emissiveTexture}",
        )
        # Normals benefit from slightly higher quality to avoid banding.
        try:
            run(
                "jpeg_n",
                "jpeg",
                "--quality",
                str(min(95, jpeg_quality + 4)),
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
        # Tangents bloat vertex buffers; only emit them when a normal map exists
        # (Unity/URP needs them for bump). Painted props skip this.
        if _has_normal_maps(cur):
            try:
                run("tangents", "tangents")
            except RuntimeError as err:
                print(f"warn: tangents skipped ({err})")
        # Do NOT run gltf-transform `sparse`: it emits zero accessors without
        # bufferView, which Unity glTFast rejects as invalid glTF.

        # Final sweep for anything the passes above orphaned.
        run("prune_final", "prune")

        out.parent.mkdir(parents=True, exist_ok=True)
        _replace_file(cur, out)
        _unity_tune_materials(out)
        fixed = _sanitize_bevy_accessors(out)
        if fixed:
            print(f"unity-sanitize: materialized {fixed} zero accessor(s)")
        _validate_unity_glb(out)

    # meshopt can only collapse topologically connected edges. Raw Tripo
    # exports are vertex-split soup that resists simplification — the Blender
    # remesh+bake pipeline is the tool for those, so say so instead of
    # silently shipping a 200k-tri "optimized" mesh.
    if do_simplify and faces:
        after_faces = _face_count(out)
        target = max(int(faces * ratio), skip_simplify_below)
        if after_faces and after_faces > target * 3:
            print(
                f"WARN {out.name}: simplify stalled at {after_faces:,} tris "
                f"(target ~{int(faces * ratio):,}) - mesh topology is likely "
                "disconnected triangle soup. Use "
                "scripts/blender_bake_optimize_glb.py (props) or "
                "scripts/blender_char_optimize_glb.py (characters) for a real "
                "reduction."
            )

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
    parser.add_argument(
        "--from-pre-opt",
        action="store_true",
        help="Restore denser .glb.pre_opt before optimizing (slow, Bevy-era rebake)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Parallel file workers (Unity re-opt of the library: 4 is a good start)",
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
    jobs = max(1, args.jobs)

    def _one(path: Path) -> dict:
        preset = args.preset or _guess_preset(path)
        return optimize_file(
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
            restore_pre_opt=args.from_pre_opt,
        )

    if jobs == 1 or len(files) == 1:
        for path in files:
            try:
                stats = _one(path)
                total_before += stats["before"]
                total_after += stats["after"]
            except Exception as exc:  # noqa: BLE001 — batch continues
                failed += 1
                print(f"error: {path}: {exc}", file=sys.stderr)
    else:
        print(f"unity-opt: {len(files)} files, {jobs} workers")
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futs = {pool.submit(_one, path): path for path in files}
            for fut in as_completed(futs):
                path = futs[fut]
                try:
                    stats = fut.result()
                    total_before += stats["before"]
                    total_after += stats["after"]
                except Exception as exc:  # noqa: BLE001
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
