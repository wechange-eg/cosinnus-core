# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch

""" Called after a CosinnusGroup, or one of its extending models is freshly created """
group_object_ceated = dispatch.Signal(providing_args=["group"])

""" Called after a new user and their profile is freshly created """
userprofile_ceated = dispatch.Signal(providing_args=["profile"])

""" Called when a user requests membership of a group """
user_group_join_requested = dispatch.Signal(providing_args=["group", "user"])

""" Called when an admin accepts a user membership request of a group """
user_group_join_accepted = dispatch.Signal(providing_args=["group", "user"])

""" Called when an admin declines a user membership request of a group """
user_group_join_declined = dispatch.Signal(providing_args=["group", "user"])


# we need to load the receivers for them to be active
import receivers
