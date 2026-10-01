from __future__ import annotations

from typing import Callable, Protocol


TextHandler = Callable[[str], bool]


class InputAdapter(Protocol):
    def run(self, on_text: TextHandler) -> None:
        """Emit text commands until stopped or on_text returns False."""
