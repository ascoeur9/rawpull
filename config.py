import json
import os
import sys
from pathlib import Path

from constants import CONFIG_FILENAME

DEFAULT_CONFIG = {
    "source_folder": "",
    "destination_folder": "",
    "match_mode": "contains",
    "extension_filter": "raw",
    "include_subfolders": False,
    "window_geometry": "900x800",
}


def get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(os.path.abspath(__file__)).parent
    return base / CONFIG_FILENAME


def load_config() -> dict:
    path = get_config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = dict(DEFAULT_CONFIG)
        config.update(data)
        return config
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(data: dict) -> None:
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[config] 설정 저장 실패: {e}")
