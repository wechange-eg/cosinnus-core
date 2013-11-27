# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def check_ug_admin(user, group):
    """Returns ``True`` if the given user is admin of the given group.
    ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the given group.
    """
    # prevent circular import
    from cosinnus.models import CosinnusGroup, GroupAdmin

    if not isinstance(group, CosinnusGroup):
        raise ValueError('Expecting a group instance as second argument')

    return GroupAdmin.objects.filter(user_id=user.pk, group_id=group.pk).exists()


def check_ug_membership(user, group):
    """Returns ``True`` if the given user is member or admin of the given
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    # prevent circular import
    from cosinnus.models import CosinnusGroup

    if not isinstance(group, CosinnusGroup):
        raise ValueError('Expecting a group instance as second argument')

    if user.is_anonymous():
        return False
    return user.cosinnus_groups.filter(pk=group.pk).exists() or check_ug_admin(user, group)


def check_object_access(user, obj):
    """Returns ``True`` if the user is a superuser or a member of the group the
    object belongs to.
    """
    return user.is_superuser or check_ug_membership(user, obj.group)
