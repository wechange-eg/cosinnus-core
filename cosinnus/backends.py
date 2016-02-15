# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from cosinnus.utils.user import get_user_by_email_safe

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

