import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

@dataclass
class Settings:
    translation: str = "NABRE"
    mode: str = "obsidian"
    canon: str = "catholic"
    cache_dir: Optional[str] = None
    no_randomize: bool = False
    no_jitter: bool = False

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "bgmd"
        self.config_path = self.config_dir / "config.json"
        self.settings = self._load()

    def _load(self) -> Settings:
        if not self.config_path.exists():
            return Settings()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Settings(**data)
        except (json.JSONDecodeError, TypeError):
            return Settings()

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.settings), f, indent=4)

    def set(self, key: str, value: Any):
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            self.save()
        else:
            raise KeyError(f"Invalid setting: {key}")

    def get_all(self) -> Dict[str, Any]:
        return asdict(self.settings)

# Global instance for easy access
config = ConfigManager()
