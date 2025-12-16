# -*- coding: utf-8 -*-
import logging
from functools import partial

import celery
from django.db import transaction

from cosinnus.celery import app as celery_app
from cosinnus.conf import settings
from cosinnus.core.mail import deliver_mail
from cosinnus.utils.threading import CosinnusWorkerThread
from cosinnus.models import CosinnusGroupMembership
from cosinnus.models.membership import PENDING_STATUS

logger = logging.getLogger('cosinnus')


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
                class TaskThread(CosinnusWorkerThread):
                    def run(self):
                        task_run(*args, **kwargs)

                TaskThread().start()

            return transaction.on_commit(run_task_threaded)


@celery_app.task
def deliver_mail_task(to, subject, message, from_email, bcc=None, is_html=False, headers=None):
    deliver_mail(to, subject, message, from_email, bcc, is_html, headers)


@celery_app.task(base=CeleryThreadTask)
def remove_pending_memberships_for_user_task(user_id: int):
    """
    Deletes all membership objects in type `PENDING_STATUS` for a given user.

    This is a background task.
    """
    try:
        with transaction.atomic():
            for membership in CosinnusGroupMembership.objects.filter(
                user__id=user_id, status__in=PENDING_STATUS
            ).select_for_update():
                membership.delete()
    except Exception as e:
        logger.error(e)
        logger.error(
            (
                'An error occurred during deletion of stale pending group memberships for deactivated user. '
                'Exception in extra'
            ),
            extra={'exc': e},
        )
