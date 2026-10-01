from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from typing import Optional

from ..app_catalog import AppCatalog


# Windows virtual-key codes for hardware media keys.
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_BROWSER_BACK = 0xA6
VK_BROWSER_FORWARD = 0xA7
VK_SNAPSHOT = 0x2C
VK_LWIN = 0x5B
VK_MENU = 0x12
VK_TAB = 0x09
VK_D = 0x44
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120
SW_MAXIMIZE = 3
SW_MINIMIZE = 6


class WindowsController:
    def __init__(self, app_catalog: Optional[AppCatalog] = None) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Command execution is supported on Windows only.")
        self.app_catalog = app_catalog or AppCatalog()

    @staticmethod
    def _launch(executable: str) -> None:
        subprocess.Popen([executable], close_fds=True)

    @staticmethod
    def _press_media_key(key_code: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.keybd_event(key_code, 0, 0, 0)
        user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def _press_shortcut(modifier: int, key_code: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.keybd_event(modifier, 0, 0, 0)
        user32.keybd_event(key_code, 0, 0, 0)
        user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(modifier, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def _show_foreground_window(command: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        window = user32.GetForegroundWindow()
        if window:
            user32.ShowWindow(window, command)

    @staticmethod
    def _scroll(delta: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)

    def open_notepad(self) -> None:
        self._launch("notepad.exe")

    def open_calculator(self) -> None:
        self._launch("calc.exe")

    def open_app(self, spoken_name: str) -> str:
        entry = self.app_catalog.find(spoken_name)
        if entry is None:
            raise ValueError(f"Application not found: {spoken_name}")
        if entry.kind == "aumid":
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{entry.target}"], close_fds=True
            )
        elif hasattr(os, "startfile"):
            os.startfile(entry.target)  # type: ignore[attr-defined]
        else:
            self._launch(entry.target)
        return entry.name

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

    def media_stop(self) -> None:
        self._press_media_key(VK_MEDIA_STOP)

    def show_desktop(self) -> None:
        self._press_shortcut(VK_LWIN, VK_D)

    def minimize_window(self) -> None:
        self._show_foreground_window(SW_MINIMIZE)

    def maximize_window(self) -> None:
        self._show_foreground_window(SW_MAXIMIZE)

    def switch_window(self) -> None:
        self._press_shortcut(VK_MENU, VK_TAB)

    def screenshot(self) -> None:
        self._press_media_key(VK_SNAPSHOT)

    def browser_back(self) -> None:
        self._press_media_key(VK_BROWSER_BACK)

    def browser_forward(self) -> None:
        self._press_media_key(VK_BROWSER_FORWARD)

    def scroll_up(self) -> None:
        self._scroll(WHEEL_DELTA * 5)

    def scroll_down(self) -> None:
        self._scroll(-WHEEL_DELTA * 5)
