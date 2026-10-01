from __future__ import annotations

import argparse
import ctypes
import sys
from pathlib import Path
from typing import Optional, Sequence

from .adapters.voice import VoiceAdapter
from .app_catalog import discover_installed_apps
from .commands import CommandParser, grammar_phrases
from .config import Settings
from .executor import CommandExecutor
from .platform.windows import WindowsController
from .speech.vosk_recognizer import VoskRecognizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Always-listening offline voice control for Windows"
    )
    parser.add_argument("--model", type=Path, help="Path to an unpacked Vosk model")
    parser.add_argument("--list-devices", action="store_true", help="List microphone devices and exit")
    parser.add_argument("--list-apps", action="store_true", help="List recognized installed apps and exit")
    parser.add_argument("--headless", action="store_true", help="Use the original console interface")
    parser.add_argument(
        "--show-window",
        action="store_true",
        help="Open the GUI instead of starting hidden in the tray",
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
    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return 0

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
    model_path = args.model or Path(settings.model_path)
    app_catalog = discover_installed_apps()
    if args.list_apps:
        for app in app_catalog.entries:
            print(app.name)
        return 0

    # Prevent duplicate tray icons and competing microphone streams when the
    # startup entry is active and START.bat is clicked again.
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    instance_mutex = kernel32.CreateMutexW(None, False, "Local\\RemoteControlVoice")
    if ctypes.get_last_error() == 183:
        print("Remote control is already running in the system tray.")
        return 0

    try:
        recognizer = VoskRecognizer(
            model_path=model_path,
            input_device=settings.input_device,
            sample_rate=settings.sample_rate,
            phrases=grammar_phrases(app_catalog.spoken_names),
        )
        executor = CommandExecutor(WindowsController(app_catalog))
    except (FileNotFoundError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    parser = CommandParser(app_catalog)

    if not args.headless:
        from .gui import RemoteControlGUI

        RemoteControlGUI(
            recognizer,
            parser,
            executor,
            app_catalog,
            settings,
            start_hidden=not args.show_window,
        ).run()
        return 0

    def handle_text(text: str) -> bool:
        print(f'Heard: "{text}"')
        command = parser.parse(text)
        if command is None:
            print("Command not recognized. Say 'show commands' for help.")
            return True
        result = executor.execute(command)
        print(result.message)
        return not result.should_quit

    print(f"Remote control 0.4.0 | always listening | sample rate={recognizer.sample_rate} Hz")
    try:
        VoiceAdapter(
            recognizer, timeout_seconds=settings.command_timeout_seconds
        ).run(handle_text)
    except KeyboardInterrupt:
        print("\nStopped.")
    if instance_mutex:
        kernel32.CloseHandle(instance_mutex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
