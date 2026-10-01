from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence


def normalize_app_name(name: str) -> str:
    name = name.replace("&", " and ")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", name).lower()
    return " ".join(cleaned.split())


@dataclass(frozen=True)
class AppEntry:
    name: str
    target: str
    kind: str = "path"

    @property
    def command_name(self) -> str:
        return normalize_app_name(self.name)


class AppCatalog:
    def __init__(self, entries: Iterable[AppEntry] = ()) -> None:
        self._entries: Dict[str, AppEntry] = {}
        for entry in entries:
            key = entry.command_name
            if key and key not in self._entries:
                self._entries[key] = entry

    def add(self, entry: AppEntry) -> None:
        key = entry.command_name
        if key and key not in self._entries:
            self._entries[key] = entry

    def find(self, command_name: str) -> Optional[AppEntry]:
        return self._entries.get(normalize_app_name(command_name))

    @property
    def entries(self) -> Sequence[AppEntry]:
        return tuple(sorted(self._entries.values(), key=lambda item: item.name.casefold()))

    def __len__(self) -> int:
        return len(self._entries)


BUILT_IN_APPS = (
    AppEntry("Notepad", "notepad.exe"),
    AppEntry("Calculator", "calc.exe"),
    AppEntry("File Explorer", "explorer.exe"),
    AppEntry("Paint", "mspaint.exe"),
    AppEntry("Snipping Tool", "snippingtool.exe"),
    AppEntry("Task Manager", "taskmgr.exe"),
)


def _start_menu_roots() -> list[Path]:
    roots = []
    app_data = os.environ.get("APPDATA")
    program_data = os.environ.get("PROGRAMDATA")
    if app_data:
        roots.append(Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    if program_data:
        roots.append(Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    return roots


def discover_start_menu_apps(roots: Optional[Iterable[Path]] = None) -> list[AppEntry]:
    entries = []
    for root in roots if roots is not None else _start_menu_roots():
        if not root.exists():
            continue
        for suffix in ("*.lnk", "*.url", "*.appref-ms"):
            for shortcut in root.rglob(suffix):
                name = shortcut.stem.replace(" - Shortcut", "").strip()
                if name:
                    entries.append(AppEntry(name=name, target=str(shortcut)))
    return entries


def discover_app_paths() -> list[AppEntry]:
    if sys.platform != "win32":
        return []
    import winreg

    entries = []
    locations = (
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    )
    for hive, path in locations:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            continue
        with root:
            index = 0
            while True:
                try:
                    key_name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(root, key_name) as app_key:
                        executable, _ = winreg.QueryValueEx(app_key, None)
                except OSError:
                    continue
                name = Path(key_name).stem
                if name and executable:
                    entries.append(AppEntry(name=name, target=str(executable)))
    return entries


def discover_store_apps() -> list[AppEntry]:
    if sys.platform != "win32":
        return []
    command = "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        values = json.loads(result.stdout or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []
    if isinstance(values, dict):
        values = [values]
    return [
        AppEntry(name=item["Name"], target=item["AppID"], kind="aumid")
        for item in values
        if item.get("Name") and item.get("AppID")
    ]


def discover_installed_apps() -> AppCatalog:
    catalog = AppCatalog(BUILT_IN_APPS)
    for entry in discover_start_menu_apps() + discover_app_paths() + discover_store_apps():
        catalog.add(entry)
    return catalog
