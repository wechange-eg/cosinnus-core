# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.mail import get_connection, EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.models import get_current_site
from django.utils.encoding import force_text

from cosinnus.conf import settings

import logging
logger = logging.getLogger('cosinnus')

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
        
        
        

def _mail_print(to, subject, template, data, from_email=None, bcc=None):
    """ DEBUG ONLY """
    if settings.DEBUG:
        print ">> Mail printing:"
        print ">> To: ", to
        print ">> Subject: ", force_text(subject)
        print ">> Body:"
        print render_to_string(template, data)
    
def send_mail_or_fail(to, subject, template, data, from_email=None, bcc=None):
    # remove newlines from header
    subject = subject.replace('\n', ' ').replace('\r', ' ')
    try:
        send_mail(to, subject, template, data, from_email, bcc)
    except Exception, e:
        # fail silently. log this, though
        if settings.DEBUG:
            _mail_print(to, subject, template, data, from_email, bcc)
        logger.error('Cosinnus.core.mail: Failed to send mail!', 
                     extra={'to_user': to, 'subject': subject, 'exception': str(e)})
    

def get_common_mail_context(request, group=None, user=None):
    """ Collects common context variables for Email templates """
    
    site = get_current_site(request)
    protocol = request.is_secure() and 'https' or 'http'
    context = {
        'site': site,
        'site_name': site.name,
        'protocol': protocol,
        'domain_url': "%s://%s" % (protocol, site.domain),
    }
    if group:
        context.update({
            'group_name': group.name,
            'group': group,
        })
    if user:
        context.update({
            'user_name': user.get_full_name() or user.get_username(),
            'user': user,
        })
    return context
