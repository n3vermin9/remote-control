from __future__ import annotations

import ctypes
import subprocess
import sys


# Windows virtual-key codes for hardware media keys.
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


class WindowsController:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Command execution is supported on Windows only.")

    @staticmethod
    def _launch(executable: str) -> None:
        subprocess.Popen([executable], close_fds=True)

    @staticmethod
    def _press_media_key(key_code: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.keybd_event(key_code, 0, 0, 0)
        user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)

    def open_notepad(self) -> None:
        self._launch("notepad.exe")

    def open_calculator(self) -> None:
        self._launch("calc.exe")

    def volume_up(self) -> None:
        self._press_media_key(VK_VOLUME_UP)

    def volume_down(self) -> None:
        self._press_media_key(VK_VOLUME_DOWN)

    def volume_mute(self) -> None:
        self._press_media_key(VK_VOLUME_MUTE)

    def media_play_pause(self) -> None:
        self._press_media_key(VK_MEDIA_PLAY_PAUSE)

    def media_next(self) -> None:
        self._press_media_key(VK_MEDIA_NEXT_TRACK)

    def media_previous(self) -> None:
        self._press_media_key(VK_MEDIA_PREV_TRACK)
