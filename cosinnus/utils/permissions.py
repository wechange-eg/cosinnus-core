# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def check_ug_admin(user, group):
    """Returns ``True`` if the given user is admin of the given group.
    ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the given group.
    """
    return group.is_admin(user)


def check_ug_membership(user, group):
    """Returns ``True`` if the given user is member or admin of the given
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    return group.is_member(user)


def check_ug_pending(user, group):
    """Returns ``True`` if the given user is member or admin of the given
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    return group.is_pending(user)


def check_object_access(user, obj):
    """Returns ``True`` if the user is a superuser or a member of the group the
    object belongs to.
    """
    return user.is_superuser or check_ug_membership(user, obj.group)
