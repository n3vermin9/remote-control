from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .adapters.voice import VoiceAdapter
from .commands import CommandParser
from .config import Settings
from .executor import CommandExecutor
from .platform.windows import WindowsController
from .speech.vosk_recognizer import VoskRecognizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline English voice control for Windows")
    parser.add_argument("--mode", choices=("f8", "always"), help="Listening mode")
    parser.add_argument("--model", type=Path, help="Path to an unpacked Vosk model")
    parser.add_argument("--list-devices", action="store_true", help="List microphone devices and exit")
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

    try:
        recognizer = VoskRecognizer(
            model_path=model_path,
            input_device=settings.input_device,
            sample_rate=settings.sample_rate,
        )
        executor = CommandExecutor(WindowsController())
    except (FileNotFoundError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    parser = CommandParser()

    def handle_text(text: str) -> bool:
        print(f'Heard: "{text}"')
        command = parser.parse(text)
        if command is None:
            print("Command not recognized. Say 'show commands' for help.")
            return True
        result = executor.execute(command)
        print(result.message)
        return not result.should_quit

    print(f"Remote control 0.1.0 | mode={mode} | sample rate={recognizer.sample_rate} Hz")
    try:
        VoiceAdapter(recognizer, mode, settings.command_timeout_seconds).run(handle_text)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
