from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from vosk import KaldiRecognizer, Model, SetLogLevel

from ..commands import grammar_phrases


StatusHandler = Callable[[str], None]


class VoskRecognizer:
    def __init__(
        self,
        model_path: Path,
        input_device: Optional[int] = None,
        sample_rate: Optional[int] = None,
    ) -> None:
        import sounddevice as sd

        if not model_path.exists():
            raise FileNotFoundError(
                f"Speech model not found at {model_path}. Run: python scripts/download_model.py"
            )
        SetLogLevel(-1)
        self._sd = sd
        self._model = Model(str(model_path))
        self._device = input_device
        device_info = sd.query_devices(input_device, "input")
        detected_rate = int(device_info["default_samplerate"])
        self.sample_rate = int(sample_rate or detected_rate or 16000)

    def _new_decoder(self) -> KaldiRecognizer:
        grammar = json.dumps(grammar_phrases())
        return KaldiRecognizer(self._model, self.sample_rate, grammar)

    def listen_once(
        self,
        stop_event: threading.Event,
        timeout_seconds: float,
        on_status: StatusHandler = print,
    ) -> str:
        chunks: queue.Queue[bytes] = queue.Queue()
        decoder = self._new_decoder()

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            if status:
                on_status(f"Audio warning: {status}")
            chunks.put(bytes(indata))

        started = time.monotonic()
        on_status("Listening…")
        with self._sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=4000,
            device=self._device,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            while not stop_event.is_set() and time.monotonic() - started < timeout_seconds:
                try:
                    data = chunks.get(timeout=0.1)
                except queue.Empty:
                    continue
                if decoder.AcceptWaveform(data):
                    text = json.loads(decoder.Result()).get("text", "")
                    if text:
                        return text

        return json.loads(decoder.FinalResult()).get("text", "")
