# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.contrib.auth.models import AbstractBaseUser

from cosinnus.utils.permissions import check_ug_admin, check_ug_membership


register = template.Library()


@register.filter
def is_group_admin(user, group):
    return check_ug_admin(user, group)


@register.filter
def is_group_member(user, group):
    return check_ug_membership(user, group)


@register.filter
def full_name(value):
    """Gets a readable name for the given user
    Filter: {{ user|full_name }}

    :param AbstractBaseUser value: the user object
    :return: either the full user name or the login user name.
    """

    if isinstance(value, AbstractBaseUser):
        return value.get_full_name() or value.get_username()
    return ""
