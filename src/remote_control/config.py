from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RemoteControlVoice"
DEFAULT_MODEL_DIR = APP_DIR / "models" / "vosk-model-small-en-us-0.15"
CONFIG_PATH = APP_DIR / "config.json"


@dataclass
class Settings:
    mode: str = "f8"
    model_path: str = str(DEFAULT_MODEL_DIR)
    input_device: Optional[int] = None
    sample_rate: Optional[int] = None
    command_timeout_seconds: float = 8.0

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Settings":
        if not path.exists():
            return cls()
        values = json.loads(path.read_text(encoding="utf-8"))
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in values.items() if key in allowed})

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
