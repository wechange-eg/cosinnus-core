# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.mail import get_connection, EmailMessage
from django.template.loader import render_to_string

from cosinnus.conf import settings


import django.dispatch as dispatch

""" Called when a user requests membership of a group """
user_group_join_requested = dispatch.Signal(providing_args=["group", "user"])

""" Called when an admin accepts a user membership request of a group """
user_group_join_accepted = dispatch.Signal(providing_args=["group", "user"])

""" Called when an admin declines a user membership request of a group """
user_group_join_declined = dispatch.Signal(providing_args=["group", "user"])


# we need to load the receivers for them to be active
import receivers
