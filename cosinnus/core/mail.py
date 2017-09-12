# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.mail import get_connection, EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.models import get_current_site
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings

import logging
import sys
import html2text
from threading import Thread
from django.core.mail.message import EmailMultiAlternatives
from cosinnus.utils.user import get_list_unsubscribe_url
logger = logging.getLogger('cosinnus')

__all__ = ['CELERY_AVAILABLE', 'send_mail']


CELERY_AVAILABLE = False
if 'djcelery' in settings.INSTALLED_APPS:
    try:
        from celery.task import task
        CELERY_AVAILABLE = True
    except ImportError:
        pass


def _django_send_mail(to, subject, template, data, from_email=None, bcc=None, is_html=False):
    """ From django.core.mail, extended with bcc 
        Note: ``template`` can be None, if so we are looking for a ``content`` key in ``data`` to fill the email message."""
    
    if from_email is None:
        portal_name =  force_text(_(settings.COSINNUS_BASE_PAGE_TITLE_TRANS))
        # add from-email readable name (yes, this is how this works)
        from_email = '%(portal_name)s <%(from_email)s>' % {'portal_name': portal_name, 'from_email': settings.COSINNUS_DEFAULT_FROM_EMAIL}
        
    if data and 'unsubscribe_url' in data:
        unsubscribe_url = data.get('unsubscribe_url')
    else:
        unsubscribe_url = get_list_unsubscribe_url(to)
        data['unsubscribe_url'] = unsubscribe_url
        
    if template is not None:
        message = render_to_string(template, data)
    else:
        if not 'content' in data:
            import traceback
            logger.error('Could not send email because of missing template/content parameters. Detail in extra.', extra={'to': to, 'trace': traceback.format_exc()})
            return
        message = data['content']

    headers = {
        'List-Unsubscribe': '<%s>' % unsubscribe_url,
    }
    
    connection = get_connection()
    if is_html:
        text_message = convert_html_email_to_plaintext(message)
        mail = EmailMultiAlternatives(subject, text_message, from_email, [to], connection=connection, headers=headers)
        mail.attach_alternative(message, 'text/html')
        ret = mail.send()
    else:
        mail = EmailMessage(subject, message, from_email, [to], bcc, connection=connection, headers=headers)
        ret = mail.send()
    
    if getattr(settings, 'COSINNUS_LOG_SENT_EMAILS', False):
        try:
            from cosinnus.models.feedback import CosinnusSentEmailLog
            from cosinnus.models.group import CosinnusPortal
            CosinnusSentEmailLog.objects.create(email=to, title=subject, portal=CosinnusPortal.get_current())
        except Exception, e:
            logger.error('Error while trying to log a sent email!', extra={'exception': force_text(e)})
        
    return ret

if CELERY_AVAILABLE:
    @task
    def send_mail(to, subject, template, data, from_email=None, bcc=None, is_html=False):
        return _django_send_mail.delay(to, subject, template, data,
                                       from_email=from_email, bcc=bcc, is_html=is_html)
else:
    def send_mail(to, subject, template, data, from_email=None, bcc=None, is_html=False):
        return _django_send_mail(to, subject, template, data,
                                 from_email=from_email, bcc=bcc, is_html=is_html)
        
        
def convert_html_email_to_plaintext(html_message):
    """ Converts a cosinnus HTML rendered message to useful plaintext """
    
    htmler = html2text.HTML2Text()
    htmler.ignore_images = True
    htmler.body_width = 0
    text_message = htmler.handle(html_message)
    # clean text message from any lines containing ONLY '-' or '|' in any order, but preserve newlines
    clean_text = ''
    for line in text_message.split('\n'):
        line = line.strip()
        if len(line) > 0 and len(line.replace('|', '').replace('-', '').replace(' ', '')) == 0:
            continue
        if line.startswith('| '):
            continue
        clean_text += line + '\n'
    return clean_text


def _mail_print(to, subject, template, data, from_email=None, bcc=None, is_html=False):
    """ DEBUG ONLY """
    if settings.DEBUG:
        print ">> Mail printing:"
        if is_html:
            print ">> (HTML)"
        print ">> To: ", to
        print ">> Subject: ", force_text(subject)
        print ">> Body:"
        print render_to_string(template, data)
    
def send_mail_or_fail(to, subject, template, data, from_email=None, bcc=None, is_html=False):
    # remove newlines from header
    subject = subject.replace('\n', ' ').replace('\r', ' ')
    try:
        send_mail(to, subject, template, data, from_email, bcc, is_html=is_html)
        extra = {'to_user': to, 'subject': subject}
        logger.info('Cosinnus.core.mail: Successfully sent mail on site "%d".' % settings.SITE_ID, extra=extra)
    except Exception, e:
        # fail silently. log this, though
        extra = {'to_user': to, 'subject': subject, 'exception': force_text(e), 'exc_reason': e}
        try: 
            extra.update({'sys_except': sys.exc_info()[0]})
        except:
            extra.update({'sys_except': 'could not print'})
        logger.warn('Cosinnus.core.mail: Failed to send mail!', extra=extra)
        if settings.DEBUG:
            print ">> extra:", extra 
            _mail_print(to, subject, template, data, from_email, bcc, is_html)


def send_mail_or_fail_threaded(to, subject, template, data, from_email=None, bcc=None, is_html=False):
    mail_thread = MailThread()
    mail_thread.add_mail(to, subject, template, data, from_email, bcc, is_html=is_html)
    mail_thread.start()


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
            'team_name': group.name,
            'group': group,
        })
    if user:
        context.update({
            'user_name': user.get_full_name() or user.get_username(),
            'user': user,
        })
    return context



class MailThread(Thread):
    
    def __init__(self, *args, **kwargs):
        self.to = []
        self.subject = []
        self.template = []
        self.data = []
        self.from_email = []
        self.bcc = []
        self.is_html = []
        super(MailThread, self).__init__(*args, **kwargs)
        
    
    def add_mail(self, to, subject, template, data, from_email=None, bcc=None, is_html=False):
        self.to.append(to)
        self.subject.append(subject)
        self.template.append(template)
        self.data.append(data)
        self.from_email.append(from_email)
        self.is_html.append(is_html)
        self.bcc.append(bcc)
        
    def run(self):
        for i, to in enumerate(self.to):
            send_mail_or_fail(to, self.subject[i], self.template[i], self.data[i], self.from_email[i], self.bcc[i], is_html=self.is_html[i])
