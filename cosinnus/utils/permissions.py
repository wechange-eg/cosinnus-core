# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Group

from cosinnus.models.group import GroupAdmin


def check_ug_admin(user, group):
    """Returns ``True`` if the given user is admin of the given group.
    ``False`` otherwise.

    :param User user: The user object to check
    :param Group or int group: The group or its PK
    :returns: True if the user is a member of the group.
    """
    gid = group.pk if isinstance(group, Group) else int(group)
    return GroupAdmin.objects.filter(user=user, group_id=gid).exists()


def check_ug_membership(user, group):
    """Returns ``True`` if the given user is member (or admin) of the given group.
    ``False`` otherwise.

    :param User user: The user object to check
    :param Group or int group: The group or its PK
    :returns: True if the user is a member of the group.
    """
    if check_ug_admin(user, group):
        return True
    else:
        gid = group.pk if isinstance(group, Group) else int(group)
        return user.groups.filter(pk=gid).exists()


def check_object_access(user, obj):
    """Returns ``True`` if the user is a superuser or a member of the group the
    object belongs to.
    """
    if user.is_superuser:
        return True
    return check_ug_membership(user, obj.group)
