from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

HYPRCLIP_MODULE = "custom/hyprclip"
HYPRCLIP_MODULE_CONFIG: dict[str, Any] = {
    "exec": "hyprclip waybar",
    "return-type": "json",
    "interval": 2,
    "on-click": "hyprclip pick",
    "on-click-right": "hyprclip clear",
    "tooltip": True,
}


def add_hyprclip_waybar_module(config: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(config)
    modules_right = list(updated.get("modules-right", []))
    if HYPRCLIP_MODULE not in modules_right:
        insert_at = 1 if modules_right else 0
        modules_right.insert(insert_at, HYPRCLIP_MODULE)
    updated["modules-right"] = modules_right
    updated[HYPRCLIP_MODULE] = dict(HYPRCLIP_MODULE_CONFIG)
    return updated


def install_hyprclip_waybar_module(config_path: Path) -> bool:
    config_path = config_path.expanduser()
    original = config_path.read_text(encoding="utf-8")
    config = json.loads(original)
    updated = add_hyprclip_waybar_module(config)
    rendered = json.dumps(updated, indent=2, ensure_ascii=False) + "\n"
    if rendered == original:
        return False
    backup = config_path.with_suffix(config_path.suffix + ".hyprclip.bak")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    config_path.write_text(rendered, encoding="utf-8")
    return True
