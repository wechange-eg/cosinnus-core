# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

import django.dispatch as dispatch

""" Called once, after server startup, when we can be absolutely sure that all cosinnus apps are loaded """
all_cosinnus_apps_loaded = dispatch.Signal()

""" Called after a CosinnusGroup, or one of its extending models is freshly created """
group_object_created = dispatch.Signal(providing_args=["group"])

""" Called after a CosinnusGroup, or one of its extending models are saved (create and update) 
        in the frontend's group form by one of the group admins
    Note: This does *not* trigger after any other model update or save! """
group_saved_in_form = dispatch.Signal(providing_args=["group", "user"])

""" Called after a CosinnusIdea is freshly created """
idea_object_created = dispatch.Signal(providing_args=["idea"])

""" Called after a new user and their profile is freshly created """
userprofile_created = dispatch.Signal(providing_args=["profile"])

""" Called after a new user voluntarily signs up on the portal, using the web frontend """
user_registered = dispatch.Signal(providing_args=["user"])

""" Called after a user account has been deactived 
    (this also happens when a user "deletes" their account """
user_deactivated = dispatch.Signal(providing_args=["user"])

""" Called after a user account is activated, or re-activated after being deactivated """
user_activated = dispatch.Signal(providing_args=["user"])

""" Called after a user has deactivated their account and marked it for 30-day deletion,
    or when an admin has triggered this action for a user account in the django admin. """
user_deactivated_and_marked_for_deletion = dispatch.Signal(providing_args=["profile"])

""" Called just before a user "deletes" their account and their
    profile still just now exists, before it will be deleted.
    Can be used to delete/disconnect any external linked accounts. """
pre_userprofile_delete = dispatch.Signal(providing_args=["profile"])

""" Called after a user has successfully changed their password """
user_password_changed = dispatch.Signal(providing_args=["user"])

""" Called when the user logs in for the first time ever """
user_logged_in_first_time = dispatch.Signal(providing_args=['request', 'user'])

""" Called after a new user properly joined a group as member (invites or join-requests do not trigger this!) """
user_joined_group = dispatch.Signal(providing_args=["user", "group"])

""" Called after a new user left a group or was kicked out """
user_left_group = dispatch.Signal(providing_args=["user", "group"])

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


""" Called when a group is moved to the current portal, serves as a notifcation message for users """
group_moved_to_portal = dispatch.Signal(providing_args=["user", "obj", "audience"])

""" Called after a CosinnusGroup, or one of its extending models was deactivated """
group_deactivated = dispatch.Signal(providing_args=["group"])

""" Called after a CosinnusGroup, or one of its extending models was reactivated """
group_reactivated = dispatch.Signal(providing_args=["group"])

""" Called after a CosinnusGroup, or one of its extending models had one or more of their cosinnus apps activated """
group_apps_activated = dispatch.Signal(providing_args=["group", "apps"])

""" Called after a CosinnusGroup, or one of its extending models had one or more of their cosinnus apps deactivated """
group_apps_deactivated = dispatch.Signal(providing_args=["group", "apps"])

""" Called after a CosinnusGroupMembership for a user has changed """
group_membership_has_changed = dispatch.Signal(providing_args=["instance", "deleted"])


""" Called when a group was invited to an organization """
organization_group_invited = dispatch.Signal(providing_args=["organization", "group"])

""" Called when an group accepts an organization invitation """
organization_group_invitation_accepted = dispatch.Signal(providing_args=["organization", "group"])

""" Called when a group declines an organization invitation """
organization_group_invitation_declined = dispatch.Signal(providing_args=["organization", "group"])

""" Called when a group requested an organization assignment """
organization_group_requested = dispatch.Signal(providing_args=["organization", "group"])

""" Called when an organization accepts a groups request """
organization_group_request_accepted = dispatch.Signal(providing_args=["organization", "group"])

""" Called when an organization declines a groups request """
organization_group_request_declined = dispatch.Signal(providing_args=["organization", "group"])
