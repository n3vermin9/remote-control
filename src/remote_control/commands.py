from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


class Action(str, Enum):
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    OPEN_NOTEPAD = "open_notepad"
    OPEN_CALCULATOR = "open_calculator"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_MUTE = "volume_mute"
    SET_VOLUME = "set_volume"
    MEDIA_PLAY_PAUSE = "media_play_pause"
    MEDIA_NEXT = "media_next"
    MEDIA_PREVIOUS = "media_previous"
    MEDIA_STOP = "media_stop"
    SHOW_DESKTOP = "show_desktop"
    MINIMIZE_WINDOW = "minimize_window"
    MAXIMIZE_WINDOW = "maximize_window"
    SWITCH_WINDOW = "switch_window"
    SCREENSHOT = "screenshot"
    BROWSER_BACK = "browser_back"
    BROWSER_FORWARD = "browser_forward"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    COPY = "copy"
    CUT = "cut"
    PASTE = "paste"
    UNDO = "undo"
    REDO = "redo"
    SELECT_ALL = "select_all"
    NEW_TAB = "new_tab"
    CLOSE_TAB = "close_tab"
    REOPEN_TAB = "reopen_tab"
    REFRESH = "refresh"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    ZOOM_RESET = "zoom_reset"
    PRESS_ENTER = "press_enter"
    PRESS_ESCAPE = "press_escape"
    CLOSE_WINDOW = "close_window"
    SHOW_HELP = "show_help"
    QUIT = "quit"


@dataclass(frozen=True)
class Command:
    action: Action
    source_text: str
    argument: Optional[str] = None
    needs_confirmation: bool = False


PHRASES = {
    "open notepad": Action.OPEN_NOTEPAD,
    "start notepad": Action.OPEN_NOTEPAD,
    "open calculator": Action.OPEN_CALCULATOR,
    "start calculator": Action.OPEN_CALCULATOR,
    "volume up": Action.VOLUME_UP,
    "turn volume up": Action.VOLUME_UP,
    "increase volume": Action.VOLUME_UP,
    "raise volume": Action.VOLUME_UP,
    "turn it up": Action.VOLUME_UP,
    "make it louder": Action.VOLUME_UP,
    "louder": Action.VOLUME_UP,
    "sound up": Action.VOLUME_UP,
    "volume down": Action.VOLUME_DOWN,
    "turn volume down": Action.VOLUME_DOWN,
    "decrease volume": Action.VOLUME_DOWN,
    "lower volume": Action.VOLUME_DOWN,
    "turn it down": Action.VOLUME_DOWN,
    "make it quieter": Action.VOLUME_DOWN,
    "quieter": Action.VOLUME_DOWN,
    "sound down": Action.VOLUME_DOWN,
    "mute": Action.VOLUME_MUTE,
    "mute volume": Action.VOLUME_MUTE,
    "mute sound": Action.VOLUME_MUTE,
    "silence": Action.VOLUME_MUTE,
    "silence volume": Action.VOLUME_MUTE,
    "toggle mute": Action.VOLUME_MUTE,
    "unmute": Action.VOLUME_MUTE,
    "unmute volume": Action.VOLUME_MUTE,
    "unmute sound": Action.VOLUME_MUTE,
    "play": Action.MEDIA_PLAY_PAUSE,
    "pause": Action.MEDIA_PLAY_PAUSE,
    "play music": Action.MEDIA_PLAY_PAUSE,
    "pause music": Action.MEDIA_PLAY_PAUSE,
    "play song": Action.MEDIA_PLAY_PAUSE,
    "pause song": Action.MEDIA_PLAY_PAUSE,
    "resume": Action.MEDIA_PLAY_PAUSE,
    "resume music": Action.MEDIA_PLAY_PAUSE,
    "continue music": Action.MEDIA_PLAY_PAUSE,
    "toggle playback": Action.MEDIA_PLAY_PAUSE,
    "play pause": Action.MEDIA_PLAY_PAUSE,
    "next song": Action.MEDIA_NEXT,
    "skip song": Action.MEDIA_NEXT,
    "skip this song": Action.MEDIA_NEXT,
    "play next song": Action.MEDIA_NEXT,
    "go to next song": Action.MEDIA_NEXT,
    "forward one song": Action.MEDIA_NEXT,
    "previous song": Action.MEDIA_PREVIOUS,
    "last song": Action.MEDIA_PREVIOUS,
    "play previous song": Action.MEDIA_PREVIOUS,
    "go to previous song": Action.MEDIA_PREVIOUS,
    "back one song": Action.MEDIA_PREVIOUS,
    "go back": Action.MEDIA_PREVIOUS,
    "stop music": Action.MEDIA_STOP,
    "stop song": Action.MEDIA_STOP,
    "stop playback": Action.MEDIA_STOP,
    "show desktop": Action.SHOW_DESKTOP,
    "go to desktop": Action.SHOW_DESKTOP,
    "hide all windows": Action.SHOW_DESKTOP,
    "minimize window": Action.MINIMIZE_WINDOW,
    "minimize this window": Action.MINIMIZE_WINDOW,
    "hide this window": Action.MINIMIZE_WINDOW,
    "maximize window": Action.MAXIMIZE_WINDOW,
    "maximize this window": Action.MAXIMIZE_WINDOW,
    "make window full screen": Action.MAXIMIZE_WINDOW,
    "switch window": Action.SWITCH_WINDOW,
    "next window": Action.SWITCH_WINDOW,
    "change window": Action.SWITCH_WINDOW,
    "take screenshot": Action.SCREENSHOT,
    "capture screen": Action.SCREENSHOT,
    "screenshot": Action.SCREENSHOT,
    "browser back": Action.BROWSER_BACK,
    "go back in browser": Action.BROWSER_BACK,
    "previous page": Action.BROWSER_BACK,
    "browser forward": Action.BROWSER_FORWARD,
    "go forward in browser": Action.BROWSER_FORWARD,
    "next page": Action.BROWSER_FORWARD,
    "scroll up": Action.SCROLL_UP,
    "page up": Action.SCROLL_UP,
    "move up": Action.SCROLL_UP,
    "scroll down": Action.SCROLL_DOWN,
    "page down": Action.SCROLL_DOWN,
    "move down": Action.SCROLL_DOWN,
    "copy": Action.COPY,
    "copy this": Action.COPY,
    "cut": Action.CUT,
    "cut this": Action.CUT,
    "paste": Action.PASTE,
    "paste here": Action.PASTE,
    "undo": Action.UNDO,
    "undo that": Action.UNDO,
    "redo": Action.REDO,
    "redo that": Action.REDO,
    "select all": Action.SELECT_ALL,
    "new tab": Action.NEW_TAB,
    "open new tab": Action.NEW_TAB,
    "close tab": Action.CLOSE_TAB,
    "close this tab": Action.CLOSE_TAB,
    "reopen tab": Action.REOPEN_TAB,
    "reopen closed tab": Action.REOPEN_TAB,
    "refresh": Action.REFRESH,
    "refresh page": Action.REFRESH,
    "reload": Action.REFRESH,
    "reload page": Action.REFRESH,
    "zoom in": Action.ZOOM_IN,
    "zoom out": Action.ZOOM_OUT,
    "reset zoom": Action.ZOOM_RESET,
    "normal zoom": Action.ZOOM_RESET,
    "press enter": Action.PRESS_ENTER,
    "enter": Action.PRESS_ENTER,
    "press escape": Action.PRESS_ESCAPE,
    "escape": Action.PRESS_ESCAPE,
    "close window": Action.CLOSE_WINDOW,
    "close this window": Action.CLOSE_WINDOW,
    "help": Action.SHOW_HELP,
    "show commands": Action.SHOW_HELP,
    "quit remote control": Action.QUIT,
    "exit remote control": Action.QUIT,
}

APP_PREFIXES = ("open ", "open up ", "start ", "launch ", "run ")
CLOSE_APP_PREFIXES = ("close app ", "close application ", "close ", "quit ", "exit ", "stop ")


_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def number_words(value: int) -> str:
    if value < 20:
        return _ONES[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        return _TENS[tens] if not ones else f"{_TENS[tens]} {_ONES[ones]}"
    return "one hundred"


NUMBER_VALUES = {number_words(value): value for value in range(101)}


def _parse_volume(normalized: str) -> Optional[int]:
    patterns = (
        r"(?:set )?(?:the )?(?:volume|sound)(?: level)?(?: to)? (.+?)(?: percent)?$",
        r"(.+?) percent (?:volume|sound)$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, normalized)
        if not match:
            continue
        value_text = match.group(1)
        try:
            value = int(value_text)
        except ValueError:
            value = NUMBER_VALUES.get(value_text, -1)
        if 0 <= value <= 100:
            return value
    return None


class CommandParser:
    def __init__(self, app_catalog=None) -> None:
        self.app_catalog = app_catalog

    def parse(self, text: str) -> Optional[Command]:
        normalized = " ".join(text.lower().strip().split())
        action = PHRASES.get(normalized)
        if action is not None:
            return Command(action=action, source_text=normalized)
        volume = _parse_volume(normalized)
        if volume is not None:
            return Command(Action.SET_VOLUME, normalized, argument=str(volume))
        if self.app_catalog:
            for prefix in APP_PREFIXES:
                if normalized.startswith(prefix):
                    name = normalized[len(prefix) :]
                    entry = self.app_catalog.find(name)
                    if entry:
                        return Command(Action.OPEN_APP, normalized, argument=entry.command_name)
            for prefix in CLOSE_APP_PREFIXES:
                if normalized.startswith(prefix):
                    name = normalized[len(prefix) :]
                    entry = self.app_catalog.find(name)
                    if entry:
                        return Command(Action.CLOSE_APP, normalized, argument=entry.command_name)
        return None


def command_help_lines() -> Iterable[str]:
    return (
        "open / open up / start / launch / run + any installed app name",
        "close / quit / exit / stop + any installed app name",
        "volume 0-100 / volume up / volume down / mute / unmute",
        "play / pause / resume / stop music / next song / previous song",
        "show desktop / minimize window / maximize window / switch window",
        "take screenshot / browser back / browser forward / scroll up / scroll down",
        "copy / cut / paste / undo / redo / select all",
        "new tab / close tab / reopen tab / refresh / zoom in / zoom out / reset zoom",
        "press enter / press escape / close window",
        "show commands",
        "quit remote control",
    )
