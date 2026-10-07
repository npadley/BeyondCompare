import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch


class View:
    def __init__(self, path):
        self.path = path

    def file_name(self):
        return self.path


class Sheet:
    def __init__(self, view):
        self.text_view = view

    def view(self):
        return self.text_view


class Window:
    def __init__(self, active, groups):
        self.active = active
        self.groups = groups

    def active_view(self):
        return self.active

    def num_groups(self):
        return len(self.groups)

    def sheets_in_group(self, group):
        return self.groups[group]


class WindowCommand:
    def __init__(self, window):
        self.window = window


class TabCompareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.executable = str(Path(self.temp.name) / 'Beyond Compare')
        Path(self.executable).touch()
        self.errors = []
        sublime = types.ModuleType('sublime')
        sublime.platform = lambda: 'windows'
        sublime.load_settings = lambda name: {'beyond_compare_path': self.executable}
        sublime.error_message = self.errors.append
        plugin = types.ModuleType('sublime_plugin')
        plugin.ApplicationCommand = type('ApplicationCommand', (), {})
        plugin.WindowCommand = WindowCommand
        plugin.EventListener = type('EventListener', (), {})
        spec = importlib.util.spec_from_file_location(
            'beyond_compare_under_test', Path(__file__).resolve().parents[1] / 'BeyondCompare.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'sublime': sublime, 'sublime_plugin': plugin}):
            spec.loader.exec_module(self.module)
        self.launch = self.enterContext(patch.object(self.module.subprocess, 'Popen'))
        self.active = View('/files/active file.txt')
        self.target = View('/files/target file.txt')
        self.window = Window(self.active, [[Sheet(self.active)], [Sheet(None), Sheet(self.target)]])

    def command(self):
        self.assertTrue(hasattr(self.module, 'BeyondCompareTabCommand'),
                        'The tab comparison command is missing')
        return self.module.BeyondCompareTabCommand(self.window)

    def test_compares_active_with_clicked_tab_across_groups(self):
        self.module.fileA, self.module.fileB = '/unrelated/a', '/unrelated/b'
        command = self.command()
        self.assertTrue(command.is_enabled(group=1, index=1))
        command.run(group=1, index=1)
        self.launch.assert_called_once_with(
            [self.executable, '/files/active file.txt', '/files/target file.txt'])
        self.assertEqual((self.module.fileA, self.module.fileB), ('/unrelated/a', '/unrelated/b'))
        self.assertIs(self.window.active, self.active)
        self.assertEqual(self.errors, [])

    def test_same_group_uses_clicked_tab_not_previous_file(self):
        self.window.groups[0].append(Sheet(self.target))
        self.command().run(group=0, index=1)
        self.launch.assert_called_once_with(
            [self.executable, '/files/active file.txt', '/files/target file.txt'])

    def test_invalid_targets_are_disabled_and_do_not_launch(self):
        command = self.command()
        for group, index in [(0, 0), (1, 0), (-1, 0), (0, -1), (2, 0), (1, 2)]:
            with self.subTest(group=group, index=index):
                self.assertFalse(command.is_enabled(group=group, index=index))
                command.run(group=group, index=index)
        self.launch.assert_not_called()

    def test_unsaved_tabs_and_missing_active_view_are_disabled(self):
        for active, target in [(View(None), self.target), (self.active, View(None)), (None, self.target)]:
            with self.subTest(active=active, target=target):
                self.window.active = active
                self.window.groups[1][1] = Sheet(target)
                command = self.command()
                self.assertFalse(command.is_enabled(group=1, index=1))
                command.run(group=1, index=1)
        self.launch.assert_not_called()

    def test_two_views_of_same_file_are_disabled(self):
        self.window.groups[1][1] = Sheet(View(self.active.file_name()))
        self.assertFalse(self.command().is_enabled(group=1, index=1))

    def test_missing_executable_reports_error(self):
        Path(self.executable).unlink()
        self.command().run(group=1, index=1)
        self.launch.assert_not_called()
        self.assertEqual(len(self.errors), 1)

    def test_show_diff_still_uses_last_two_activated_files(self):
        self.module.recordActiveFile('/files/first.txt')
        self.module.recordActiveFile('/files/second.txt')
        self.module.BeyondCompareCommand().run()
        self.launch.assert_called_once_with(
            [self.executable, '/files/second.txt', '/files/first.txt'])

    def test_show_diff_requires_two_files(self):
        self.module.recordActiveFile('/files/first.txt')
        self.module.BeyondCompareCommand().run()
        self.launch.assert_not_called()
        self.assertEqual(len(self.errors), 1)


if __name__ == '__main__':
    unittest.main()
