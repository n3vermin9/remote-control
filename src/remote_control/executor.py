from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .commands import Action, Command, command_help_lines


class SystemController(Protocol):
    def open_app(self, spoken_name: str) -> str: ...
    def open_notepad(self) -> None: ...
    def open_calculator(self) -> None: ...
    def volume_up(self) -> None: ...
    def volume_down(self) -> None: ...
    def volume_mute(self) -> None: ...
    def media_play_pause(self) -> None: ...
    def media_next(self) -> None: ...
    def media_previous(self) -> None: ...


@dataclass(frozen=True)
class ExecutionResult:
    message: str
    should_quit: bool = False


class CommandExecutor:
    """Input-agnostic command layer shared by voice and future adapters."""

    def __init__(self, controller: SystemController) -> None:
        self.controller = controller

    def execute(self, command: Command) -> ExecutionResult:
        if command.action is Action.OPEN_APP:
            if not command.argument:
                return ExecutionResult("No application name was supplied.")
            app_name = self.controller.open_app(command.argument)
            return ExecutionResult(f"Opening {app_name}")

        handlers = {
            Action.OPEN_NOTEPAD: (self.controller.open_notepad, "Opening Notepad"),
            Action.OPEN_CALCULATOR: (self.controller.open_calculator, "Opening Calculator"),
            Action.VOLUME_UP: (self.controller.volume_up, "Volume up"),
            Action.VOLUME_DOWN: (self.controller.volume_down, "Volume down"),
            Action.VOLUME_MUTE: (self.controller.volume_mute, "Toggled mute"),
            Action.MEDIA_PLAY_PAUSE: (self.controller.media_play_pause, "Toggled play/pause"),
            Action.MEDIA_NEXT: (self.controller.media_next, "Next song"),
            Action.MEDIA_PREVIOUS: (self.controller.media_previous, "Previous song"),
        }

        if command.action is Action.SHOW_HELP:
            return ExecutionResult("Supported commands:\n  " + "\n  ".join(command_help_lines()))
        if command.action is Action.QUIT:
            return ExecutionResult("Stopping Remote control", should_quit=True)

        handler, message = handlers[command.action]
        handler()
        return ExecutionResult(message)
