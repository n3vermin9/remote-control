from __future__ import annotations

import argparse
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
        description="Offline voice, GUI, and webcam gesture control for Windows"
    )
    parser.add_argument("--mode", choices=("f8", "always"), help="Listening mode")
    parser.add_argument("--model", type=Path, help="Path to an unpacked Vosk model")
    parser.add_argument("--list-devices", action="store_true", help="List microphone devices and exit")
    parser.add_argument("--list-apps", action="store_true", help="List recognized installed apps and exit")
    parser.add_argument("--headless", action="store_true", help="Use the original console interface")
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

    settings = Settings.load()
    settings.save()
    mode = args.mode or settings.mode
    model_path = args.model or Path(settings.model_path)
    app_catalog = discover_installed_apps()
    if args.list_apps:
        for app in app_catalog.entries:
            print(app.name)
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
            initial_mode=mode,
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

    print(f"Remote control 0.2.0 | mode={mode} | sample rate={recognizer.sample_rate} Hz")
    try:
        VoiceAdapter(recognizer, mode, settings.command_timeout_seconds).run(handle_text)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
