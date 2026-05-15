"""Configuration management — ~/.codingagentim/config.toml."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

CONFIG_DIR = Path.home() / ".codingagentim"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_defaults: dict[str, Any] = {
    "default_provider": "dingtalk",
    "default_agent": "claude",
    "output_format": "table",
    "dingtalk": {
        "app_key": "",
        "app_secret": "",
        "agent_id": "",
        "robot_code": "",
    },
}


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            user_cfg = tomllib.load(f)
        merged = {**_defaults, **user_cfg}
        for k, v in _defaults.items():
            if isinstance(v, dict) and k in user_cfg:
                merged[k] = {**v, **user_cfg[k]}
        return merged
    return dict(_defaults)


def save_config(cfg: dict[str, Any]) -> None:
    ensure_config_dir()
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(cfg, f)


def get(key: str, default: Any = None) -> Any:
    cfg = load_config()
    parts = key.split(".")
    current = cfg
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current
