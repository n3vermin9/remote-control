from __future__ import annotations

import argparse
import ctypes
import sys
from typing import Optional, Sequence

from .app_catalog import discover_installed_apps
from .commands import CommandParser
from .config import Settings
from .executor import CommandExecutor
from .platform.windows import WindowsController


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram bot remote control for Windows")
    parser.add_argument("--list-apps", action="store_true", help="List recognized apps and exit")
    parser.add_argument(
        "--show-window",
        action="store_true",
        help="Open the setup window instead of starting hidden in the tray",
    )
    parser.add_argument(
        "--install-autostart", action="store_true", help="Start automatically with Windows"
    )
    parser.add_argument(
        "--remove-autostart", action="store_true", help="Disable Windows autostart"
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if sys.platform != "win32":
        print("Remote control currently runs on Windows only.", file=sys.stderr)
        return 2

    if args.install_autostart or args.remove_autostart:
        from .autostart import install_autostart, remove_autostart

        if args.install_autostart:
            install_autostart()
            print("Remote control will start automatically with Windows.")
        else:
            remove_autostart()
            print("Remote control Windows autostart was removed.")
        return 0

    settings = Settings.load()
    settings.save()
    app_catalog = discover_installed_apps()
    if args.list_apps:
        for app in app_catalog.entries:
            print(app.name)
        return 0

    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    instance_mutex = kernel32.CreateMutexW(None, False, "Local\\RemoteControlTelegram")
    if ctypes.get_last_error() == 183:
        print("Remote control is already running in the system tray.")
        return 0

    parser = CommandParser(app_catalog)
    executor = CommandExecutor(WindowsController(app_catalog))

    from .gui import RemoteControlGUI

    RemoteControlGUI(
        parser,
        executor,
        app_catalog,
        settings,
        start_hidden=not args.show_window,
    ).run()
    if instance_mutex:
        kernel32.CloseHandle(instance_mutex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
