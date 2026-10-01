from __future__ import annotations

import subprocess
import sys
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "RemoteControlVoice"


def _command() -> str:
    pythonw = Path(sys.prefix) / "Scripts" / "pythonw.exe"
    return subprocess.list2cmdline([str(pythonw), "-m", "remote_control"])


def install_autostart() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Windows autostart is supported on Windows only.")
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())


def remove_autostart() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Windows autostart is supported on Windows only.")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass


def autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return False
    return value == _command()
