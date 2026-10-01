from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


class Action(str, Enum):
    OPEN_NOTEPAD = "open_notepad"
    OPEN_CALCULATOR = "open_calculator"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_MUTE = "volume_mute"
    MEDIA_PLAY_PAUSE = "media_play_pause"
    MEDIA_NEXT = "media_next"
    MEDIA_PREVIOUS = "media_previous"
    SHOW_HELP = "show_help"
    QUIT = "quit"


@dataclass(frozen=True)
class Command:
    action: Action
    spoken_text: str
    needs_confirmation: bool = False


PHRASES = {
    "open notepad": Action.OPEN_NOTEPAD,
    "start notepad": Action.OPEN_NOTEPAD,
    "open calculator": Action.OPEN_CALCULATOR,
    "start calculator": Action.OPEN_CALCULATOR,
    "volume up": Action.VOLUME_UP,
    "turn volume up": Action.VOLUME_UP,
    "increase volume": Action.VOLUME_UP,
    "volume down": Action.VOLUME_DOWN,
    "turn volume down": Action.VOLUME_DOWN,
    "decrease volume": Action.VOLUME_DOWN,
    "mute": Action.VOLUME_MUTE,
    "mute volume": Action.VOLUME_MUTE,
    "unmute": Action.VOLUME_MUTE,
    "unmute volume": Action.VOLUME_MUTE,
    "play": Action.MEDIA_PLAY_PAUSE,
    "pause": Action.MEDIA_PLAY_PAUSE,
    "play music": Action.MEDIA_PLAY_PAUSE,
    "pause music": Action.MEDIA_PLAY_PAUSE,
    "play pause": Action.MEDIA_PLAY_PAUSE,
    "next track": Action.MEDIA_NEXT,
    "skip track": Action.MEDIA_NEXT,
    "previous track": Action.MEDIA_PREVIOUS,
    "go back": Action.MEDIA_PREVIOUS,
    "help": Action.SHOW_HELP,
    "show commands": Action.SHOW_HELP,
    "quit remote control": Action.QUIT,
    "exit remote control": Action.QUIT,
}


def grammar_phrases() -> list[str]:
    """Phrases supplied to Vosk to improve speed and command accuracy."""
    return list(PHRASES) + ["[unk]"]


class CommandParser:
    def parse(self, text: str) -> Optional[Command]:
        normalized = " ".join(text.lower().strip().split())
        action = PHRASES.get(normalized)
        if action is None:
            return None
        return Command(action=action, spoken_text=normalized)


def command_help_lines() -> Iterable[str]:
    return (
        "open notepad / open calculator",
        "volume up / volume down / mute / unmute",
        "play / pause / next track / previous track",
        "show commands",
        "quit remote control",
    )
