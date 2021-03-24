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

from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchEngine
from urllib3.exceptions import ProtocolError, ConnectionError
from elasticsearch.exceptions import TransportError

from django.contrib import messages

import logging 
from django.utils.encoding import force_text
from cosinnus.models.group import CosinnusPortal
logger = logging.getLogger('cosinnus')


USER_MODEL = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    Email Authentication Backend
    
    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
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
                message_parts = force_text(_('The email address for the account you are trying to use needs to be activated before you can log in.'))
                support_email = CosinnusPortal.get_current().support_email
                if support_email:
                    message_parts += ' ' + force_text(_('If you have not received an activation email yet, please try signing up again or contact our support at %(email)s!') % {'email': support_email})
                else:
                    message_parts += ' ' + force_text(_('If you have not received an activation email from %(portal_name)s within a few minutes please look in your spam folder or try signing up again!') % {'portal_name': CosinnusPortal.get_current().name})
                messages.error(request, message_parts)
        elif user and user.check_password(password) and self.user_can_authenticate(user):
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

    def build_schema(self, *args, **kwargs):
        """ Use the standard search_analyzer for ngram fields, so the search query itself won't be n-gramed """
        content_field_name, mapping = super(RobustElasticSearchBackend, self).build_schema(*args, **kwargs)
        for _field_name, field_mapping in mapping.items():
            if "analyzer" in field_mapping and field_mapping["analyzer"] == "ngram_analyzer":
                field_mapping["search_analyzer"] = "standard"
        return content_field_name, mapping

    @mute_error
    def update(self, *args, **kwargs):
        super(RobustElasticSearchBackend, self).update(*args, **kwargs)

    @mute_error
    def remove(self, *args, **kwargs):
        super(RobustElasticSearchBackend, self).remove(*args, **kwargs)

    @mute_error
    def clear(self, *args, **kwargs):
        super(RobustElasticSearchBackend, self).clear(*args, **kwargs)


class RobustElasticSearchEngine(ElasticsearchSearchEngine):
    backend = RobustElasticSearchBackend
