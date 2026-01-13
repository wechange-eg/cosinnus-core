import threading
from unittest import skipIf

from django.conf import settings
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
        thread.join(timeout=1)
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

        other_thread.join(timeout=1)
        no_nesting_thread.join(timeout=1)

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
                inner_thread.join(timeout=1)

        outer_thread = OuterThread()
        outer_thread.start()
        outer_thread.join(timeout=1)

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
                    inner_thread.join(timeout=1)

        outer_thread = OuterThread()
        outer_thread.start()
        outer_thread.join(timeout=1)

        self.assertTrue(results[0].startswith('OuterThread'), 'Worker thread not used at all despite enabled')
        # the inner run-method should run in the outer thread context
        self.assertEqual(results[0], results[1], 'Nested thread used despite disabled by disabled by contextmanager')
