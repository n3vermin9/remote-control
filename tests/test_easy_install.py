import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EasyInstallTests(unittest.TestCase):
    def test_installer_bootstraps_environment_model_and_autostart(self):
        installer = (ROOT / "INSTALL.bat").read_text(encoding="utf-8")
        self.assertIn('-m venv ".venv"', installer)
        self.assertIn("-m pip install --disable-pip-version-check -e .", installer)
        self.assertIn('"scripts\\download_model.py"', installer)
        self.assertIn("--install-autostart", installer)
        self.assertNotIn("webcam", installer.casefold())

    def test_launcher_starts_hidden_without_f8_mode(self):
        launcher = (ROOT / "START.bat").read_text(encoding="utf-8")
        self.assertIn('".venv\\Scripts\\pythonw.exe" -m remote_control', launcher)
        self.assertNotIn("f8", launcher.casefold())
        self.assertFalse((ROOT / "START_F8.bat").exists())
        self.assertFalse((ROOT / "START_ALWAYS_LISTENING.bat").exists())
        self.assertTrue((ROOT / "src" / "remote_control" / "__main__.py").exists())
