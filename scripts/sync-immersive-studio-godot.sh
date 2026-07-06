#!/usr/bin/env bash
# Sync Godot helpers from immersive.labs packages/studio-godot into this project.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${IMMERSIVE_LABS_ROOT:-$ROOT/../../Desktop/vibe-code/immersive.labs}/packages/studio-godot"
DEST="$ROOT/third_party/immersive_studio"

if [[ ! -d "$SRC/scripts" ]]; then
  echo "error: studio-godot source not found at $SRC" >&2
  echo "Set IMMERSIVE_LABS_ROOT to your immersive.labs clone." >&2
  exit 1
fi

mkdir -p "$DEST/scripts" "$DEST/shaders"
cp "$SRC/scripts/"*.gd "$DEST/scripts/"
cp "$SRC/shaders/"*.gdshader "$DEST/shaders/"
cp "$SRC/README.md" "$DEST/README.md"
export DEST

python - <<'PY'
from pathlib import Path
import os
dest = Path(os.environ["DEST"])
material = dest / "scripts" / "immersive_studio_material.gd"
text = material.read_text(encoding="utf-8")
text = text.replace(
    'res://shaders/immersive_studio_orm.gdshader',
    'res://third_party/immersive_studio/shaders/immersive_studio_orm.gdshader',
)
material.write_text(text, encoding="utf-8")
PY

echo "Synced studio-godot -> $DEST"
