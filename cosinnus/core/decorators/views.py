# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.permissions import check_ug_admin, check_ug_membership


def staff_required(function):
    """A function decorator to assure a requesting user is a staff user."""
    actual_decorator = user_passes_test(
        lambda u: u.is_staff
    )
    return actual_decorator(function)


def superuser_required(function):
    """A function decorator to assure a requesting user has the superuser flag
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_superuser
    )
    return actual_decorator(function)


def require_membership(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is a member
    of the given group or has the superuser flag.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            try:
                group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                return HttpResponseNotFound(_("No group found with this name"))

            if request.user.is_superuser or check_ug_membership(request.user, group):
                setattr(self, group_attr, group)
                return function(self, request, *args, **kwargs)

            return HttpResponseForbidden(_("Not a member of this group"))
        return wrapper
    return decorator


def require_admin(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is an admin
    of the given group or has the superuser flag.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            try:
                group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                return HttpResponseNotFound(_("No group found with this name"))

            if request.user.is_superuser or check_ug_admin(request.user, group):
                setattr(self, group_attr, group)
                return function(self, request, *args, **kwargs)

            return HttpResponseForbidden(_("Not an admin of this group"))
        return wrapper
    return decorator
