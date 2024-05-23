# -*- coding: utf-8 -*-
from functools import partial
from threading import Thread

import celery
from django.db import transaction

from cosinnus.celery import app as celery_app
from cosinnus.conf import settings
from cosinnus.core.mail import deliver_mail


class CeleryThreadTask(celery.Task):
    """
    Base celery task. If Celery is enabled the delay method is called. Otherwise, we run the task in a Thread.
    Note: Celery tasks fetch objects from the db. If a task is queued during an atomic transaction the data fetched by
    the task ist outdated. Need to wait until commit before executing a task. If no transaction is active on_commit is
    executed immediately.
    """

    def delay(self, *args, **kwargs):
        if settings.COSINNUS_USE_CELERY:
            # Pass task to Celery after transaction is finished.
            return transaction.on_commit(partial(super(CeleryThreadTask, self).delay, *args, **kwargs))
        else:
            # Runs task in a Thread after transaction is finished.
            task_run = super(CeleryThreadTask, self).__call__

            def run_task_threaded():
                class TaskThread(Thread):
                    def run(self):
                        task_run(*args, **kwargs)

                TaskThread().start()

            return transaction.on_commit(run_task_threaded)


@celery_app.task
def deliver_mail_task(to, subject, message, from_email, bcc=None, is_html=False, headers=None):
    deliver_mail(to, subject, message, from_email, bcc, is_html, headers)
