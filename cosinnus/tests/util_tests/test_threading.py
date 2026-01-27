import io
import logging
import threading
from functools import wraps
from threading import current_thread
from unittest import skipIf
from unittest.mock import patch

from django.conf import settings
from django.db import connections
from django.test import TestCase, override_settings

from cosinnus.utils.threading import CosinnusWorkerThread, cosinnus_worker_thread_threading_disabled, is_threaded


@skipIf(
    not getattr(settings, 'COSINNUS_USE_WORKER_THREADS', False), 'depends on CosinnusWorkerThreads, which are disabled'
)
@override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=False)
class CosinnusWorkerThreadTests(TestCase):
    class TestThread(CosinnusWorkerThread):
        """reusable Thread-Class storing its own name for later evaluation"""

        def __init__(self, results, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.results = results

        def run(self):
            self.results.append(threading.current_thread().name)

    def _run_thread(self):
        """starts a thread and returns the thread-name active during its runtime"""
        results = []
        thread = self.TestThread(results)
        thread.start()
        thread.join()
        return results

    def test_threading_enabled(self):
        results = self._run_thread()

        self.assertTrue(results[0].startswith('TestThread'), 'Worker thread not used despite enabled')

    @override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=True)
    def test_threading_disabled(self):
        results = self._run_thread()

        self.assertTrue(results[0].startswith('MainThread'), 'Worker thread used despite disabled')

    def test_threading_disabled_by_contextmanager(self):
        with cosinnus_worker_thread_threading_disabled():
            results = self._run_thread()

        self.assertTrue(results[0].startswith('MainThread'), 'Worker thread used despite disabled by contextmanager')

    def test_threading_disabled_by_contextmanager_locally_only(self):
        """Test if the _thread_local_state is truly thread-local or if other threads are affected"""
        other_thread_results = []
        no_nesting_thread_results = []

        other_thread_ready = threading.Event()
        no_nesting_thread_ready = threading.Event()

        class OtherThread(CosinnusWorkerThread):
            def run(self):
                # print(f'{threading.current_thread().name} started')
                # print(f'{threading.current_thread().name} waiting for no_nesting_thread')
                no_nesting_thread_ready.wait()
                other_thread_results.append(is_threaded())
                other_thread_ready.set()

        class NoNestingThread(CosinnusWorkerThread):
            def run(self):
                # print(f'{threading.current_thread().name} started')
                with cosinnus_worker_thread_threading_disabled():
                    no_nesting_thread_results.append(is_threaded())
                    # print(f'{threading.current_thread().name} ready')
                    no_nesting_thread_ready.set()
                    # print(f'{threading.current_thread().name} waiting for other_thread')
                    other_thread_ready.wait()

        other_thread = OtherThread()
        no_nesting_thread = NoNestingThread()

        other_thread.start()
        no_nesting_thread.start()

        other_thread.join()
        no_nesting_thread.join()

        self.assertTrue(other_thread_results[0], 'Threading in other thread disabled, despite enabled')
        self.assertFalse(no_nesting_thread_results[0], 'Threading in locally disabled context enabled')

    def test_threading_nested_enabled(self):
        results = []

        class OuterThread(CosinnusWorkerThread):
            def run(self):
                results.append(threading.current_thread().name)
                # noinspection PyTypeChecker
                inner_thread = CosinnusWorkerThreadTests.TestThread(results, name='InnerThread-TestThread')
                inner_thread.start()
                inner_thread.join()

        outer_thread = OuterThread()
        outer_thread.start()
        outer_thread.join()

        self.assertTrue(results[0].startswith('OuterThread'), 'Outer thread not used despite enabled')
        self.assertTrue(results[1].startswith('InnerThread'), 'Inner thread not used despite enabled')

    def test_threading_nested_disabled_by_contextmanager(self):
        results = []

        class OuterThread(CosinnusWorkerThread):
            def run(self):
                results.append(threading.current_thread().name)
                with cosinnus_worker_thread_threading_disabled():
                    # noinspection PyTypeChecker
                    inner_thread = CosinnusWorkerThreadTests.TestThread(results, name='InnerThread-TestThread')
                    inner_thread.start()
                    inner_thread.join()

        outer_thread = OuterThread()
        outer_thread.start()
        outer_thread.join()

        self.assertTrue(results[0].startswith('OuterThread'), 'Worker thread not used at all despite enabled')
        # the inner run-method should run in the outer thread context
        self.assertEqual(results[0], results[1], 'Nested thread used despite disabled by disabled by contextmanager')

    # sentry-sdk wraps the run-method to capture Thead-Exceptions
    # https://github.com/getsentry/sentry-python/blob/e73e600ea1d151cf2dfb9345de8c6c77d7bd9b1f/sentry_sdk/integrations/threading.py#L108
    def test_wrapping_run_like_sentry(self):
        results = []
        thread = self.TestThread(results)
        logger = logging.getLogger(f'{__name__}.test_wrapping_run_like_sentry')
        logger.propagate = False
        original_run = getattr(thread.run, '__func__', self.run)

        @wraps(original_run)
        def sentry_like_wrapper(*args, **kwargs):
            logger.debug('sentry_like_wrapper called')
            _self = current_thread()
            # noinspection PyBroadException
            try:
                return original_run(_self, *args[1:], **kwargs)
            except Exception:
                logger.exception('Exception raised while running thread')

        thread.run = sentry_like_wrapper

        with self.assertLogs(logger, level='DEBUG') as cm:
            thread.start()
            thread.join()

        self.assertGreater(len(cm.output), 0, 'sentry-like run-wrapper was not called')
        self.assertFalse(
            any('ERROR' in entry for entry in cm.output),
            'Exception raised while running thread with sentry-like wrapped run',
        )

    @patch.object(connections, 'close_all')
    def test_db_cleanup_is_called_once_normal(self, mock_close_all):
        self._run_thread()

        mock_close_all.assert_called_once()

    @patch.object(connections, 'close_all')
    def test_db_cleanup_is_called_once_on_error(self, mock_close_all):
        class TestThread(CosinnusWorkerThread):
            def run(self):
                raise Exception('TestError')

        thread = TestThread()

        with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
            thread.start()
            thread.join()

        self.assertTrue('Exception: TestError' in fake_stderr.getvalue(), 'TestError was not triggered')
        self.assertEqual(fake_stderr.getvalue().count('Traceback'), 1, 'unexpected Errors occurred')
        mock_close_all.assert_called_once()

    @patch.object(connections, 'close_all')
    def test_db_cleanup_is_called_once_subclass_without_super(self, mock_close_all):
        class TestThread(CosinnusWorkerThread):
            def run(self):
                pass

        class SubTestThread(TestThread):
            def run(self):
                pass

        thread = SubTestThread()

        thread.start()
        thread.join()
        mock_close_all.assert_called_once()

    @patch.object(connections, 'close_all')
    def test_db_cleanup_is_called_once_subclass_with_super(self, mock_close_all):
        class TestThread(CosinnusWorkerThread):
            def run(self):
                pass

        class SubTestThread(TestThread):
            def run(self):
                super().run()

        thread = SubTestThread()

        thread.start()
        thread.join()
        mock_close_all.assert_called_once()

    @patch.object(connections, 'close_all')
    def test_db_cleanup_not_called_in_main_thread(self, mock_close_all):
        thread = CosinnusWorkerThread()

        thread.run()
        thread.join()
        mock_close_all.assert_not_called()

    @patch.object(connections, 'close_all')
    def test_error_in_db_cleanup(self, mock_close_all):
        mock_close_all.side_effect = Exception('TestError')

        thread = CosinnusWorkerThread()

        with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
            thread.start()
            thread.join()

        self.assertTrue('Exception: TestError' in fake_stderr.getvalue(), 'TestError was not triggered')
        self.assertEqual(fake_stderr.getvalue().count('Traceback'), 1, 'unexpected Errors occurred')
        mock_close_all.assert_called_once()
