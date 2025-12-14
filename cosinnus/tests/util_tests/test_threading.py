import threading
from unittest import skipIf

from django.conf import settings
from django.test import TestCase, override_settings

from cosinnus.utils.threading import CosinnusWorkerThread


@skipIf(not getattr(settings, 'COSINNUS_USE_WORKER_THREADS', False), 'CosinnusWorkerThreads disabled in settings')
class ThreadingTests(TestCase):
    def test_threading_activated(self):
        worker_thread_info = []

        class TestThread(CosinnusWorkerThread):
            def run(self):
                worker_thread_info.append(threading.current_thread().name)

        my_thread = TestThread()

        with override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=False):
            my_thread.start()
            my_thread.join(timeout=1)

        self.assertTrue(worker_thread_info[0].startswith('TestThread'), 'Worker thread not used despite enabled')

    def test_threading_deactivated(self):
        worker_thread_info = []

        class TestThread(CosinnusWorkerThread):
            def run(self):
                worker_thread_info.append(threading.current_thread().name)

        my_thread = TestThread()

        with override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=True):
            my_thread.start()
            my_thread.join(timeout=1)
        self.assertTrue(worker_thread_info[0].startswith('MainThread'), 'Worker thread used despite disabled')
