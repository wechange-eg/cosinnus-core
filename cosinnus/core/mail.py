# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.mail import send_mail as django_send_mail
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


def _send_mail(to, subject, template, data, from_email=None):
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    message = render_to_string(template, data)
    django_send_mail(subject, message, from_email, [to])


if CELERY_AVAILABLE:
    @task
    def send_mail(to, subject, template, data, from_email=None):
        _send_mail.delay(to, subject, template, data)
else:
    def send_mail(to, subject, template, data, from_email=None):
        _send_mail(to, subject, template, data)
