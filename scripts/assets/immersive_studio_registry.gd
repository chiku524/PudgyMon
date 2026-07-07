class_name ImmersiveStudioRegistry
extends RefCounted

## Loads studio asset entries from assets/studio_registry.json (updated by import_immersive_studio_pack.py).

const REGISTRY_PATH := "res://assets/studio_registry.json"


static func register_all() -> void:
	if not ResourceLoader.exists(REGISTRY_PATH):
		push_warning("ImmersiveStudioRegistry: missing %s" % REGISTRY_PATH)
		return

	var file := FileAccess.open(REGISTRY_PATH, FileAccess.READ)
	if file == null:
		push_warning("ImmersiveStudioRegistry: cannot read %s" % REGISTRY_PATH)
		return

	var json := JSON.new()
	var err := json.parse(file.get_as_text())
	if err != OK or not json.data is Dictionary:
		push_warning("ImmersiveStudioRegistry: invalid JSON in %s" % REGISTRY_PATH)
		return

	var data: Dictionary = json.data
	var import_root := str(data.get("import_root", "res://assets/models")).rstrip("/")
	var assets: Array = data.get("assets", [])
	for raw in assets:
		if not raw is Dictionary:
			continue
		var entry: Dictionary = raw
		var asset_id := str(entry.get("asset_id", "")).strip()
		if asset_id.is_empty():
			continue
		var folder := "%s/%s" % [import_root, asset_id]
		var target_height := float(entry.get("target_height", -1.0))
		var target_width := float(entry.get("target_width", -1.0))
		ImmersiveStudioMaterial.register_asset(
			asset_id,
			"%s/%s.glb" % [folder, asset_id],
			target_height,
			target_width,
			folder,
		)
