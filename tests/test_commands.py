import unittest

from remote_control.app_catalog import AppCatalog, AppEntry
from remote_control.commands import Action, Command, CommandParser, grammar_phrases
from remote_control.executor import CommandExecutor


class FakeController:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda: self.calls.append(name)

    def open_app(self, spoken_name):
        self.calls.append(("open_app", spoken_name))
        return "Visual Studio Code"


class CommandTests(unittest.TestCase):
    def test_parser_normalizes_text(self):
        command = CommandParser().parse("  OPEN   NOTEPAD ")
        self.assertEqual(command, Command(Action.OPEN_NOTEPAD, "open notepad"))

    def test_unknown_command_is_ignored(self):
        self.assertIsNone(CommandParser().parse("delete all files"))

    def test_vosk_grammar_contains_unknown_token(self):
        self.assertIn("open calculator", grammar_phrases())
        self.assertIn("next song", grammar_phrases())
        self.assertNotIn("next track", grammar_phrases())
        self.assertIn("[unk]", grammar_phrases())

    def test_parser_opens_an_installed_app_by_name(self):
        catalog = AppCatalog([AppEntry("Visual Studio Code", "Code.exe")])
        command = CommandParser(catalog).parse("launch visual studio code")
        self.assertEqual(
            command,
            Command(Action.OPEN_APP, "launch visual studio code", "visual studio code"),
        )

    def test_app_names_are_added_to_voice_grammar(self):
        phrases = grammar_phrases(["visual studio code"])
        self.assertIn("open visual studio code", phrases)
        self.assertIn("start visual studio code", phrases)
        self.assertIn("launch visual studio code", phrases)
        self.assertIn("run visual studio code", phrases)
        self.assertIn("open up visual studio code", phrases)

    def test_common_variations_map_to_safe_actions(self):
        cases = {
            "make it louder": Action.VOLUME_UP,
            "make it quieter": Action.VOLUME_DOWN,
            "resume music": Action.MEDIA_PLAY_PAUSE,
            "skip this song": Action.MEDIA_NEXT,
            "back one song": Action.MEDIA_PREVIOUS,
            "show desktop": Action.SHOW_DESKTOP,
            "maximize this window": Action.MAXIMIZE_WINDOW,
            "capture screen": Action.SCREENSHOT,
            "previous page": Action.BROWSER_BACK,
            "scroll down": Action.SCROLL_DOWN,
        }
        parser = CommandParser()
        for phrase, action in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(parser.parse(phrase).action, action)

    def test_executor_opens_dynamic_app(self):
        controller = FakeController()
        result = CommandExecutor(controller).execute(
            Command(Action.OPEN_APP, "open visual studio code", "visual studio code")
        )
        self.assertEqual(controller.calls, [("open_app", "visual studio code")])
        self.assertEqual(result.message, "Opening Visual Studio Code")

    def test_executor_calls_platform_layer(self):
        controller = FakeController()
        result = CommandExecutor(controller).execute(Command(Action.VOLUME_UP, "volume up"))
        self.assertEqual(controller.calls, ["volume_up"])
        self.assertEqual(result.message, "Volume up")
        self.assertFalse(result.should_quit)

    def test_quit_does_not_call_platform_layer(self):
        controller = FakeController()
        result = CommandExecutor(controller).execute(Command(Action.QUIT, "quit remote control"))
        self.assertEqual(controller.calls, [])
        self.assertTrue(result.should_quit)
