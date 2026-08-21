#!/usr/bin/env python3
"""Generate PudgyMon GLBs from the Tripo v3 API and drop them into assets/models.

Auth: TRIPO_API_KEY or STUDIO_TRIPO_API_KEY (repo-root .env is loaded automatically).
Never commit the key.

Usage:
  python scripts/generate_tripo_assets.py --balance
  python scripts/generate_tripo_assets.py --wave nest
  python scripts/generate_tripo_assets.py --id env_pad_koth_01
  python scripts/generate_tripo_assets.py --catalog-id char_pudgy_candy_01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_REGISTRY = _REPO / "assets" / "studio_registry.json"
_CATALOG = _REPO / "data" / "studio_prompts_v2" / "catalog.json"
_V3 = "https://openapi.tripo3d.ai/v3"
_MIN_CREDITS = 25.0

_STYLE = (
    "Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world. "
    "Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials "
    "(not clay, not glossy vinyl), exaggerated silhouettes, soft even shading, no gore, "
    "no realistic dirt, no photorealism. Single isolated object, centered, floor-pivoted at "
    "ground center, game-ready low-to-mid poly, no base/plinth, no floating text, no characters."
)

# First Unity-facing jobs: missing Nest pad + hill + KO sticker, then extra Nest flavor.
WAVES: dict[str, list[dict]] = {
    "nest": [
        {
            "asset_id": "env_pad_koth_01",
            "target_height": 0.28,
            "notes": "Nest King of the Hill mode pad",
            "prompt": (
                f"{_STYLE} no readable glyphs. A circular floor mode pad for King of the Hill: "
                "flat soft disc with a raised candy rim, purple and gold crown-ring pattern, "
                "subtle emissive glow, very thin, about 2.5 meters wide."
            ),
        },
        {
            "asset_id": "env_koth_hill_01",
            "target_height": 0.45,
            "notes": "Moving King of the Hill capture disc",
            "prompt": (
                f"{_STYLE} A glowing King of the Hill capture platform: wide low candy disc "
                "with a tiny cartoon crown in the center, warm gold and lilac, soft emissive "
                "rim, about 3 meters wide and 0.4 meters tall, one solid piece."
            ),
        },
        {
            "asset_id": "vfx_ko_burst_marker_01",
            "target_height": 0.06,
            "notes": "Shooter floor KO sticker",
            "prompt": (
                f"{_STYLE} A flat soft KO burst decal disc for a party shooter floor: pink star "
                "burst pattern, very thin, about 2 meters wide, looks like a glowing candy "
                "sticker on the ground."
            ),
        },
        {
            "asset_id": "env_nest_crown_01",
            "target_height": 1.1,
            "notes": "Nest King of the Hill showcase crown",
            "prompt": (
                f"{_STYLE} A chunky cartoon party crown on a tiny candy pillow, gold and lilac, "
                "soft matte paint, about 1.1 meters tall, single object, no wearer."
            ),
        },
        {
            "asset_id": "prop_koth_flag_01",
            "target_height": 2.2,
            "notes": "Hill capture flag decoration",
            "prompt": (
                f"{_STYLE} A soft cartoon capture flag on a rounded candy pole, gold cloth with "
                "a simple crown silhouette (no readable letters), about 2.2 meters tall, "
                "floor pivot, single object."
            ),
        },
    ]
}


def _load_dotenv() -> None:
    env_path = _REPO / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _api_key() -> str:
    _load_dotenv()
    key = os.environ.get("TRIPO_API_KEY") or os.environ.get("STUDIO_TRIPO_API_KEY")
    if not key:
        raise SystemExit("error: set TRIPO_API_KEY in the repo-root .env (gitignored)")
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, url: str, payload: dict | None = None, timeout: int = 60) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {err.code} {url}: {body[:1200]}") from err


def balance() -> float:
    payload = _request("GET", f"{_V3}/account/balance")
    data = payload.get("data") or {}
    return float(data.get("balance") or 0.0)


def _submit_text_to_model(prompt: str, *, model: str) -> str:
    if len(prompt) > 1024:
        raise ValueError(f"prompt is {len(prompt)} chars (Tripo max 1024)")
    payload = _request(
        "POST",
        f"{_V3}/generation/text-to-model",
        {
            "prompt": prompt,
            "model": model,
            "texture": True,
            "pbr": True,
            "texture_quality": "standard",
        },
    )
    data = payload.get("data") or {}
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"no task_id in response: {payload}")
    return str(task_id)


def _poll(task_id: str, *, timeout_s: int = 300) -> dict:
    deadline = time.time() + timeout_s
    last_status = ""
    while time.time() < deadline:
        payload = _request("GET", f"{_V3}/tasks/{task_id}")
        data = payload.get("data") or payload
        status = str(data.get("status") or "")
        progress = data.get("progress")
        if status != last_status:
            print(f"  task {task_id}: {status}" + (f" {progress}%" if progress is not None else ""))
            last_status = status
        if status == "success":
            return data
        if status in {"failed", "cancelled", "banned", "expired"}:
            raise RuntimeError(f"task {task_id} {status}: {data}")
        time.sleep(3)
    raise TimeoutError(f"task {task_id} still {last_status} after {timeout_s}s")


def _model_url(task: dict) -> str:
    output = task.get("output") or {}
    for key in ("model_url", "pbr_model", "model", "base_model"):
        value = output.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
        if isinstance(value, dict):
            nested = value.get("url") or value.get("glb")
            if isinstance(nested, str) and nested.startswith("http"):
                return nested
    urls = output.get("model_urls")
    if isinstance(urls, list) and urls:
        first = urls[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict) and isinstance(first.get("url"), str):
            return first["url"]
    raise RuntimeError(f"no GLB URL in task output: {json.dumps(output)[:800]}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "PudgyMon-Tripo/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())
    if dest.stat().st_size < 1024:
        raise RuntimeError(f"downloaded file too small: {dest} ({dest.stat().st_size} bytes)")


def _register(asset_id: str, *, height: float, notes: str) -> None:
    registry = {"import_root": "assets/models", "assets": []}
    if _REGISTRY.is_file():
        registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    by_id = {
        a["asset_id"]: a
        for a in registry.get("assets", [])
        if isinstance(a, dict) and a.get("asset_id")
    }
    entry = by_id.get(asset_id, {"asset_id": asset_id})
    entry["target_height"] = float(height)
    entry["uniform_scale"] = 1.0
    entry["notes"] = notes
    by_id[asset_id] = entry
    registry["import_root"] = "assets/models"
    registry["assets"] = sorted(by_id.values(), key=lambda x: x.get("asset_id", ""))
    _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def _optimize(glb: Path) -> None:
    sys.path.insert(0, str(_REPO / "scripts"))
    import optimize_glb as opt  # noqa: WPS433

    opt.optimize_file(glb, preset="prop", backup=False, restore_pre_opt=False)


def _catalog_job(asset_id: str) -> dict:
    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    for asset in catalog.get("assets", []):
        if asset.get("asset_id") == asset_id:
            return {
                "asset_id": asset_id,
                "target_height": float(asset.get("target_height") or 1.0),
                "notes": asset.get("notes") or asset.get("label") or "Tripo catalog",
                "prompt": asset["prompt"],
            }
    raise SystemExit(f"error: `{asset_id}` not in {_CATALOG.relative_to(_REPO)}")


def generate_one(job: dict, *, model: str, optimize: bool, force: bool) -> dict:
    asset_id = job["asset_id"]
    glb = _MODELS / asset_id / f"{asset_id}.glb"
    if glb.is_file() and not force:
        print(f"skip {asset_id}: already on disk (pass --force to regenerate)")
        return {"asset_id": asset_id, "skipped": True}

    credits = balance()
    print(f"balance {credits:.2f} credits before {asset_id}")
    if credits < _MIN_CREDITS:
        raise SystemExit(
            f"not enough Tripo credits ({credits:.2f}); need at least {_MIN_CREDITS:.0f} to keep generating"
        )

    prompt = job["prompt"].strip()
    print(f"submit {asset_id} ({len(prompt)} chars, model={model})")
    task_id = _submit_text_to_model(prompt, model=model)
    task = _poll(task_id)
    used = float(task.get("credits_consumed") or 0.0)
    url = _model_url(task)
    _download(url, glb)
    meta = {
        "asset_id": asset_id,
        "task_id": task_id,
        "model": model,
        "credits_consumed": used,
        "prompt": prompt,
    }
    (glb.parent / "tripo_task.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    if optimize:
        try:
            _optimize(glb)
        except Exception as err:  # noqa: BLE001
            print(f"warn: optimize skipped for {asset_id}: {err}")
    _register(asset_id, height=float(job.get("target_height") or 1.0), notes=str(job.get("notes") or "Tripo"))
    left = balance()
    print(
        f"OK {asset_id}: {glb.stat().st_size / 1e6:.2f} MB, "
        f"used {used:.2f} credits, balance {left:.2f}"
    )
    return {"asset_id": asset_id, "credits_consumed": used, "balance": left, "path": str(glb)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balance", action="store_true", help="print credit balance and exit")
    parser.add_argument("--wave", choices=sorted(WAVES), help="generate a named first-wave batch")
    parser.add_argument("--id", dest="asset_id", help="generate one built-in wave job by asset_id")
    parser.add_argument("--catalog-id", help="generate one prompt from data/studio_prompts_v2/catalog.json")
    parser.add_argument("--model", default="v3.1-20260211", help="Tripo model id")
    parser.add_argument("--no-optimize", action="store_true")
    parser.add_argument("--force", action="store_true", help="regenerate even if the GLB exists")
    args = parser.parse_args()

    if args.balance:
        print(f"Tripo balance: {balance():.2f} credits")
        return 0

    jobs: list[dict] = []
    if args.wave:
        jobs = list(WAVES[args.wave])
    elif args.asset_id:
        for wave in WAVES.values():
            for job in wave:
                if job["asset_id"] == args.asset_id:
                    jobs = [job]
                    break
        if not jobs:
            raise SystemExit(f"error: `{args.asset_id}` is not in a built-in wave (try --catalog-id)")
    elif args.catalog_id:
        jobs = [_catalog_job(args.catalog_id)]
    else:
        parser.print_help()
        return 1

    results = []
    for job in jobs:
        results.append(
            generate_one(job, model=args.model, optimize=not args.no_optimize, force=args.force)
        )
    used = sum(float(r.get("credits_consumed") or 0) for r in results)
    print(f"done {len(results)} job(s), {used:.2f} credits consumed, balance {balance():.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
