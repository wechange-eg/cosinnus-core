import threading
from unittest import skipIf

from django.conf import settings
from django.test import TestCase, override_settings

from cosinnus.utils.threading import CosinnusWorkerThread, cosinnus_worker_thread_threading_disabled, is_threaded


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

    def test_threading_contextmanager_thread_local(self):
        """Test if the _thread_local_state is truly thread-local or if other threads are affected"""
        worker_thread1_info = []
        worker_thread2_info = []
        thread1_ready = threading.Event()
        thread2_ready = threading.Event()

        class TestThread1(CosinnusWorkerThread):
            def run(self):
                # print(f'{threading.current_thread().name} started')
                # print(f'{threading.current_thread().name} waiting for thread2')
                thread2_ready.wait()
                worker_thread1_info.append(is_threaded())
                thread1_ready.set()

        class TestThread2(CosinnusWorkerThread):
            def run(self):
                # print(f'{threading.current_thread().name} started')
                with cosinnus_worker_thread_threading_disabled():
                    worker_thread2_info.append(is_threaded())
                    # print(f'{threading.current_thread().name} ready')
                    thread2_ready.set()
                    # print(f'{threading.current_thread().name} waiting for thread1')
                    thread1_ready.wait()

        my_thread1 = TestThread1()
        my_thread2 = TestThread2()

        # this test blocks if called with threading disabled
        with override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=False):
            my_thread1.start()
            my_thread2.start()
            my_thread1.join(timeout=1)
            my_thread2.join(timeout=1)
        self.assertTrue(worker_thread1_info[0], 'Threading in normal thread disabled, despite enabled')
        self.assertFalse(worker_thread2_info[0], 'threading in locally disabled context enabled')

    def test_threading_deactivated_by_contextmanager(self):
        worker_thread_info = []

        class TestThread(CosinnusWorkerThread):
            def run(self):
                worker_thread_info.append(threading.current_thread().name)

        my_thread = TestThread()

        with override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=False):
            with cosinnus_worker_thread_threading_disabled():
                my_thread.start()
                my_thread.join(timeout=1)
        self.assertTrue(
            worker_thread_info[0].startswith('MainThread'), 'Worker thread used despite disabled by contextmanager'
        )

    def test_threading_nested(self):
        worker_thread_info = []

        class TestThread(CosinnusWorkerThread):
            def run(self):
                worker_thread_info.append(threading.current_thread().name)

                class TestThreadNested(CosinnusWorkerThread):
                    def run(self):
                        worker_thread_info.append(threading.current_thread().name)

                my_thread_nested = TestThreadNested()
                my_thread_nested.start()
                my_thread_nested.join(timeout=1)

        my_thread = TestThread()
        with override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=False):
            my_thread.start()
            my_thread.join(timeout=1)

        self.assertTrue(worker_thread_info.pop(0).startswith('TestThread-'), 'Worker thread not used despite enabled')
        self.assertTrue(
            worker_thread_info.pop(0).startswith('TestThreadNested-'), 'Nested Worker thread not used despite enabled'
        )

    def test_threading_deactivated_by_contextmanager_nested(self):
        worker_thread_info = []

        class TestThread(CosinnusWorkerThread):
            def run(self):
                worker_thread_info.append(threading.current_thread().name)

                class TestThreadNested(CosinnusWorkerThread):
                    def run(self):
                        worker_thread_info.append(threading.current_thread().name)

                my_thread_nested = TestThreadNested()
                with cosinnus_worker_thread_threading_disabled():
                    my_thread_nested.start()
                    my_thread_nested.join(timeout=1)

        my_thread = TestThread()
        with override_settings(COSINNUS_WORKER_THREADS_DISABLE_THREADING=False):
            my_thread.start()
            my_thread.join(timeout=1)
        self.assertTrue(
            worker_thread_info.pop(0).startswith('TestThread-'), 'Worker thread not used at all despite enabled'
        )
        self.assertTrue(
            worker_thread_info.pop(0).startswith('TestThread-'),
            'Nested thread used despite disabled by disabled by contextmanager',
        )
