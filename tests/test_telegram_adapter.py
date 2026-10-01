import unittest

from remote_control.adapters.telegram import TelegramAdapter


class FakeTelegramAdapter(TelegramAdapter):
    def __init__(self, authorized_chat_id, updates):
        super().__init__("123:secret", authorized_chat_id, status=lambda _text: None)
        self.updates = updates
        self.sent = []

    def _request(self, method, values):
        if method == "getMe":
            return {"username": "remote_test_bot"}
        if method == "deleteWebhook":
            return True
        if method == "getUpdates":
            self.stop()
            return self.updates
        raise AssertionError(method)

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


class TelegramAdapterTests(unittest.TestCase):
    def test_invalid_token_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid Telegram bot token"):
            TelegramAdapter("not-a-token", None)

    def test_only_authorized_chat_executes_commands(self):
        updates = [
            {"update_id": 1, "message": {"text": "volume 20", "chat": {"id": 10, "type": "private"}}},
            {"update_id": 2, "message": {"text": "volume 30", "chat": {"id": 20, "type": "private"}}},
        ]
        adapter = FakeTelegramAdapter(20, updates)
        commands = []
        adapter.run(lambda text: commands.append(text) or "done")
        self.assertEqual(commands, ["volume 30"])
        self.assertEqual(adapter.sent, [(20, "done")])

    def test_id_is_available_before_pairing(self):
        updates = [
            {"update_id": 1, "message": {"text": "/id", "chat": {"id": 7654321, "type": "private"}}}
        ]
        adapter = FakeTelegramAdapter(None, updates)
        adapter.run(lambda _text: self.fail("Unpaired command executed"))
        self.assertEqual(adapter.sent, [(7654321, "Your Telegram chat ID is 7654321.")])

    def test_unpaired_commands_do_not_execute(self):
        updates = [
            {"update_id": 1, "message": {"text": "open notepad", "chat": {"id": 44, "type": "private"}}}
        ]
        adapter = FakeTelegramAdapter(None, updates)
        adapter.run(lambda _text: self.fail("Unpaired command executed"))
        self.assertIn("not paired", adapter.sent[0][1])

    def test_group_messages_are_ignored(self):
        updates = [
            {"update_id": 1, "message": {"text": "open notepad", "chat": {"id": 44, "type": "group"}}}
        ]
        adapter = FakeTelegramAdapter(44, updates)
        adapter.run(lambda _text: self.fail("Group command executed"))
        self.assertEqual(adapter.sent, [])
