from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard

from ..speech.vosk_recognizer import VoskRecognizer
from .base import TextHandler


class VoiceAdapter:
    def __init__(
        self,
        recognizer: VoskRecognizer,
        mode: str = "f8",
        timeout_seconds: float = 8.0,
        status: Callable[[str], None] = print,
    ) -> None:
        if mode not in {"f8", "always"}:
            raise ValueError("Listening mode must be 'f8' or 'always'.")
        self.recognizer = recognizer
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.status = status

    def run(self, on_text: TextHandler) -> None:
        if self.mode == "always":
            self._run_always(on_text)
        else:
            self._run_f8(on_text)

    def _run_always(self, on_text: TextHandler) -> None:
        self.status("Always-listening mode active. Press Ctrl+C to stop.")
        while True:
            text = self.recognizer.listen_once(threading.Event(), self.timeout_seconds, self.status)
            if text and not on_text(text):
                return

    def _run_f8(self, on_text: TextHandler) -> None:
        self.status("F8 mode active. Hold F8 while speaking; release it when done.")
        pressed = threading.Event()
        released = threading.Event()
        quit_event = threading.Event()

        def on_press(key) -> None:  # noqa: ANN001
            if key == keyboard.Key.f8 and not pressed.is_set():
                released.clear()
                pressed.set()

        def on_release(key) -> None:  # noqa: ANN001
            if key == keyboard.Key.f8:
                released.set()

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        try:
            while not quit_event.is_set():
                pressed.wait()
                pressed.clear()
                text = self.recognizer.listen_once(released, self.timeout_seconds, self.status)
                if text:
                    if not on_text(text):
                        quit_event.set()
                else:
                    self.status("No command recognized.")
        finally:
            listener.stop()
