# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.mail.backends.smtp import EmailBackend
from django.utils.decorators import method_decorator

from cosinnus.utils.user import get_user_by_email_safe
from cosinnus.conf import settings
from django.utils.translation import ugettext_lazy as _

import dkim
import smtplib
from django.core.mail.message import sanitize_address

from haystack.backends.elasticsearch7_backend import Elasticsearch7SearchEngine, Elasticsearch7SearchBackend
from urllib3.exceptions import ProtocolError, ConnectionError
from elasticsearch.exceptions import TransportError

from django.contrib import messages

import logging 
from django.utils.encoding import force_str
from cosinnus.models.group import CosinnusPortal
from threading import Thread
logger = logging.getLogger('cosinnus')


USER_MODEL = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    Email Authentication Backend
    
    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
    Disallows guest user accounts from logging in via password.
    """
    
    def authenticate(self, request, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        email = username.lower().strip()
        user = get_user_by_email_safe(email)
        
        if not user:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            USER_MODEL().set_password(password)
            # check if a non-activated user with that email exists (ie the user hasnt activated his email yet)
            if CosinnusPortal.get_current().email_needs_verification and \
                USER_MODEL.objects.filter(is_active=True, email__iendswith='__%s' % email).count():
                message_parts = force_str(_('The email address for the account you are trying to use needs to be activated before you can log in.'))
                support_email = CosinnusPortal.get_current().support_email
                if support_email:
                    message_parts += ' ' + force_str(_('If you have not received an activation email yet, please try signing up again or contact our support at %(email)s!') % {'email': support_email})
                else:
                    message_parts += ' ' + force_str(_('If you have not received an activation email from %(portal_name)s within a few minutes please look in your spam folder or try signing up again!') % {'portal_name': CosinnusPortal.get_current().name})
                messages.error(request, message_parts)
        elif user and not user.is_guest and user.check_password(password) and self.user_can_authenticate(user):
            return user

    def get_user(self, user_id):
        """ Get a User object from the user_id. """
        try:
            user = USER_MODEL._default_manager.get(pk=user_id)
        except USER_MODEL.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
    

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
            signed_message = (signature + message_string).encode('utf-8')
            self.connection.sendmail(from_email, recipients, signed_message)
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True
    
    
def threaded_execution_and_catch_error(f):
    """ Will run in a thread and catch all errors """
    
    def error_wrapper(self, *args, **kwargs):
        my_self = self
        def do_execute():
            try:
                return f(my_self, *args, **kwargs)
            except (TransportError, ProtocolError, ConnectionError) as e:
                logger.error('Could not connect to the ElasticSearch backend for indexing! The search function will not work and saving objects on the site will be terribly slow! Exception in extra.', extra={'exception': force_str(e)})
            except Exception as e:
                logger.error('An unknown error occured while indexing an object! Exception in extra.', extra={'exception': force_str(e)})
                if settings.DEBUG:
                    raise
        
        if getattr(settings, 'COSINNUS_ELASTIC_BACKEND_RUN_THREADED', True):
            class CosinnusElasticsearchExecutionThread(Thread):
                def run(self):
                    do_execute()
            CosinnusElasticsearchExecutionThread().start()
        else:
            do_execute()
    return error_wrapper


class RobustElasticSearchBackend(Elasticsearch7SearchBackend):
    """A robust backend that doesn't crash when no connection is available"""
    
    MIN_GRAM = 2
    MAX_NGRAM = 25
    

    def __init__(self, *args, **options):
        """ Add custom default options """
        
        self.DEFAULT_SETTINGS = {
            "settings": {
                "index": {
                    "max_ngram_diff": self.MAX_NGRAM - self.MIN_GRAM + 1,
                },
                "analysis": {
                    "analyzer": {
                        "ngram_analyzer": {
                            "tokenizer": "standard",
                            "filter": [
                                "haystack_ngram",
                                "lowercase",
                            ],
                        },
                        "edgengram_analyzer": {
                            "tokenizer": "standard",
                            "filter": [
                                "haystack_edgengram",
                                "lowercase",
                            ],
                        },
                    },
                    "filter": {
                        "haystack_ngram": {
                            "type": "ngram",
                            "min_gram": self.MIN_GRAM,
                            "max_gram": self.MAX_NGRAM,
                        },
                        "haystack_edgengram": {
                            "type": "edge_ngram",
                            "min_gram": self.MIN_GRAM,
                            "max_gram": self.MAX_NGRAM,
                        },
                    },
                },
            },
        }
        
        super(RobustElasticSearchBackend, self).__init__(*args, **options)

    def build_schema(self, *args, **kwargs):
        """ Use the standard search_analyzer for ngram fields, so the search query itself won't be n-gramed """
        content_field_name, mapping = super(RobustElasticSearchBackend, self).build_schema(*args, **kwargs)
        for _field_name, field_mapping in mapping.items():
            if "analyzer" in field_mapping and field_mapping["analyzer"] == "ngram_analyzer":
                field_mapping["search_analyzer"] = "standard"
            field_class = args[0].get(_field_name)
            if field_class and field_class.field_type == "nested":
                field_mapping["type"] = "nested"
                if hasattr(field_class, "get_properties"):
                    field_mapping["properties"] = field_class.get_properties()
        return (content_field_name, mapping)

    @threaded_execution_and_catch_error
    def update(self, *args, **kwargs):
        super(RobustElasticSearchBackend, self).update(*args, **kwargs)

    @threaded_execution_and_catch_error
    def remove(self, *args, **kwargs):
        super(RobustElasticSearchBackend, self).remove(*args, **kwargs)

    @threaded_execution_and_catch_error
    def clear(self, *args, **kwargs):
        super(RobustElasticSearchBackend, self).clear(*args, **kwargs)


class RobustElasticSearchEngine(Elasticsearch7SearchEngine):
    backend = RobustElasticSearchBackend
