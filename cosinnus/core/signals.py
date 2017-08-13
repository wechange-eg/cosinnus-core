# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch

""" Called once, after server startup, when we can be absolutely sure that all cosinnus apps are loaded """
all_cosinnus_apps_loaded = dispatch.Signal()

""" Called after a CosinnusGroup, or one of its extending models is freshly created """
group_object_ceated = dispatch.Signal(providing_args=["group"])

""" Called after a new user and their profile is freshly created """
userprofile_ceated = dispatch.Signal(providing_args=["profile"])

""" Called after a new user voluntarily signs up on the portal, using the web frontend """
user_registered = dispatch.Signal(providing_args=["user"])

""" Called when the user logs in for the first time ever """
user_logged_in_first_time = dispatch.Signal(providing_args=['request', 'user'])

""" Called after a new user voluntarily signs up on the portal, using the web frontend """
user_joined_group = dispatch.Signal(providing_args=["user", "group"])

""" Called when a user requests membership of a group """
user_group_join_requested = dispatch.Signal(providing_args=["user", "obj", "audience"])

""" Called when an admin accepts a user membership request of a group """
user_group_join_accepted = dispatch.Signal(providing_args=["user", "obj", "audience"])

""" Called when an admin declines a user membership request of a group """
user_group_join_declined = dispatch.Signal(providing_args=["user", "obj", "audience"])


""" Called when a user was invited to a group """
user_group_invited = dispatch.Signal(providing_args=["user", "obj", "audience"])

""" Called when an user accepts a group invitation """
user_group_invitation_accepted = dispatch.Signal(providing_args=["user", "obj", "audience"])

""" Called when an admin declines a group invitation """
user_group_invitation_declined = dispatch.Signal(providing_args=["user", "obj", "audience"])


""" Called when a person (not a user yet) is being recruited for a group """
user_group_recruited = dispatch.Signal(providing_args=["user", "obj", "audience"])


# we need to load the receivers for them to be active
import receivers
