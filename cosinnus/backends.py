# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.mail.backends.smtp import EmailBackend

from cosinnus.utils.user import get_user_by_email_safe
from cosinnus.conf import settings

import dkim
import smtplib
from django.core.mail.message import sanitize_address


USER_MODEL = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    Email Authentication Backend
    
    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
    """
    
    def authenticate(self, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        user = get_user_by_email_safe(username)
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
    
    