from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class TelegramResponse:
    text: str
    should_exit: bool = False


CommandHandler = Callable[[str], TelegramResponse]
StatusHandler = Callable[[str], None]


class TelegramAdapter:
    """Receive text commands through Telegram Bot API long polling."""

    def __init__(
        self,
        token: str,
        authorized_chat_id: Optional[int],
        status: StatusHandler = print,
    ) -> None:
        token = token.strip()
        if not token or ":" not in token:
            raise ValueError("Enter a valid Telegram bot token from BotFather.")
        self.token = token
        self.authorized_chat_id = authorized_chat_id
        self.status = status
        self._stop_event = threading.Event()
        self._offset: Optional[int] = None
        self.exit_requested = False

    def stop(self) -> None:
        self._stop_event.set()

    def _request(self, method: str, values: dict[str, object]) -> object:
        encoded = urllib.parse.urlencode(values).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/{method}",
            data=encoded,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise RuntimeError("Telegram rejected the bot token.") from None
            if error.code == 409:
                raise RuntimeError(
                    "Another copy of this bot is already connected to Telegram."
                ) from None
            if error.code == 429 or error.code >= 500:
                raise urllib.error.URLError("Telegram is temporarily unavailable.") from None
            raise RuntimeError(f"Telegram request failed with status {error.code}.") from None
        if not payload.get("ok"):
            raise RuntimeError("Telegram rejected the request.")
        return payload.get("result")

    def send_message(self, chat_id: int, text: str) -> None:
        for attempt in range(3):
            try:
                self._request("sendMessage", {"chat_id": chat_id, "text": text[:4096]})
                return
            except urllib.error.URLError:
                if attempt == 2:
                    raise RuntimeError("Could not send the Telegram reply.") from None
                self.status("Telegram reply delayed; retrying…")
                self._stop_event.wait(2)

    def run(self, on_command: CommandHandler) -> None:
        while not self._stop_event.is_set():
            try:
                identity = self._request("getMe", {})
                self._request("deleteWebhook", {"drop_pending_updates": "true"})
                break
            except urllib.error.URLError:
                self.status("Telegram offline; reconnecting…")
                self._stop_event.wait(5)
        else:
            return
        username = identity.get("username") if isinstance(identity, dict) else None
        self.status(f"Telegram connected{f' as @{username}' if username else ''}")
        while not self._stop_event.is_set():
            values: dict[str, object] = {
                "timeout": 25,
                "allowed_updates": json.dumps(["message"]),
            }
            if self._offset is not None:
                values["offset"] = self._offset
            try:
                updates = self._request("getUpdates", values)
            except urllib.error.URLError:
                self.status("Telegram offline; reconnecting…")
                self._stop_event.wait(5)
                continue
            for update in updates if isinstance(updates, list) else []:
                self._offset = int(update["update_id"]) + 1
                message = update.get("message") or {}
                text = (message.get("text") or "").strip()
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                if not text or not isinstance(chat_id, int):
                    continue
                if chat.get("type") != "private":
                    continue
                if text.casefold() == "/id":
                    self.send_message(chat_id, f"Your Telegram chat ID is {chat_id}.")
                    continue
                if self.authorized_chat_id is None:
                    self.send_message(
                        chat_id,
                        "This computer is not paired yet. Send /id, then enter that ID in the desktop app.",
                    )
                    continue
                if chat_id != self.authorized_chat_id:
                    continue
                if text.casefold() in {"/status", "/ping"}:
                    self.send_message(chat_id, "Remote control is online and ready.")
                    continue
                if text.casefold() in {"/start", "/help", "/commands"}:
                    text = "show commands"
                response = on_command(text)
                self.send_message(chat_id, response.text)
                if response.should_exit:
                    self.exit_requested = True
                    return
