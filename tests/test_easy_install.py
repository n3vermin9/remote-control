import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EasyInstallTests(unittest.TestCase):
    def test_installer_bootstraps_environment_app_and_model(self):
        installer = (ROOT / "INSTALL.bat").read_text(encoding="utf-8")
        self.assertIn('-m venv ".venv"', installer)
        self.assertIn("-m pip install --disable-pip-version-check -e .", installer)
        self.assertIn('"scripts\\download_model.py"', installer)

    def test_default_launcher_uses_f8_mode(self):
        launcher = (ROOT / "START_F8.bat").read_text(encoding="utf-8")
        self.assertIn('".venv\\Scripts\\remote-control.exe" --mode f8', launcher)

    def test_continuous_launcher_uses_always_mode(self):
        launcher = (ROOT / "START_ALWAYS_LISTENING.bat").read_text(encoding="utf-8")
        self.assertIn('".venv\\Scripts\\remote-control.exe" --mode always', launcher)
