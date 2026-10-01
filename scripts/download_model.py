from __future__ import annotations

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from remote_control.config import DEFAULT_MODEL_DIR


MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


def main() -> int:
    destination = DEFAULT_MODEL_DIR
    if destination.exists():
        print(f"Model already installed: {destination}")
        return 0

    destination.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading the Vosk small English model (about 40 MB)…")
    with tempfile.TemporaryDirectory() as temp_dir:
        archive = Path(temp_dir) / "model.zip"
        with urllib.request.urlopen(MODEL_URL, timeout=60) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(destination.parent)
    print(f"Installed model: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
