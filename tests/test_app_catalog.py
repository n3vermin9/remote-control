import tempfile
import unittest
from pathlib import Path

from remote_control.app_catalog import AppCatalog, AppEntry, discover_start_menu_apps


class AppCatalogTests(unittest.TestCase):
    def test_normalized_lookup_supports_punctuation(self):
        catalog = AppCatalog([AppEntry("Visual Studio Code", "Code.exe")])
        self.assertEqual(catalog.find("visual-studio code").target, "Code.exe")

    def test_ampersand_is_spoken_as_and(self):
        catalog = AppCatalog([AppEntry("Movies & TV", "movies.exe")])
        self.assertEqual(catalog.find("movies and tv").target, "movies.exe")

    def test_duplicate_spoken_names_keep_first_safe_target(self):
        catalog = AppCatalog(
            [AppEntry("My App", "first.exe"), AppEntry("My-App", "second.exe")]
        )
        self.assertEqual(catalog.find("my app").target, "first.exe")

    def test_start_menu_shortcuts_are_discovered_recursively(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "Creative"
            folder.mkdir()
            shortcut = folder / "Photo Editor.lnk"
            shortcut.touch()
            entries = discover_start_menu_apps([root])
        self.assertEqual(entries, [AppEntry("Photo Editor", str(shortcut))])
