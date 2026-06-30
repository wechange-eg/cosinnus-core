import threading
import types
from functools import wraps

from django.conf import settings
from django.db import connections

if getattr(settings, 'COSINNUS_USE_WORKER_THREADS', True):
    _thread_local_state = threading.local()

    def is_threaded():
        """Determines if in the current context, CosinnusWorkerThread should run threaded or not"""
        if getattr(settings, 'COSINNUS_WORKER_THREADS_DISABLE_THREADING', False):
            return False

        if getattr(_thread_local_state, 'force_unthreaded', False):
            return False

        return True

    class cosinnus_worker_thread_threading_disabled:
        """
        Context manager that disables threading via CosinnusWorkerThread in its context

        Does nothing if `COSINNUS_USE_WORKER_THREADS` is False.
        """

        def __enter__(self):
            _thread_local_state.force_unthreaded = True

        def __exit__(self, type, value, tb):
            _thread_local_state.force_unthreaded = False

    class CosinnusWorkerThread(threading.Thread):
        """
        Custom Thread-Class ensuring that DB-Connections are closed when the thread ends.

        - If `COSINNUS_WORKER_THREADS_DISABLE_THREADING` is True, the `run` method is called directly in the main thread
        - Ensures, the Thread has a descriptive name including the actual class-name.
        """

        def start(self):
            # store threaded-state to skip join later if running unthreaded
            self._cosinnus_worker_thread_running_threaded = is_threaded()

            if not self._cosinnus_worker_thread_running_threaded:
                # run in main thread
                self._cosinnus_worker_thread_original_run()
                return

            super().start()

        def join(self, timeout=None):
            if self._cosinnus_worker_thread_running_threaded:
                super().join(timeout)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self._cosinnus_worker_thread_running_threaded = None

            if (type_name := type(self).__name__) not in self._name:
                self._name = f'{type_name}-{self._name}'

            self._cosinnus_worker_thread_original_run = self.run

            @wraps(self._cosinnus_worker_thread_original_run)
            def wrapped_run(self):
                try:
                    return self._cosinnus_worker_thread_original_run()
                finally:
                    if threading.current_thread() is not threading.main_thread():
                        connections.close_all()

            # assign wrapped_run as proper bound method
            self.run = types.MethodType(wrapped_run, self)
else:

    def is_threaded():
        """
        Stub-Method for context-getter. Returning always True.
        :return: True, since threading cannot be disabled
        """
        return True

    class cosinnus_worker_thread_threading_disabled:
        """
        Stub-Class for Contextmanager, does nothing.
        """

        def __enter__(self):
            pass

        def __exit__(self, type, value, tb):
            pass

    class CosinnusWorkerThread(threading.Thread):
        """Stub-Subclass of vanilla Thread, since WorkerThreads are disabled"""

        pass
