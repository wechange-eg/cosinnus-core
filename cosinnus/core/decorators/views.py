# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import available_attrs

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


def require_populate_group(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is a member
    of the given group or has the superuser flag.

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_id = kwargs.get(group_url_kwarg, None)
            if not group_id:
                raise Http404("No group provided")

            if not check_ug_membership(request.user, group_id) and \
                    not request.user.is_superuser:
                return HttpResponseForbidden("Not a member of this group")

            setattr(self, group_attr, get_object_or_404(Group, pk=group_id))
            return function(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin_group(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is an admin
    of the given group or has the superuser flag.

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_id = kwargs.get(group_url_kwarg, None)
            if not group_id:
                raise Http404("No group provided")

            if not check_ug_admin(request.user, group_id) and \
                    not request.user.is_superuser:
                return HttpResponseForbidden("Not an admin of this group")

            setattr(self, group_attr, get_object_or_404(Group, pk=group_id))
            return function(self, request, *args, **kwargs)
        return wrapper
    return decorator
