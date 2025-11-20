import threading
from functools import wraps

from django.conf import settings
from django.db import connections


class DjangoWorkerThread(threading.Thread):
    """
    Custom Thread-Class ensuring that DB-Connections are closed when the thread ends.

    - If `COSINNUS_USE_WORKER_THREADS` is False, the `run` method is called directly in the main thread.
    - Ensures, the Thread has a descriptive name including the actual class-name.
    """

    def start(self):
        if not getattr(settings, 'COSINNUS_USE_WORKER_THREADS', True):
            # run in main thread
            self._original_run()
            return
        super().start()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (type_name := type(self).__name__) not in self._name:
            self._name = f'{type_name}-{self._name}'

        self._original_run = self.run

        @wraps(self._original_run)
        def wrapped_run():
            try:
                return self._original_run()
            finally:
                connections.close_all()

        self.run = wrapped_run
