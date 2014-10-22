# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.mail import get_connection, EmailMessage
from django.template.loader import render_to_string

from cosinnus.conf import settings


__all__ = ['CELERY_AVAILABLE', 'send_mail']


CELERY_AVAILABLE = False
if 'djcelery' in settings.INSTALLED_APPS:
    try:
        from celery.task import task
        CELERY_AVAILABLE = True
    except ImportError:
        pass


def _django_send_mail(to, subject, template, data, from_email=None, bcc=None):
    """ From django.core.mail, extended with bcc """
    if from_email is None:
        from_email = settings.COSINNUS_DEFAULT_FROM_EMAIL
    message = render_to_string(template, data)

    connection = get_connection()
    return EmailMessage(subject, message, from_email, [to], bcc,
                        connection=connection).send()


if CELERY_AVAILABLE:
    @task
    def send_mail(to, subject, template, data, from_email=None, bcc=None):
        return _django_send_mail.delay(to, subject, template, data,
                                       from_email=from_email, bcc=bcc)
else:
    def send_mail(to, subject, template, data, from_email=None, bcc=None):
        return _django_send_mail(to, subject, template, data,
                                 from_email=from_email, bcc=bcc)
