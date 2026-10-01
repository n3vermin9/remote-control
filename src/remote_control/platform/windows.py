from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..app_catalog import AppCatalog, normalize_app_name


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
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_F4 = 0x73
VK_F5 = 0x74
VK_A = 0x41
VK_C = 0x43
VK_D = 0x44
VK_R = 0x52
VK_T = 0x54
VK_V = 0x56
VK_W = 0x57
VK_X = 0x58
VK_Y = 0x59
VK_Z = 0x5A
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD
VK_0 = 0x30
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
WM_CLOSE = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


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
        WindowsController._press_keys(modifier, key_code)

    @staticmethod
    def _press_keys(*key_codes: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        for key_code in key_codes:
            user32.keybd_event(key_code, 0, 0, 0)
        for key_code in reversed(key_codes):
            user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)

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

    def open_app(self, app_name: str) -> str:
        entry = self.app_catalog.find(app_name)
        if entry is None:
            raise ValueError(f"Application not found: {app_name}")
        if entry.kind == "aumid":
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{entry.target}"], close_fds=True
            )
        elif hasattr(os, "startfile"):
            os.startfile(entry.target)  # type: ignore[attr-defined]
        else:
            self._launch(entry.target)
        return entry.name

    def close_app(self, app_name: str) -> str:
        entry = self.app_catalog.find(app_name)
        if entry is None:
            raise ValueError(f"Application not found: {app_name}")

        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
        )
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

        app_name = normalize_app_name(entry.name)
        app_words = set(app_name.split())
        target_process = ""
        if entry.kind == "path" and Path(entry.target).suffix.casefold() == ".exe":
            target_process = normalize_app_name(Path(entry.target).stem)
        closed = []

        def process_name(hwnd) -> str:  # noqa: ANN001
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if not handle:
                return ""
            try:
                size = wintypes.DWORD(32768)
                buffer = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    return normalize_app_name(Path(buffer.value).stem)
            finally:
                kernel32.CloseHandle(handle)
            return ""

        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def visit(hwnd, _lparam) -> bool:  # noqa: ANN001
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, length + 1)
            title = normalize_app_name(title_buffer.value)
            process = process_name(hwnd)
            process_matches = bool(
                process
                and (
                    process == target_process
                    or process == app_name
                    or (len(process) >= 3 and process in app_words)
                )
            )
            title_matches = bool(app_name and app_name in title)
            if process_matches or title_matches:
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                closed.append(hwnd)
            return True

        user32.EnumWindows(callback_type(visit), 0)
        if not closed:
            raise RuntimeError(f"No open window was found for {entry.name}.")
        return entry.name

    def volume_up(self) -> None:
        self._press_media_key(VK_VOLUME_UP)

    def volume_down(self) -> None:
        self._press_media_key(VK_VOLUME_DOWN)

    def volume_mute(self) -> None:
        self._press_media_key(VK_VOLUME_MUTE)

    def set_volume(self, percent: int) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("Volume must be between 0 and 100.")
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMasterVolumeLevelScalar(percent / 100, None)

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

    def copy(self) -> None:
        self._press_keys(VK_CONTROL, VK_C)

    def cut(self) -> None:
        self._press_keys(VK_CONTROL, VK_X)

    def paste(self) -> None:
        self._press_keys(VK_CONTROL, VK_V)

    def undo(self) -> None:
        self._press_keys(VK_CONTROL, VK_Z)

    def redo(self) -> None:
        self._press_keys(VK_CONTROL, VK_Y)

    def select_all(self) -> None:
        self._press_keys(VK_CONTROL, VK_A)

    def new_tab(self) -> None:
        self._press_keys(VK_CONTROL, VK_T)

    def close_tab(self) -> None:
        self._press_keys(VK_CONTROL, VK_W)

    def reopen_tab(self) -> None:
        self._press_keys(VK_CONTROL, VK_SHIFT, VK_T)

    def refresh(self) -> None:
        self._press_keys(VK_F5)

    def zoom_in(self) -> None:
        self._press_keys(VK_CONTROL, VK_OEM_PLUS)

    def zoom_out(self) -> None:
        self._press_keys(VK_CONTROL, VK_OEM_MINUS)

    def zoom_reset(self) -> None:
        self._press_keys(VK_CONTROL, VK_0)

    def press_enter(self) -> None:
        self._press_keys(VK_RETURN)

    def press_escape(self) -> None:
        self._press_keys(VK_ESCAPE)

    def close_window(self) -> None:
        self._press_keys(VK_MENU, VK_F4)
