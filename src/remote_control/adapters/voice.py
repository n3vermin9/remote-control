from __future__ import annotations

import threading
from typing import Callable

from ..speech.vosk_recognizer import VoskRecognizer
from .base import TextHandler


class VoiceAdapter:
    def __init__(
        self,
        recognizer: VoskRecognizer,
        timeout_seconds: float = 8.0,
        status: Callable[[str], None] = print,
    ) -> None:
        self.recognizer = recognizer
        self.timeout_seconds = timeout_seconds
        self.status = status
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self, on_text: TextHandler) -> None:
        self.status("Always listening")
        while not self._stop_event.is_set():
            text = self.recognizer.listen_once(
                self._stop_event, self.timeout_seconds, self.status
            )
            if text and not on_text(text):
                return
