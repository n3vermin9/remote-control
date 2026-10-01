import unittest

from remote_control.commands import Action, Command, CommandParser, grammar_phrases
from remote_control.executor import CommandExecutor


class FakeController:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda: self.calls.append(name)


class CommandTests(unittest.TestCase):
    def test_parser_normalizes_text(self):
        command = CommandParser().parse("  OPEN   NOTEPAD ")
        self.assertEqual(command, Command(Action.OPEN_NOTEPAD, "open notepad"))

    def test_unknown_command_is_ignored(self):
        self.assertIsNone(CommandParser().parse("delete all files"))

    def test_vosk_grammar_contains_unknown_token(self):
        self.assertIn("open calculator", grammar_phrases())
        self.assertIn("[unk]", grammar_phrases())

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
