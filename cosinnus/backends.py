# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.mail.backends.smtp import EmailBackend
from django.utils.decorators import method_decorator

from cosinnus.utils.user import get_user_by_email_safe
from cosinnus.conf import settings

import dkim
import smtplib
from django.core.mail.message import sanitize_address

from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchEngine
from urllib3.exceptions import ProtocolError, ConnectionError
from elasticsearch.exceptions import TransportError

import logging 
from django.utils.encoding import force_text
logger = logging.getLogger('cosinnus')


USER_MODEL = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    Email Authentication Backend
    
    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
    """
    
    def authenticate(self, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        email = username.lower().strip()
        user = get_user_by_email_safe(email)
        if user and user.check_password(password):
            return user

    def get_user(self, user_id):
        """ Get a User object from the user_id. """
        try:
            return USER_MODEL.objects.get(pk=user_id)
        except USER_MODEL.DoesNotExist:
            return None


class DKIMEmailBackend(EmailBackend):
    
    def _send(self, email_message):
        """A helper method that does the actual sending + DKIM signing."""
        if not email_message.recipients():
            return False
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.recipients()]
        message = email_message.message()
        
        try:
            message_string = message.as_string()
            signature = dkim.sign(message_string,
                                  settings.DKIM_SELECTOR,
                                  settings.DKIM_DOMAIN,
                                  settings.DKIM_PRIVATE_KEY)
            self.connection.sendmail(from_email, recipients, signature+message_string)
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True
    

class RobustElasticSearchBackend(ElasticsearchSearchBackend):
    """A robust backend that doesn't crash when no connection is available"""

    def mute_error(f):
        def error_wrapper(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except (TransportError, ProtocolError, ConnectionError) as e:
                logger.exception('Could not connect to the ElasticSearch backend for indexing! The search function will not work and saving objects on the site will be terribly slow! Exception in extra.', extra={'exception': force_text(e)})
            except Exception as e:
                logger.exception('An unknown error occured while indexing an object! Exception in extra.', extra={'exception': force_text(e)})
        return error_wrapper

    def __init__(self, connectionalias, **options):
        super(RobustElasticSearchBackend, self).__init__(connectionalias, **options)

    @mute_error
    def update(self, indexer, iterable, commit=True):
        super(RobustElasticSearchBackend, self).update(indexer, iterable, commit)

    @mute_error
    def remove(self, obj, commit=True):
        super(RobustElasticSearchBackend, self).remove(obj, commit)

    @mute_error
    def clear(self, models=[], commit=True):
        super(RobustElasticSearchBackend, self).clear(models, commit)

class RobustElasticSearchEngine(ElasticsearchSearchEngine):
    backend = RobustElasticSearchBackend
