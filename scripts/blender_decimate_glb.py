#!/usr/bin/env python3
"""Decimate dense Tripo GLBs via Blender (meshopt often stalls on Tripo topology).

Restores from `.glb.pre_opt` when present and larger, applies Decimate to a target
triangle budget, re-exports GLB, then runs the Bevy-safe texture/resample pass
from optimize_glb.py (simplify skipped).

Usage:
  python scripts/blender_decimate_glb.py assets/models/env_nest_bench_01/env_nest_bench_01.glb
  python scripts/blender_decimate_glb.py --batch assets/models --glob "*/*.glb"
  python scripts/blender_decimate_glb.py path.glb --faces 12000
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_BLENDER_SCRIPT = Path(__file__).resolve().parent / "_blender_decimate_inner.py"

# Default triangle targets by asset prefix.
_FACE_BUDGET = {
    "char_": 28_000,
    "oceanic_": 28_000,
    "npc_": 28_000,
    "acc_": 8_000,
    "prop_": 12_000,
    "env_": 14_000,
    "vfx_": 4_000,
}


def _blender_bin() -> str:
    env = os.environ.get("STUDIO_BLENDER_BIN") or os.environ.get("BLENDER_BIN")
    if env and Path(env).is_file():
        return env
    candidates = [
        Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"),
        Path("/usr/bin/blender"),
        Path("/Applications/Blender.app/Contents/MacOS/Blender"),
    ]
    which = shutil.which("blender")
    if which:
        candidates.insert(0, Path(which))
    for c in candidates:
        if c.is_file():
            return str(c)
    raise RuntimeError(
        "Blender not found — set STUDIO_BLENDER_BIN or install Blender 4+/5+"
    )


def _face_budget(path: Path, override: int | None) -> int:
    if override is not None:
        return override
    name = path.stem.lower()
    for prefix, faces in _FACE_BUDGET.items():
        if name.startswith(prefix):
            return faces
    return 12_000


def _safe_copy(src: Path, dst: Path, *, attempts: int = 8) -> None:
    """Copy with retries — Windows often locks GLBs briefly (IDE / AV / mapper)."""
    import time

    last: Exception | None = None
    for i in range(attempts):
        try:
            shutil.copy2(src, dst)
            return
        except OSError as exc:
            last = exc
            time.sleep(0.15 * (i + 1))
    raise RuntimeError(f"copy failed {src} -> {dst}: {last}")


def decimate_one(
    src: Path,
    *,
    faces: int | None = None,
    dry_run: bool = False,
    skip_texture_pass: bool = False,
) -> dict:
    src = src.resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    budget = _face_budget(src, faces)
    before = src.stat().st_size

    if dry_run:
        print(f"dry-run {src.name}: target_faces={budget} ({before / 1e6:.2f} MB)")
        return {"path": str(src), "before": before, "after": before, "faces": budget}

    # Prefer denser .pre_opt when present.
    bak = src.with_suffix(src.suffix + ".pre_opt")
    if bak.is_file() and bak.stat().st_size > src.stat().st_size:
        _safe_copy(bak, src)
        print(f"restored dense source from {bak.name}")
    elif not bak.is_file():
        _safe_copy(src, bak)
        print(f"backup -> {bak.name}")

    before = src.stat().st_size
    blender = _blender_bin()

    with tempfile.TemporaryDirectory(prefix="pudgy_dec_") as tmp:
        td = Path(tmp)
        out_glb = td / "decimated.glb"
        cmd = [
            blender,
            "--background",
            "--python",
            str(_BLENDER_SCRIPT),
            "--",
            str(src),
            str(out_glb),
            str(budget),
        ]
        print(f"+ blender decimate {src.name} -> ~{budget:,} tris")
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0 or not out_glb.is_file():
            tail = ((proc.stderr or "") + (proc.stdout or ""))[-2000:]
            raise RuntimeError(f"Blender decimate failed for {src.name}:\n{tail}")

        # If Blender made the file larger (e.g. already-optimal oceanic), keep input.
        if out_glb.stat().st_size > before * 1.02:
            print(
                f"keep source {src.name}: decimated larger "
                f"({out_glb.stat().st_size / 1e6:.2f} MB > {before / 1e6:.2f} MB)"
            )
        else:
            _safe_copy(out_glb, src)

    if not skip_texture_pass:
        sys.path.insert(0, str(_REPO / "scripts"))
        from optimize_glb import optimize_file  # noqa: WPS433

        optimize_file(
            src,
            preset="prop" if not src.stem.startswith(("char_", "oceanic_")) else "game",
            backup=False,
            force=False,
            skip_simplify_below=10_000_000,
        )

    after = src.stat().st_size
    saved = 1.0 - (after / before) if before else 0.0
    print(
        f"DEC_OK {src.name}: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB "
        f"({saved:.0%} smaller, target={budget:,} tris)"
    )
    return {"path": str(src), "before": before, "after": after, "saved": saved, "faces": budget}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--batch", type=Path, default=None)
    parser.add_argument("--glob", default="**/*.glb")
    parser.add_argument("--faces", type=int, default=None, help="Override triangle budget")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-texture-pass",
        action="store_true",
        help="Skip optimize_glb texture/resample after decimate",
    )
    args = parser.parse_args()

    files: list[Path] = list(args.paths)
    if args.batch is not None:
        files.extend(sorted(args.batch.resolve().glob(args.glob)))
    files = [
        f
        for f in files
        if f.is_file()
        and f.suffix.lower() == ".glb"
        and ".pre_opt" not in f.name
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

    if not _BLENDER_SCRIPT.is_file():
        print(f"error: missing {_BLENDER_SCRIPT}", file=sys.stderr)
        return 1

    total_before = total_after = 0
    failed = 0
    for path in files:
        try:
            stats = decimate_one(
                path,
                faces=args.faces,
                dry_run=args.dry_run,
                skip_texture_pass=args.skip_texture_pass,
            )
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
