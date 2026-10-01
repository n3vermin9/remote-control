import tempfile
import unittest
from pathlib import Path

from remote_control.config import Settings


class ConfigTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            expected = Settings(telegram_token="123:secret", authorized_chat_id=123456)
            expected.save(path)
            self.assertEqual(Settings.load(path), expected)
