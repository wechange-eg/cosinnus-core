# -*- coding: utf-8 -*-
from cosinnus.celery import app as celery_app
from cosinnus.core.mail import deliver_mail


@celery_app.task
def deliver_mail_task(to, subject, message, from_email, bcc=None, is_html=False, headers=None):
    deliver_mail(to, subject, message, from_email, bcc, is_html, headers)
