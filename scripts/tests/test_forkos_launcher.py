import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).parents[1] / 'forkos.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_install_preserves_user_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            rc = home / '.zshrc'
            rc.write_text('export MY_SETTING=kept\n')
            with patch.object(launcher.Path, 'home', return_value=home):
                launcher.install()
                first = rc.read_text()
                launcher.install()
            self.assertEqual(first, rc.read_text())
            self.assertIn('export MY_SETTING=kept', first)
            self.assertEqual(first.count('alias forkos='), 1)

    def test_wait_retries_transient_errors(self):
        with patch.object(launcher.time, 'sleep'), patch.object(launcher.time, 'monotonic', side_effect=[0, 0, 1]):
            with patch('builtins.print'):
                check = unittest.mock.Mock(side_effect=[OSError(), False, True])
                launcher.wait(check, 10)
        self.assertEqual(check.call_count, 3)

    def test_wait_has_deadline(self):
        with patch.object(launcher.time, 'monotonic', side_effect=[0, 11]):
            with self.assertRaises(RuntimeError):
                launcher.wait(lambda: False, 10)

    def test_step_does_not_claim_success_on_failure(self):
        with patch('builtins.print') as output:
            with self.assertRaises(SystemExit) as result:
                launcher.step('Backend', lambda: (_ for _ in ()).throw(RuntimeError('unavailable')))
        self.assertEqual(result.exception.code, 1)
        self.assertFalse(any('✓' in str(call) for call in output.call_args_list))


if __name__ == '__main__':
    unittest.main()
