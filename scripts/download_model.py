from __future__ import annotations

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from remote_control.config import DEFAULT_MODEL_DIR, HAND_MODEL_PATH, POSE_MODEL_PATH


MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
CAMERA_MODELS = {
    HAND_MODEL_PATH: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    POSE_MODEL_PATH: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
}


def download_file(url: str, destination: Path) -> None:
    if destination.exists():
        print(f"Model already installed: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    destination = DEFAULT_MODEL_DIR
    if destination.exists():
        print(f"Model already installed: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        print("Downloading the Vosk small English model (about 40 MB)…")
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "model.zip"
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(destination.parent)
        print(f"Installed model: {destination}")

    print("Installing local webcam gesture models…")
    for model_path, model_url in CAMERA_MODELS.items():
        download_file(model_url, model_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
