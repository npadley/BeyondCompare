import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch


class Settings(dict):
    def set(self, key, value):
        self[key] = value


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(beyond_compare_path='missing')
        self.errors, self.saves = [], []
        sublime = types.ModuleType('sublime')
        sublime.platform = lambda: 'windows'
        sublime.load_settings = lambda name: self.settings
        sublime.error_message = self.errors.append
        sublime.save_settings = self.saves.append
        plugin = types.ModuleType('sublime_plugin')
        for name in ('ApplicationCommand', 'WindowCommand', 'EventListener'):
            setattr(plugin, name, type(name, (), {}))
        spec = importlib.util.spec_from_file_location(
            'detection_under_test', Path(__file__).resolve().parents[1] / 'BeyondCompare.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'sublime': sublime, 'sublime_plugin': plugin}):
            spec.loader.exec_module(self.module)
        self.enterContext(patch.dict('os.environ', {
            'ProgramFiles': str(self.root / 'Program Files'),
            'ProgramFiles(x86)': str(self.root / 'Program Files (x86)')
        }, clear=True))

    def install(self, folder, version):
        path = self.root / folder / ('Beyond Compare ' + str(version)) / 'BCompare.exe'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return str(path)

    def test_detects_both_versions_in_both_program_files_locations(self):
        for version in (5, 4):
            for folder in ('Program Files', 'Program Files (x86)'):
                with self.subTest(version=version, folder=folder):
                    path = self.install(folder, version)
                    self.settings['beyond_compare_path'] = 'missing'
                    self.module.plugin_loaded()
                    self.assertEqual(self.settings['beyond_compare_path'], path)
                    self.assertTrue(Path(self.settings['beyond_compare_path']).exists())
                    Path(path).unlink()
        self.assertEqual(len(self.saves), 4)
        self.assertEqual(self.errors, [])

    def test_prefers_version_five_even_when_four_is_in_other_folder(self):
        self.install('Program Files', 4)
        expected = self.install('Program Files (x86)', 5)
        self.module.plugin_loaded()
        self.assertEqual(self.settings['beyond_compare_path'], expected)

    def test_preserves_valid_configured_path_and_does_not_resave(self):
        expected = self.install('Custom Tools', 4)
        self.install('Program Files', 5)
        for configured in (expected, {'windows': expected, 'osx': '/custom/bcompare'}):
            with self.subTest(configured=configured):
                self.settings['beyond_compare_path'] = configured
                self.module.plugin_loaded()
                self.assertEqual(self.settings['beyond_compare_path'], configured)
        self.assertEqual(self.saves, [])
        self.assertEqual(self.errors, [])

    def test_missing_x86_environment_variable_does_not_block_detection(self):
        del self.module.os.environ['ProgramFiles(x86)']
        expected = self.install('Program Files', 5)
        self.module.plugin_loaded()
        self.assertEqual(self.settings['beyond_compare_path'], expected)

    def test_missing_program_files_variable_still_detects_x86_install(self):
        del self.module.os.environ['ProgramFiles']
        expected = self.install('Program Files (x86)', 5)
        self.module.plugin_loaded()
        self.assertEqual(self.settings['beyond_compare_path'], expected)

    def test_non_windows_startup_does_not_change_settings(self):
        self.install('Program Files', 5)
        with patch.object(self.module.sublime, 'platform', return_value='osx'):
            self.module.plugin_loaded()
        self.assertEqual(self.settings['beyond_compare_path'], 'missing')
        self.assertEqual(self.saves, [])
        self.assertEqual(self.errors, [])

    def test_no_environment_variables_reports_one_error_without_saving(self):
        with patch.dict('os.environ', {}, clear=True):
            self.module.plugin_loaded()
        self.assertEqual(len(self.errors), 1)
        self.assertEqual(self.saves, [])

    def test_missing_setting_is_detected_and_persisted_only_once(self):
        self.settings.clear()
        expected = self.install('Program Files', 5)
        self.module.plugin_loaded()
        self.module.plugin_loaded()
        self.assertEqual(self.settings['beyond_compare_path'], expected)
        self.assertEqual(len(self.saves), 1)
        self.assertEqual(self.errors, [])

    def test_repairs_previously_quoted_setting(self):
        expected = self.install('Program Files (x86)', 4)
        self.settings['beyond_compare_path'] = '"' + expected + '"'
        self.module.plugin_loaded()
        self.assertEqual(self.settings['beyond_compare_path'], expected)
        self.assertEqual(len(self.saves), 1)


if __name__ == '__main__':
    unittest.main()
