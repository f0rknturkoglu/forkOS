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


class ShutdownTests(unittest.TestCase):
    def test_process_scope_excludes_unrelated_models_and_python(self):
        home = str(Path.home())
        output = f"123 {home}/.hermes/tools/llamacpp/llama-server --api-key SECRET\n124 /opt/bin/python unrelated.py\n125 /opt/bin/llama-server --model other.gguf"
        with patch.object(launcher, 'run', return_value=output):
            self.assertEqual(list(launcher.project_processes()), [123])

    def test_pid_is_rechecked_before_signal(self):
        with patch.object(launcher, 'project_processes', side_effect=[{123: 'owned'}, {123: 'changed'}, {}]):
            with patch.object(launcher.os, 'kill') as kill:
                launcher.stop_processes()
        kill.assert_not_called()

    def test_containers_stop_writers_before_db_without_force_or_volume_deletion(self):
        commands = []
        def run(args, timeout=30):
            commands.append(args)
            if 'info' in args:
                return 'version'
            if 'ps' in args:
                return 'db-id\napi-id' if sum('ps' in cmd for cmd in commands) == 1 else ''
            if 'working_dir' in ' '.join(args):
                return str(launcher.ROOT)
            if 'service' in ' '.join(args):
                return 'db' if args[-1] == 'db-id' else 'api'
            return ''
        with patch.object(launcher, 'run', side_effect=run):
            launcher.stop_containers()
        stopped = [cmd for cmd in commands if 'stop' in cmd]
        self.assertEqual([cmd[-1] for cmd in stopped], ['api-id', 'db-id'])
        self.assertTrue(all(cmd[cmd.index('--time') + 1] == '-1' for cmd in stopped))
        self.assertFalse(any('rm' in cmd or 'down' in cmd for cmd in commands))

    def test_foreign_checkout_is_not_stopped(self):
        with patch.object(launcher, 'run', side_effect=['version', 'id', '/other/project']):
            with self.assertRaisesRegex(RuntimeError, 'başka bir checkout'):
                launcher.stop_containers()

    def test_shared_engine_is_kept_running(self):
        with patch.object(launcher.shutil, 'which', return_value='/bin/orb'):
            with patch.object(launcher, 'run', side_effect=['other-container', '']) as run:
                self.assertIn('açık bırakıldı', launcher.stop_engine())
        self.assertFalse(any('stop' in call.args[0] for call in run.call_args_list))

    def test_closed_engine_is_not_woken_for_repeat_stop(self):
        error = launcher.subprocess.CalledProcessError(1, ['docker', 'ps'])
        with patch.object(launcher.shutil, 'which', return_value='/bin/orb'):
            with patch.object(launcher, 'run', side_effect=error) as run:
                self.assertIn('ek kapatma uygulanmadı', launcher.stop_engine())
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('orb', run.call_args.args[0])

    def test_shutdown_keeps_going_after_failure_and_does_not_stop_engine(self):
        labels = []
        def step(label, action):
            labels.append(label)
            if label == 'forkOS container’ları':
                raise SystemExit(1)
        with patch.object(launcher, 'step', side_effect=step), patch('builtins.print'):
            with self.assertRaises(SystemExit) as result:
                launcher.stop()
        self.assertEqual(result.exception.code, 1)
        self.assertIn('Son kontrol', labels)
        self.assertNotIn('OrbStack', labels)


if __name__ == '__main__':
    unittest.main()
