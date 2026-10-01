import tempfile
import unittest
from pathlib import Path

from remote_control.config import Settings


class ConfigTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            expected = Settings(mode="always", input_device=2, sample_rate=16000)
            expected.save(path)
            self.assertEqual(Settings.load(path), expected)
