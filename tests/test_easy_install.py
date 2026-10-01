import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EasyInstallTests(unittest.TestCase):
    def test_installer_bootstraps_telegram_app_and_autostart(self):
        installer = (ROOT / "INSTALL.bat").read_text(encoding="utf-8")
        self.assertIn('-m venv ".venv"', installer)
        self.assertIn("-m pip install --disable-pip-version-check -e .", installer)
        self.assertIn("--install-autostart", installer)
        self.assertIn("pip uninstall --yes remote-control-voice", installer)
        self.assertIn("vosk", installer)
        self.assertIn("sounddevice", installer)
        self.assertIn("opencv-contrib-python", installer)
        self.assertIn("pynput", installer)
        self.assertNotIn("download_model.py", installer)

    def test_launcher_starts_hidden_without_f8_mode(self):
        launcher = (ROOT / "START.bat").read_text(encoding="utf-8")
        self.assertIn('".venv\\Scripts\\pythonw.exe" -m remote_control', launcher)
        self.assertNotIn("f8", launcher.casefold())
        self.assertFalse((ROOT / "START_F8.bat").exists())
        self.assertFalse((ROOT / "START_ALWAYS_LISTENING.bat").exists())
        self.assertTrue((ROOT / "src" / "remote_control" / "__main__.py").exists())
